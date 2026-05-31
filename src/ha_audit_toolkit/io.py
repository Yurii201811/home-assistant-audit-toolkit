from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def csv_record_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def json_record_count(payload: Any) -> int | None:
    if isinstance(payload, dict) and isinstance(payload.get("record_count"), int):
        return payload["record_count"]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return len(payload["records"])
    if isinstance(payload, dict) and isinstance(payload.get("files"), list):
        return len(payload["files"])
    if isinstance(payload, list):
        return len(payload)
    return None


def record_count(path: Path) -> int | None:
    if path.suffix == ".csv":
        return csv_record_count(path)
    if path.suffix == ".json":
        return json_record_count(read_json(path))
    return None

