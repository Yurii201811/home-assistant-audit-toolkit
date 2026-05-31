from __future__ import annotations

from ha_audit_toolkit.secret_scan import scan_text


def test_scan_text_finds_bearer_token() -> None:
    findings = scan_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456")

    assert findings

