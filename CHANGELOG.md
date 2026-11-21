# Changelog

All notable changes to this project are documented here.

## 0.2.0 - 2026-11-21

- Upgraded safe-export manifests to schema version 2 with SHA-256 integrity
  metadata and fail-closed validation for missing, modified, symlinked, nested,
  or unexpected entries.
- Blocked symlinked output roots and `--no-clean` destination aliases before
  writes, including case and Unicode equivalents on APFS-style filesystems.
- Made safe exports fail closed before destination changes: canonical-bundle
  containment, symlink escapes, raw evidence, secret patterns, missing sources,
  and source/output overlap are checked before cleaning or copying.
- Added `export-safe --dry-run` for a no-write preflight and copy-plan preview.
- Added public repository polish: README quality signals, package project URLs,
  GitHub issue templates, and a pull request template.
- Expanded CI coverage to Python 3.11 and 3.12.

## 0.1.0 - 2026-05-31

- Initial public MVP for read-only Home Assistant audit bundle registry,
  validation, secret scanning, and upload-safe export workflows.
- Added fake sample data, privacy documentation, security policy, and tests for
  the core CLI behavior.
