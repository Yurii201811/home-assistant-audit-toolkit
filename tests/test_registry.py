from __future__ import annotations

from pathlib import Path

from ha_audit_toolkit.registry import build_registry


def test_build_registry_marks_raw_unsafe(tmp_path: Path) -> None:
    root = tmp_path
    bundle = root / "ha_audit_20260101_000000"
    (bundle / "index").mkdir(parents=True)
    (bundle / "normalized").mkdir()
    (bundle / "raw" / "api").mkdir(parents=True)
    (bundle / "index" / "progress.json").write_text('{"bundle_dir":"ha_audit_20260101_000000","completeness_verdict":"safe_to_publish"}')
    (bundle / "normalized" / "system_snapshot.json").write_text('{"records":[{"home_assistant_version":"2026.1"}]}')
    (bundle / "raw" / "api" / "states.json").write_text("[]")

    manifest = build_registry(root, bundle.name)

    raw = next(entry for entry in manifest["files"] if entry["bundle_relative_path"] == "raw/api/states.json")
    assert raw["privacy_sensitivity"] == "high"
    assert raw["safe_to_upload"] is False

