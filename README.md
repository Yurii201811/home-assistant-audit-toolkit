# Home Assistant Audit Toolkit

[![CI](https://github.com/Yurii201811/home-assistant-audit-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Yurii201811/home-assistant-audit-toolkit/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Read-only source-bundle tooling for Home Assistant audits, validation, and
upload-safe AI review packs.

Home Assistant Audit Toolkit helps operators keep a clean boundary between live
smart-home state, generated audit evidence, and the small subset of files that
are safe to share with an assistant or teammate. It grew from a real audit
workflow, but this repository contains only generic code, fake sample data, and
public-safe documentation.

## What It Does

- Builds a machine-readable source registry for a Home Assistant audit bundle.
- Marks files by source type, privacy level, record count, and upload safety.
- Validates bundle structure, JSON/CSV record counts, export manifests, and
  obvious secret patterns.
- Detects missing, modified, symlinked, or structurally unexpected files in a
  completed safe export.
- Preflights canonical-bundle paths, raw-file exclusion, obvious secret
  patterns, and output location before creating an export.
- Creates a flat upload-safe export pack from normalized files and reports.
- Refuses raw evidence files in safe exports by default.
- Runs entirely read-only against bundle files.

It does not edit Home Assistant, rename entities, change automations, touch
`.storage`, or call live services.

## Project Signals

- Public-safe sample bundle with fake Home Assistant data.
- Tested registry, export, validation, and secret-scan workflow.
- CI checks Python 3.11 and 3.12.
- Explicit privacy and security docs for assistant-upload boundaries.
- MIT licensed and designed as a focused CLI, not a private config dump.

## Why This Exists

Home Assistant investigations often produce a pile of raw API responses,
normalized tables, reports, screenshots, and notes. Without a source registry,
future agents or humans can accidentally:

- cite stale reports instead of current normalized evidence
- upload raw/private data when a smaller safe pack was enough
- treat generated reports as live truth
- miss partial collection warnings
- lose track of which bundle is canonical

This toolkit makes those boundaries explicit.

## Install

```bash
python3 -m pip install -e ".[dev]"
```

## Quick Demo

Build a source registry from the included fake bundle:

```bash
ha-audit-toolkit build-registry \
  --root sample_data \
  --bundle example_bundle \
  --output sample_data/current_manifest.json
```

Validate the source bundle:

```bash
ha-audit-toolkit validate \
  --root sample_data \
  --manifest sample_data/current_manifest.json
```

Preview the exact safe-export copy plan without writing anything:

```bash
ha-audit-toolkit export-safe \
  --root sample_data \
  --manifest sample_data/current_manifest.json \
  --output exports/example_current \
  --dry-run
```

Create the upload-safe export:

```bash
ha-audit-toolkit export-safe \
  --root sample_data \
  --manifest sample_data/current_manifest.json \
  --output exports/example_current
```

`export-safe` fails before creating, cleaning, or copying into the destination
if an upload-safe entry escapes the canonical bundle, resolves through a
symlink outside it, points at raw evidence, or matches a configured secret
pattern.

Validate the completed export:

```bash
ha-audit-toolkit validate \
  --root sample_data \
  --manifest sample_data/current_manifest.json \
  --export-dir exports/example_current
```

Completed exports record SHA-256 hashes for every copied file and the generated
README. Validation fails closed if those files are missing, modified, replaced
by symlinks, or joined by nested directories. These hashes detect accidental
drift; they are not signatures and do not prove who created the pack.

## CLI Commands

```text
ha-audit-toolkit build-registry
ha-audit-toolkit export-safe
ha-audit-toolkit validate
ha-audit-toolkit scan-secrets
```

## Bundle Layout

The expected bundle shape is:

```text
ha_audit_YYYYMMDD_HHMMSS/
  index/
    manifest.json
    progress.json
  normalized/
    system_snapshot.json
    entities.json
    devices.json
    automations.json
    scripts.json
    recommendations.json
  reports/
    00_executive_summary.md
    01_system_overview.md
    09_recommendations.md
```

The toolkit is intentionally tolerant: it reports missing files clearly instead
of pretending every collector produces the same sections.

## Privacy Model

Raw Home Assistant exports can contain names, rooms, entities, device metadata,
state history, URLs, and tokens in logs. This project treats:

- `raw/` as high sensitivity and not export-safe
- `normalized/` as medium sensitivity by default
- `reports/` and index metadata as lower sensitivity after review
- the generated safe export as the only folder intended for assistant upload

You should still review exports before uploading them anywhere.

## Documentation

- [Architecture](docs/architecture.md)
- [Privacy and export safety](docs/privacy.md)
- [Workflow guide](docs/workflow.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](CHANGELOG.md)

## Checks

```bash
python3 -m pytest
python3 -m compileall src tests
```

## Project Status

MVP. The core registry/export/validation workflow is usable, but live collection
is intentionally out of scope for this public repo.
