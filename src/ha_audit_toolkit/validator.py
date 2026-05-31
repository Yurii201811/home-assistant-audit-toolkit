from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io import read_json, record_count
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
    if not export_manifest_path.exists():
        result.errors.append("Export is missing safe_export_manifest.json.")
        return
    export_manifest = read_json(export_manifest_path, {})
    if export_manifest.get("source_bundle") != manifest.get("current_canonical_bundle"):
        result.errors.append("Export source_bundle does not match manifest current_canonical_bundle.")
    allowed = set(export_manifest.get("copied_files", [])) | {"README.md", "safe_export_manifest.json"}
    for path in export_dir.iterdir():
        if path.is_file() and path.name not in allowed:
            result.errors.append(f"Unexpected file in export: {path.name}")
        if "raw" in path.parts:
            result.errors.append(f"Raw path appeared in export: {path}")
        if path.is_file():
            for finding in scan_file(path, root=export_dir):
                result.errors.append(f"Possible secret in export {finding.path}:{finding.line}")

