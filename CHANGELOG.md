# Changelog

All notable changes to this project are documented here.

## Unreleased

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
