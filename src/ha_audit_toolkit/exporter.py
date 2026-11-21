from __future__ import annotations

import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .io import sha256_file, write_json
from .secret_scan import scan_file


RESERVED_EXPORT_NAMES = {"README.md", "safe_export_manifest.json"}


def export_name_key(name: str) -> str:
    """Return a filesystem-conservative key for a flat export filename."""

    return unicodedata.normalize("NFC", name.casefold())


RESERVED_EXPORT_NAME_KEYS = frozenset(export_name_key(name) for name in RESERVED_EXPORT_NAMES)


class UnsafeExportError(ValueError):
    """Raised when an export cannot satisfy the toolkit's safety boundary."""


@dataclass(frozen=True)
class PlannedFile:
    source: Path
    bundle_relative_path: str
    export_name: str


@dataclass(frozen=True)
class ExportPlan:
    output: Path
    source_bundle: str
    files: tuple[PlannedFile, ...]
    skipped_files: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_output(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def _relative_manifest_path(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise UnsafeExportError(f"Manifest {field} must be a non-empty relative path.")
    if "\\" in value:
        raise UnsafeExportError(f"Manifest {field} must use forward slashes: {value!r}")
    pure_path = PurePosixPath(value)
    if pure_path.is_absolute() or ".." in pure_path.parts or not pure_path.parts:
        raise UnsafeExportError(f"Manifest {field} escapes the audit root: {value!r}")
    return Path(*pure_path.parts)


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _is_same_or_within(path: Path, directory: Path) -> bool:
    """Check containment through both lexical paths and existing filesystem aliases."""

    if _is_within(path, directory):
        return True
    for candidate in (path, *path.parents):
        try:
            if candidate.samefile(directory):
                return True
        except OSError:
            continue
    return False


def _safe_output_path(root: Path, bundle: Path, output: Path) -> Path:
    if output.is_symlink():
        raise UnsafeExportError(f"Export output cannot be a symlink: {output}")
    output = output.resolve()
    if output.exists() and not output.is_dir():
        raise UnsafeExportError(f"Export output exists and is not a directory: {output}")
    if _is_same_or_within(root, output):
        raise UnsafeExportError("Export output cannot be the audit root or one of its parents.")
    if _is_same_or_within(output, bundle) or _is_same_or_within(bundle, output):
        raise UnsafeExportError("Export output cannot overlap the canonical source bundle.")
    return output


def _unique_export_name(bundle_relative_path: str, used_name_keys: set[str]) -> str:
    source_name = PurePosixPath(bundle_relative_path).name
    export_name = source_name
    if export_name_key(export_name) in RESERVED_EXPORT_NAME_KEYS or export_name_key(export_name) in used_name_keys:
        export_name = bundle_relative_path.replace("/", "__")
    if export_name_key(export_name) in RESERVED_EXPORT_NAME_KEYS:
        export_name = f"source__{export_name}"
    base_name = export_name
    suffix = 2
    while (
        export_name_key(export_name) in used_name_keys
        or export_name_key(export_name) in RESERVED_EXPORT_NAME_KEYS
    ):
        export_name = f"{base_name}__{suffix}"
        suffix += 1
    used_name_keys.add(export_name_key(export_name))
    return export_name


def _preflight_preserved_output(plan: ExportPlan) -> None:
    if not plan.output.exists():
        return

    existing_by_key: dict[str, Path] = {}
    for child in plan.output.iterdir():
        key = export_name_key(child.name)
        previous = existing_by_key.get(key)
        if previous is not None and previous.name != child.name:
            raise UnsafeExportError(
                "Existing export entries collide by case or Unicode normalization: "
                f"{previous.name!r} and {child.name!r}"
            )
        existing_by_key[key] = child

    destination_names = [
        *(planned_file.export_name for planned_file in plan.files),
        *sorted(RESERVED_EXPORT_NAMES),
    ]
    for name in destination_names:
        destination = plan.output / name
        existing = existing_by_key.get(export_name_key(name))
        if existing is not None and existing.name != name:
            raise UnsafeExportError(
                f"Existing export entry aliases destination {name!r}: {existing.name!r}"
            )
        if destination.is_symlink():
            raise UnsafeExportError(f"Export destination cannot be a symlink: {name}")
        if destination.exists() and not destination.is_file():
            raise UnsafeExportError(f"Export destination exists and is not a regular file: {name}")


def plan_safe_pack(root: Path, manifest: dict[str, Any], output: Path) -> ExportPlan:
    root = root.resolve()
    if not root.is_dir():
        raise UnsafeExportError(f"Audit root does not exist or is not a directory: {root}")

    bundle_path = _relative_manifest_path(
        manifest.get("current_canonical_bundle"),
        field="current_canonical_bundle",
    )
    bundle = (root / bundle_path).resolve()
    if bundle == root or not _is_within(bundle, root):
        raise UnsafeExportError("Manifest current_canonical_bundle escapes the audit root.")
    if not bundle.is_dir():
        raise UnsafeExportError(f"Canonical source bundle does not exist: {bundle_path.as_posix()}")

    output = _safe_output_path(root, bundle, output)
    planned: list[PlannedFile] = []
    skipped: list[str] = []
    possible_secrets: list[str] = []
    used_name_keys: set[str] = set()

    for index, entry in enumerate(manifest.get("files", [])):
        if not isinstance(entry, dict):
            raise UnsafeExportError(f"Manifest files[{index}] must be an object.")
        entry_path = entry.get("path")
        relative_path = _relative_manifest_path(entry_path, field=f"files[{index}].path")
        if entry.get("safe_to_upload") is not True:
            skipped.append(relative_path.as_posix())
            continue

        source = (root / relative_path).resolve()
        if not _is_within(source, bundle):
            raise UnsafeExportError(
                f"Upload-safe entry is outside the canonical source bundle: {relative_path.as_posix()}"
            )
        if not source.is_file():
            raise UnsafeExportError(f"Upload-safe source is missing or not a file: {relative_path.as_posix()}")

        actual_bundle_path = source.relative_to(bundle).as_posix()
        declared_bundle_path = _relative_manifest_path(
            entry.get("bundle_relative_path"),
            field=f"files[{index}].bundle_relative_path",
        ).as_posix()
        if actual_bundle_path != declared_bundle_path:
            raise UnsafeExportError(
                "Upload-safe entry does not resolve to its declared bundle path: "
                f"{relative_path.as_posix()}"
            )
        source_type = entry.get("source_type")
        has_raw_source_type = isinstance(source_type, str) and source_type.lower() == "raw"
        if PurePosixPath(actual_bundle_path).parts[0].lower() == "raw" or has_raw_source_type:
            raise UnsafeExportError(f"Raw evidence cannot be exported: {actual_bundle_path}")

        findings = scan_file(source, root=bundle)
        possible_secrets.extend(f"{finding.path}:{finding.line}" for finding in findings)
        planned.append(
            PlannedFile(
                source=source,
                bundle_relative_path=actual_bundle_path,
                export_name=_unique_export_name(actual_bundle_path, used_name_keys),
            )
        )

    if possible_secrets:
        locations = ", ".join(possible_secrets)
        raise UnsafeExportError(
            "Possible secret pattern(s) found in upload-safe source file(s): "
            f"{locations}. Review or redact before exporting."
        )

    return ExportPlan(
        output=output,
        source_bundle=bundle_path.as_posix(),
        files=tuple(planned),
        skipped_files=tuple(skipped),
    )


def export_safe_pack(root: Path, manifest: dict[str, Any], output: Path, *, clean: bool = True) -> dict[str, Any]:
    plan = plan_safe_pack(root, manifest, output)
    output = plan.output
    if clean:
        clean_output(output)
    else:
        _preflight_preserved_output(plan)
        output.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for planned_file in plan.files:
        shutil.copy2(planned_file.source, output / planned_file.export_name)
        copied.append(planned_file.export_name)

    export_manifest = {
        "schema_version": 2,
        "exported_at": utc_now(),
        "source_bundle": plan.source_bundle,
        "copied_files": copied,
        "skipped_files": list(plan.skipped_files),
        "preflight_checks": [
            "source_paths_within_canonical_bundle",
            "raw_sources_excluded",
            "configured_secret_patterns_absent",
            "output_does_not_overlap_source_evidence",
        ],
        "privacy_note": "Review files before upload. Raw files are excluded by default.",
    }
    (output / "README.md").write_text(build_readme(export_manifest), encoding="utf-8")
    export_manifest["file_sha256"] = {
        name: sha256_file(output / name)
        for name in [*copied, "README.md"]
    }
    write_json(output / "safe_export_manifest.json", export_manifest)
    return export_manifest


def build_readme(export_manifest: dict[str, Any]) -> str:
    files = "\n".join(f"- `{name}`" for name in export_manifest.get("copied_files", [])) or "- none"
    return (
        "# Home Assistant Audit Safe Export\n\n"
        "This folder is a flat, upload-oriented subset of a Home Assistant audit bundle.\n\n"
        f"- Source bundle: `{export_manifest.get('source_bundle')}`\n"
        f"- Exported at: `{export_manifest.get('exported_at')}`\n\n"
        "Export preflight passed before this folder was written: source paths stayed inside the canonical bundle, "
        "raw evidence was excluded, and no configured secret pattern matched.\n\n"
        "## Included Files\n\n"
        f"{files}\n\n"
        "## Safety Notes\n\n"
        "- Raw files are intentionally excluded.\n"
        "- Review this folder before sharing it with an assistant or teammate.\n"
        "- Treat entity IDs, areas, device names, and state summaries as potentially private.\n"
    )
