from __future__ import annotations

import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exporter import RESERVED_EXPORT_NAME_KEYS, export_name_key
from .io import read_json, record_count, sha256_file
from .secret_scan import scan_file

REQUIRED_FILES = {
    "index/manifest.json",
    "index/progress.json",
    "normalized/system_snapshot.json",
    "normalized/entities.json",
    "normalized/devices.json",
    "normalized/automations.json",
    "normalized/scripts.json",
    "normalized/recommendations.json",
    "reports/00_executive_summary.md",
    "reports/01_system_overview.md",
    "reports/09_recommendations.md",
}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_bundle(root: Path, manifest: dict[str, Any], *, export_dir: Path | None = None) -> ValidationResult:
    root = root.resolve()
    result = ValidationResult()
    bundle_name = manifest.get("current_canonical_bundle")
    if not isinstance(bundle_name, str):
        result.errors.append("Manifest is missing current_canonical_bundle.")
        return result
    bundle = root / bundle_name
    if not bundle.exists():
        result.errors.append(f"Bundle does not exist: {bundle_name}")
        return result

    for rel in sorted(REQUIRED_FILES):
        if not (bundle / rel).exists():
            result.errors.append(f"Missing required file: {bundle_name}/{rel}")

    progress = read_json(bundle / "index" / "progress.json", {})
    if progress.get("bundle_dir") and progress.get("bundle_dir") != bundle_name:
        result.errors.append("progress.json bundle_dir does not match current_canonical_bundle.")
    if progress.get("completeness_verdict") != "safe_to_publish":
        result.warnings.append("progress.json is not marked safe_to_publish.")

    for entry in manifest.get("files", []):
        rel_path = entry.get("path")
        if not isinstance(rel_path, str):
            continue
        file_path = root / rel_path
        if not file_path.exists():
            result.errors.append(f"Manifest file missing on disk: {rel_path}")
            continue
        expected = entry.get("record_count")
        if isinstance(expected, int):
            try:
                actual = record_count(file_path)
            except Exception as exc:  # noqa: BLE001 - validation should report all possible errors.
                result.errors.append(f"Could not count records for {rel_path}: {exc}")
                continue
            if actual is not None and actual != expected:
                result.errors.append(f"Record count mismatch for {rel_path}: manifest {expected}, actual {actual}")
        if entry.get("safe_to_upload"):
            for finding in scan_file(file_path, root=root):
                result.errors.append(f"Possible secret in {finding.path}:{finding.line}")

    if not manifest.get("missing_or_partial_data"):
        result.warnings.append("Manifest does not list missing_or_partial_data.")

    if export_dir is not None:
        validate_export(root, manifest, export_dir, result)
    return result


def validate_export(root: Path, manifest: dict[str, Any], export_dir: Path, result: ValidationResult) -> None:
    export_dir = export_dir.resolve()
    if not export_dir.exists():
        result.errors.append(f"Export directory does not exist: {export_dir}")
        return
    export_manifest_path = export_dir / "safe_export_manifest.json"
    if not export_manifest_path.is_file() or export_manifest_path.is_symlink():
        result.errors.append("Export is missing safe_export_manifest.json.")
        return
    export_manifest = read_json(export_manifest_path, {})
    if not isinstance(export_manifest, dict):
        result.errors.append("Export manifest must be a JSON object.")
        return
    if export_manifest.get("schema_version") != 2:
        result.errors.append("Export manifest schema_version must be 2 for integrity validation.")
    if export_manifest.get("source_bundle") != manifest.get("current_canonical_bundle"):
        result.errors.append("Export source_bundle does not match manifest current_canonical_bundle.")

    copied_files = export_manifest.get("copied_files")
    copied_name_keys = (
        [export_name_key(name) for name in copied_files if isinstance(name, str)]
        if isinstance(copied_files, list)
        else []
    )
    if (
        not isinstance(copied_files, list)
        or any(not isinstance(name, str) or not name or Path(name).name != name for name in copied_files)
        or len(set(copied_name_keys)) != len(copied_name_keys)
        or any(name_key in RESERVED_EXPORT_NAME_KEYS for name_key in copied_name_keys)
    ):
        result.errors.append(
            "Export copied_files must contain unique, non-reserved flat filenames "
            "after case and Unicode normalization."
        )
        copied_files = []

    payload_names = set(copied_files) | {"README.md"}
    allowed = payload_names | {"safe_export_manifest.json"}
    file_sha256 = export_manifest.get("file_sha256")
    if not isinstance(file_sha256, dict) or set(file_sha256) != payload_names:
        result.errors.append("Export file_sha256 must cover every copied file and README.md exactly.")
        file_sha256 = {}

    for path in export_dir.iterdir():
        if path.is_symlink():
            result.errors.append(f"Symlinks are not allowed in export: {path.name}")
            continue
        if not path.is_file():
            result.errors.append(f"Non-file entry is not allowed in export: {path.name}")
            continue
        if path.name not in allowed:
            result.errors.append(f"Unexpected file in export: {path.name}")
        for finding in scan_file(path, root=export_dir):
            result.errors.append(f"Possible secret in export {finding.path}:{finding.line}")

    for name in sorted(payload_names):
        path = export_dir / name
        if not path.is_file() or path.is_symlink():
            result.errors.append(f"Export is missing regular file: {name}")
            continue
        expected_hash = file_sha256.get(name)
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(character not in string.hexdigits for character in expected_hash)
        ):
            result.errors.append(f"Export has invalid SHA-256 metadata for: {name}")
            continue
        if sha256_file(path) != expected_hash.lower():
            result.errors.append(f"Export SHA-256 mismatch for: {name}")
