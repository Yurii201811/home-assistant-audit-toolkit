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

```bash
ha-audit-toolkit export-safe \
  --root /path/to/audit-workspace \
  --manifest data/home_assistant/current/manifest.json \
  --output chatgpt_exports/home_assistant_audit_current
```

The export is flat and current-only. Existing files in the output directory are
cleared first unless `--no-clean` is used.

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

