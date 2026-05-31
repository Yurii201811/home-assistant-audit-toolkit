from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import read_json, record_count

DEFAULT_SAFE_EXPORT_NAMES = {
    "system_snapshot.json",
    "automations.json",
    "scripts.json",
    "automation_dependencies.json",
    "script_dependencies.json",
    "areas.json",
    "integrations.json",
    "recommendations.json",
    "00_executive_summary.md",
    "01_system_overview.md",
    "09_recommendations.md",
    "manifest.json",
    "progress.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_type(rel: str) -> str:
    if rel.startswith("raw/"):
        return "raw"
    if rel.startswith("normalized/"):
        return "normalized"
    if rel.startswith("reports/"):
        return "report"
    if rel.startswith("index/"):
        return "index"
    return "derived"


def privacy_sensitivity(rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    if rel.startswith("raw/"):
        return "high"
    if name in {"entities.json", "devices.json", "current_state_snapshot.json"}:
        return "medium"
    if rel.startswith("normalized/"):
        return "medium"
    return "low"


def safe_to_upload(rel: str, safe_names: set[str]) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return not rel.startswith("raw/") and name in safe_names


def file_entry(root: Path, bundle: Path, file_path: Path, safe_names: set[str]) -> dict[str, Any]:
    rel = file_path.relative_to(bundle).as_posix()
    return {
        "path": file_path.relative_to(root).as_posix(),
        "bundle_relative_path": rel,
        "source_type": source_type(rel),
        "record_count": record_count(file_path),
        "safe_to_upload": safe_to_upload(rel, safe_names),
        "privacy_sensitivity": privacy_sensitivity(rel),
        "size_bytes": file_path.stat().st_size,
        "notes": notes_for(rel),
    }


def notes_for(rel: str) -> str:
    if rel.startswith("raw/"):
        return "Raw local evidence. Do not upload casually."
    if rel.startswith("normalized/"):
        return "Derived audit-ready data."
    if rel.startswith("reports/"):
        return "Human-readable derived report."
    if rel.startswith("index/"):
        return "Generated bundle metadata."
    return ""


def build_registry(
    root: Path,
    bundle_name: str,
    *,
    safe_names: set[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    bundle = (root / bundle_name).resolve()
    if not bundle.exists() or not bundle.is_dir():
        raise FileNotFoundError(f"Bundle does not exist: {bundle}")
    safe_names = safe_names or DEFAULT_SAFE_EXPORT_NAMES
    progress = read_json(bundle / "index" / "progress.json", {})
    system = read_json(bundle / "normalized" / "system_snapshot.json", {})
    snapshot = (system.get("records") or [{}])[0] if isinstance(system, dict) else {}
    files = [
        file_entry(root, bundle, file_path, safe_names)
        for file_path in sorted(bundle.rglob("*"))
        if file_path.is_file()
    ]
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "root": ".",
        "root_note": "Paths in this manifest are relative to the audit workspace root.",
        "current_canonical_bundle": bundle.name,
        "current_bundle_generated_at": progress.get("generated_at"),
        "completeness_verdict": progress.get("completeness_verdict"),
        "home_assistant_version": snapshot.get("home_assistant_version"),
        "source_hierarchy": [
            "raw files are direct evidence and private by default",
            "normalized files are audit-ready working data",
            "reports are derived human summaries",
            "safe exports are the only intended upload surface",
        ],
        "missing_or_partial_data": progress.get("partial_sections") or ["unknown_or_not_recorded"],
        "files": files,
    }
