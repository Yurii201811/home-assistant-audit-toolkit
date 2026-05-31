from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_output(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def export_safe_pack(root: Path, manifest: dict[str, Any], output: Path, *, clean: bool = True) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    if clean:
        clean_output(output)
    else:
        output.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []
    for entry in manifest.get("files", []):
        if not entry.get("safe_to_upload"):
            skipped.append(entry.get("path", ""))
            continue
        rel_path = entry.get("path")
        if not rel_path:
            continue
        source = root / rel_path
        if not source.exists() or source.is_dir():
            skipped.append(rel_path)
            continue
        export_name = source.name
        if export_name in copied:
            export_name = rel_path.replace("/", "__")
        shutil.copy2(source, output / export_name)
        copied.append(export_name)

    export_manifest = {
        "schema_version": 1,
        "exported_at": utc_now(),
        "source_bundle": manifest.get("current_canonical_bundle"),
        "copied_files": copied,
        "skipped_files": skipped,
        "privacy_note": "Review files before upload. Raw files are excluded by default.",
    }
    write_json(output / "safe_export_manifest.json", export_manifest)
    (output / "README.md").write_text(build_readme(export_manifest), encoding="utf-8")
    return export_manifest


def build_readme(export_manifest: dict[str, Any]) -> str:
    files = "\n".join(f"- `{name}`" for name in export_manifest.get("copied_files", [])) or "- none"
    return (
        "# Home Assistant Audit Safe Export\n\n"
        "This folder is a flat, upload-oriented subset of a Home Assistant audit bundle.\n\n"
        f"- Source bundle: `{export_manifest.get('source_bundle')}`\n"
        f"- Exported at: `{export_manifest.get('exported_at')}`\n\n"
        "## Included Files\n\n"
        f"{files}\n\n"
        "## Safety Notes\n\n"
        "- Raw files are intentionally excluded.\n"
        "- Review this folder before sharing it with an assistant or teammate.\n"
        "- Treat entity IDs, areas, device names, and state summaries as potentially private.\n"
    )

