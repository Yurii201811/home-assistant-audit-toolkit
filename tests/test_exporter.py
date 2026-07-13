from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

import pytest

from ha_audit_toolkit.cli import main
from ha_audit_toolkit.exporter import UnsafeExportError, export_safe_pack
from ha_audit_toolkit.registry import build_registry


def create_bundle(root: Path) -> Path:
    bundle = root / "ha_audit_20260101_000000"
    (bundle / "index").mkdir(parents=True)
    (bundle / "normalized").mkdir()
    (bundle / "raw").mkdir()
    (bundle / "index" / "progress.json").write_text(
        '{"bundle_dir":"ha_audit_20260101_000000","completeness_verdict":"safe_to_publish"}',
        encoding="utf-8",
    )
    (bundle / "index" / "manifest.json").write_text("{}", encoding="utf-8")
    (bundle / "normalized" / "system_snapshot.json").write_text(
        '{"record_count":1,"records":[{}]}',
        encoding="utf-8",
    )
    (bundle / "raw" / "states.json").write_text("[]", encoding="utf-8")
    return bundle


def test_export_safe_pack_excludes_raw(tmp_path: Path) -> None:
    root = tmp_path
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)

    export_manifest = export_safe_pack(root, manifest, root / "export")

    assert "system_snapshot.json" in export_manifest["copied_files"]
    assert "states.json" not in export_manifest["copied_files"]
    assert not (root / "export" / "states.json").exists()
    assert export_manifest["schema_version"] == 2
    assert set(export_manifest["file_sha256"]) == {*export_manifest["copied_files"], "README.md"}
    assert all(len(digest) == 64 for digest in export_manifest["file_sha256"].values())
    assert "configured_secret_patterns_absent" in export_manifest["preflight_checks"]


def test_no_clean_rejects_destination_symlink_before_writing(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    output = root / "export"
    output.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("do not overwrite", encoding="utf-8")
    os.symlink(outside, output / "system_snapshot.json")

    with pytest.raises(UnsafeExportError, match="destination cannot be a symlink"):
        export_safe_pack(root, manifest, output, clean=False)

    assert outside.read_text(encoding="utf-8") == "do not overwrite"
    assert not (output / "README.md").exists()
    assert not (output / "safe_export_manifest.json").exists()


def test_export_rejects_symlinked_output_root(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    outside = tmp_path / "outside"
    outside.mkdir()
    output = root / "export"
    os.symlink(outside, output)

    with pytest.raises(UnsafeExportError, match="output cannot be a symlink"):
        export_safe_pack(root, manifest, output)

    assert list(outside.iterdir()) == []


def test_secret_preflight_preserves_existing_output(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    token = "Bearer " + "a" * 28
    (bundle / "normalized" / "system_snapshot.json").write_text(
        json.dumps({"record_count": 1, "records": [{"authorization": token}]}),
        encoding="utf-8",
    )
    manifest = build_registry(root, bundle.name)
    output = root / "export"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("existing output", encoding="utf-8")

    with pytest.raises(UnsafeExportError, match="Possible secret pattern"):
        export_safe_pack(root, manifest, output)

    assert sentinel.read_text(encoding="utf-8") == "existing output"
    assert not (output / "system_snapshot.json").exists()


def test_preflight_rejects_raw_entry_marked_safe(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    raw_entry = next(entry for entry in manifest["files"] if entry["source_type"] == "raw")
    raw_entry["safe_to_upload"] = True
    raw_entry["source_type"] = "RAW"
    output = root / "export"

    with pytest.raises(UnsafeExportError, match="Raw evidence cannot be exported"):
        export_safe_pack(root, manifest, output)

    assert not output.exists()


def test_only_literal_true_opts_file_into_export(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    snapshot = next(
        entry for entry in manifest["files"] if entry["bundle_relative_path"] == "normalized/system_snapshot.json"
    )
    snapshot["safe_to_upload"] = "true"

    export_manifest = export_safe_pack(root, manifest, root / "export")

    assert "system_snapshot.json" not in export_manifest["copied_files"]
    assert snapshot["path"] in export_manifest["skipped_files"]


def test_unselected_absolute_path_is_rejected_before_export(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    manifest["files"].append(
        {
            "path": (tmp_path / "private.json").as_posix(),
            "safe_to_upload": False,
        }
    )
    output = root / "export"

    with pytest.raises(UnsafeExportError, match="escapes the audit root"):
        export_safe_pack(root, manifest, output)

    assert not output.exists()


def test_preflight_rejects_case_variant_raw_directory(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    (bundle / "raw").rename(bundle / "Raw")
    manifest = build_registry(root, bundle.name)
    raw_entry = next(entry for entry in manifest["files"] if entry["bundle_relative_path"] == "Raw/states.json")
    raw_entry["safe_to_upload"] = True

    with pytest.raises(UnsafeExportError, match="Raw evidence cannot be exported"):
        export_safe_pack(root, manifest, root / "export")


def test_preflight_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    outside = tmp_path / "private.json"
    outside.write_text('{"record_count":1,"records":[{}]}', encoding="utf-8")
    source = bundle / "normalized" / "system_snapshot.json"
    source.unlink()
    source.symlink_to(outside)
    manifest = build_registry(root, bundle.name)
    output = root / "export"

    with pytest.raises(UnsafeExportError, match="outside the canonical source bundle"):
        export_safe_pack(root, manifest, output)

    assert not output.exists()


@pytest.mark.parametrize("output_name", ["root", "bundle"])
def test_preflight_rejects_output_overlapping_source(tmp_path: Path, output_name: str) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    output = root if output_name == "root" else bundle
    source = bundle / "normalized" / "system_snapshot.json"

    with pytest.raises(UnsafeExportError, match="Export output cannot"):
        export_safe_pack(root, manifest, output)

    assert source.exists()


def test_preflight_rejects_output_that_contains_nested_bundle(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root / "bundles")
    manifest = build_registry(root, f"bundles/{bundle.name}")
    manifest["current_canonical_bundle"] = f"bundles/{bundle.name}"
    source = bundle / "normalized" / "system_snapshot.json"

    with pytest.raises(UnsafeExportError, match="overlap the canonical source bundle"):
        export_safe_pack(root, manifest, root / "bundles")

    assert source.exists()


def test_preflight_rejects_case_variant_alias_of_root(tmp_path: Path) -> None:
    root = tmp_path / "WorkspaceCase"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    output = tmp_path / "workspacecase"
    source = bundle / "normalized" / "system_snapshot.json"
    sentinel = source.read_text(encoding="utf-8")
    if not output.exists() or not output.samefile(root):
        pytest.skip("requires a case-insensitive filesystem")

    with pytest.raises(UnsafeExportError, match="Export output cannot"):
        export_safe_pack(root, manifest, output)

    assert source.read_text(encoding="utf-8") == sentinel


def test_preflight_rejects_case_variant_descendant_of_bundle(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest = build_registry(root, bundle.name)
    case_variant_bundle = root / bundle.name.upper()
    output = case_variant_bundle / "export"
    source = bundle / "normalized" / "system_snapshot.json"
    sentinel = source.read_text(encoding="utf-8")
    if not case_variant_bundle.exists() or not case_variant_bundle.samefile(bundle):
        pytest.skip("requires a case-insensitive filesystem")

    with pytest.raises(UnsafeExportError, match="overlap the canonical source bundle"):
        export_safe_pack(root, manifest, output)

    assert source.read_text(encoding="utf-8") == sentinel
    assert not output.exists()


def test_export_disambiguates_case_variant_reserved_name(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    source = bundle / "normalized" / "readme.md"
    source.write_text("source readme payload", encoding="utf-8")
    manifest = build_registry(root, bundle.name, safe_names={source.name})
    output = root / "export"

    export_manifest = export_safe_pack(root, manifest, output)

    assert export_manifest["copied_files"] == ["normalized__readme.md"]
    assert (output / "normalized__readme.md").read_text(encoding="utf-8") == "source readme payload"
    assert (output / "README.md").read_text(encoding="utf-8").startswith("# Home Assistant Audit Safe Export")


def test_export_preserves_case_only_basename_collisions(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    first = bundle / "reports-a" / "Summary.md"
    second = bundle / "reports-b" / "summary.md"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("first payload", encoding="utf-8")
    second.write_text("second payload", encoding="utf-8")
    manifest = build_registry(root, bundle.name, safe_names={first.name, second.name})
    output = root / "export"

    export_manifest = export_safe_pack(root, manifest, output)

    copied = export_manifest["copied_files"]
    assert len(copied) == 2
    assert len({unicodedata.normalize("NFC", name.casefold()) for name in copied}) == 2
    assert {(output / name).read_text(encoding="utf-8") for name in copied} == {
        "first payload",
        "second payload",
    }


def test_export_dry_run_preflights_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "workspace"
    bundle = create_bundle(root)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(build_registry(root, bundle.name)), encoding="utf-8")
    output = root / "export"

    exit_code = main(
        [
            "export-safe",
            "--root",
            str(root),
            "--manifest",
            str(manifest_path),
            "--output",
            str(output),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert "PASS safe export preflight" in capsys.readouterr().out
    assert not output.exists()
