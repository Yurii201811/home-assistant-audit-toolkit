from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exporter import export_safe_pack, plan_safe_pack
from .io import read_json, write_json
from .registry import build_registry
from .secret_scan import scan_path
from .validator import validate_bundle


def command_build_registry(args: argparse.Namespace) -> int:
    manifest = build_registry(args.root, args.bundle)
    write_json(args.output, manifest)
    print(args.output)
    return 0


def command_export_safe(args: argparse.Namespace) -> int:
    manifest = read_json(args.manifest)
    if args.dry_run:
        plan = plan_safe_pack(args.root, manifest, args.output)
        print("PASS safe export preflight")
        print(f"would copy {len(plan.files)} file(s) to {plan.output}")
        for planned_file in plan.files:
            print(f"- {planned_file.bundle_relative_path} -> {planned_file.export_name}")
        print("No files were written.")
        return 0
    export_manifest = export_safe_pack(args.root, manifest, args.output, clean=not args.no_clean)
    print(args.output)
    print(f"copied {len(export_manifest['copied_files'])} file(s)")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    manifest = read_json(args.manifest)
    result = validate_bundle(args.root, manifest, export_dir=args.export_dir)
    if result.ok:
        print("PASS Home Assistant audit bundle validation")
    else:
        print("FAIL Home Assistant audit bundle validation")
        for error in result.errors:
            print(f"- {error}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")
    else:
        print("Warnings: none")
    return 0 if result.ok else 1


def command_scan_secrets(args: argparse.Namespace) -> int:
    findings = scan_path(args.path)
    for finding in findings:
        print(f"{finding.path}:{finding.line}")
    return 1 if findings else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ha-audit-toolkit", description="Read-only Home Assistant audit bundle tools.")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-registry", help="Build source registry manifest for an audit bundle.")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--bundle", required=True)
    build.add_argument("--output", type=Path, required=True)
    build.set_defaults(func=command_build_registry)

    export = sub.add_parser("export-safe", help="Create a flat upload-safe export pack.")
    export.add_argument("--root", type=Path, required=True)
    export.add_argument("--manifest", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--no-clean", action="store_true", help="Keep unrelated files already in the output directory.")
    export.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full safety preflight and show the copy plan without writing files.",
    )
    export.set_defaults(func=command_export_safe)

    validate = sub.add_parser("validate", help="Validate bundle and optional safe export.")
    validate.add_argument("--root", type=Path, required=True)
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--export-dir", type=Path)
    validate.set_defaults(func=command_validate)

    scan = sub.add_parser("scan-secrets", help="Scan a file or directory for obvious secret patterns.")
    scan.add_argument("path", type=Path)
    scan.set_defaults(func=command_scan_secrets)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
