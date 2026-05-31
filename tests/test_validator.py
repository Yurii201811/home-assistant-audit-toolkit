from __future__ import annotations

from pathlib import Path

from ha_audit_toolkit.exporter import export_safe_pack
from ha_audit_toolkit.registry import build_registry
from ha_audit_toolkit.validator import validate_bundle


def create_minimal_bundle(root: Path) -> Path:
    bundle = root / "ha_audit_20260101_000000"
    for folder in ("index", "normalized", "reports"):
        (bundle / folder).mkdir(parents=True, exist_ok=True)
    (bundle / "index" / "progress.json").write_text('{"bundle_dir":"ha_audit_20260101_000000","completeness_verdict":"safe_to_publish"}')
    (bundle / "index" / "manifest.json").write_text("{}")
    for name in ("system_snapshot", "entities", "devices", "automations", "scripts", "recommendations"):
        (bundle / "normalized" / f"{name}.json").write_text('{"record_count":0,"records":[]}')
    for name in ("00_executive_summary.md", "01_system_overview.md", "09_recommendations.md"):
        (bundle / "reports" / name).write_text("# Report\n")
    return bundle


def test_validate_bundle_and_export_pass(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    export_safe_pack(tmp_path, manifest, tmp_path / "export")

    result = validate_bundle(tmp_path, manifest, export_dir=tmp_path / "export")

    assert result.ok

