# Workflow Guide

## Build Registry

```bash
ha-audit-toolkit build-registry \
  --root /path/to/audit-workspace \
  --bundle ha_audit_YYYYMMDD_HHMMSS \
  --output data/home_assistant/current/manifest.json
```

The registry records each file's path, type, privacy level, record count, and
whether it is safe to include in the upload pack.

## Export Safe Pack

Preview and preflight the copy plan first:

```bash
ha-audit-toolkit export-safe \
  --root /path/to/audit-workspace \
  --manifest data/home_assistant/current/manifest.json \
  --output chatgpt_exports/home_assistant_audit_current \
  --dry-run
```

Then create the pack:

```bash
ha-audit-toolkit export-safe \
  --root /path/to/audit-workspace \
  --manifest data/home_assistant/current/manifest.json \
  --output chatgpt_exports/home_assistant_audit_current
```

The export is flat and current-only. Existing files in the output directory are
cleared first unless `--no-clean` is used.

The same safety preflight runs in both modes. It completes before the output is
created or cleaned and blocks canonical-bundle escapes, raw evidence, missing
safe sources, configured secret-pattern matches, and output paths that overlap
source evidence. `--dry-run` prints each source-to-export filename mapping and
writes nothing.

## Validate

```bash
ha-audit-toolkit validate \
  --root /path/to/audit-workspace \
  --manifest data/home_assistant/current/manifest.json \
  --export-dir chatgpt_exports/home_assistant_audit_current
```

Validation fails if required files are missing, counts disagree, the export
points at the wrong bundle, raw files appear in the export, or possible secrets
are found in upload-safe files.
