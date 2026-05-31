from __future__ import annotations

from pathlib import Path

from ha_audit_toolkit.exporter import export_safe_pack
from ha_audit_toolkit.registry import build_registry


def test_export_safe_pack_excludes_raw(tmp_path: Path) -> None:
    root = tmp_path
    bundle = root / "ha_audit_20260101_000000"
    (bundle / "index").mkdir(parents=True)
    (bundle / "normalized").mkdir()
    (bundle / "raw").mkdir()
    (bundle / "index" / "progress.json").write_text('{"bundle_dir":"ha_audit_20260101_000000","completeness_verdict":"safe_to_publish"}')
    (bundle / "index" / "manifest.json").write_text("{}")
    (bundle / "normalized" / "system_snapshot.json").write_text('{"record_count":1,"records":[{}]}')
    (bundle / "raw" / "states.json").write_text('{"token":"not-a-real-token"}')
    manifest = build_registry(root, bundle.name)

    export_manifest = export_safe_pack(root, manifest, root / "export")

    assert "system_snapshot.json" in export_manifest["copied_files"]
    assert "states.json" not in export_manifest["copied_files"]
    assert not (root / "export" / "states.json").exists()

