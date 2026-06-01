from __future__ import annotations

from pathlib import Path

from ha_audit_toolkit.secret_scan import scan_path, scan_text


def test_scan_text_finds_bearer_token() -> None:
    token = "Bearer " + "a" * 28
    findings = scan_text("Authorization: " + token)

    assert findings


def test_scan_text_skips_marked_fixture_line() -> None:
    token = "Bearer " + "b" * 28

    assert scan_text("Authorization: " + token + " allow-secret-fixture") == []


def test_scan_path_skips_generated_cache_dirs(tmp_path: Path) -> None:
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "token.pyc").write_text("Authorization: Bearer " + "c" * 28, encoding="utf-8")

    assert scan_path(tmp_path) == []
