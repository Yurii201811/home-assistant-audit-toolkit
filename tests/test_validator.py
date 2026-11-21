from __future__ import annotations

import json
import os
from pathlib import Path

from ha_audit_toolkit.exporter import export_safe_pack
from ha_audit_toolkit.io import sha256_file
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


def test_validate_export_rejects_modified_file(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_manifest = export_safe_pack(tmp_path, manifest, output)
    copied_file = output / export_manifest["copied_files"][0]
    copied_file.write_text("changed after export\n", encoding="utf-8")

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert f"Export SHA-256 mismatch for: {copied_file.name}" in result.errors


def test_validate_export_rejects_missing_file(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_manifest = export_safe_pack(tmp_path, manifest, output)
    copied_file = output / export_manifest["copied_files"][0]
    copied_file.unlink()

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert f"Export is missing regular file: {copied_file.name}" in result.errors


def test_validate_export_rejects_symlinked_file(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_manifest = export_safe_pack(tmp_path, manifest, output)
    copied_file = output / export_manifest["copied_files"][0]
    outside = tmp_path / "outside.txt"
    outside.write_text(copied_file.read_text(encoding="utf-8"), encoding="utf-8")
    copied_file.unlink()
    os.symlink(outside, copied_file)

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert f"Symlinks are not allowed in export: {copied_file.name}" in result.errors


def test_validate_export_rejects_nested_directory(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_safe_pack(tmp_path, manifest, output)
    (output / "nested").mkdir()

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert "Non-file entry is not allowed in export: nested" in result.errors


def test_validate_export_rejects_invalid_digest_metadata(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_manifest = export_safe_pack(tmp_path, manifest, output)
    copied_name = export_manifest["copied_files"][0]
    export_manifest["file_sha256"][copied_name] = "z" * 64
    (output / "safe_export_manifest.json").write_text(json.dumps(export_manifest), encoding="utf-8")

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert f"Export has invalid SHA-256 metadata for: {copied_name}" in result.errors


def test_validate_export_rejects_case_equivalent_copied_names(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_manifest = export_safe_pack(tmp_path, manifest, output)
    copied_name = export_manifest["copied_files"][0]
    alias = copied_name.upper()
    export_manifest["copied_files"].append(alias)
    export_manifest["file_sha256"][alias] = export_manifest["file_sha256"][copied_name]
    (output / "safe_export_manifest.json").write_text(json.dumps(export_manifest), encoding="utf-8")

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert any("after case and Unicode normalization" in error for error in result.errors)


def test_validate_export_rejects_unicode_equivalent_copied_names(tmp_path: Path) -> None:
    bundle = create_minimal_bundle(tmp_path)
    manifest = build_registry(tmp_path, bundle.name)
    output = tmp_path / "export"
    export_manifest = export_safe_pack(tmp_path, manifest, output)
    composed = "Résumé.txt"
    decomposed = "Re\u0301sume\u0301.txt"
    extra = output / composed
    extra.write_text("same logical filename", encoding="utf-8")
    digest = sha256_file(extra)
    export_manifest["copied_files"].extend([composed, decomposed])
    export_manifest["file_sha256"].update({composed: digest, decomposed: digest})
    (output / "safe_export_manifest.json").write_text(json.dumps(export_manifest), encoding="utf-8")

    result = validate_bundle(tmp_path, manifest, export_dir=output)

    assert not result.ok
    assert any("after case and Unicode normalization" in error for error in result.errors)
