from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(r"https?://\S*(?:access_token|refresh_token|auth|token|api_key|key)=\S+", re.IGNORECASE),
    re.compile(r"(?i)(?:access_token|refresh_token|api_key|password|secret|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
]


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    pattern: str


def scan_text(text: str, path_label: str = "<memory>") -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(path_label, line_number, pattern.pattern))
                break
    return findings


def scan_file(path: Path, *, root: Path | None = None) -> list[SecretFinding]:
    label = path.relative_to(root).as_posix() if root else path.as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    return scan_text(text, label)

