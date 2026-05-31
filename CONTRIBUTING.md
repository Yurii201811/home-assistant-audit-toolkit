# Contributing

Home Assistant Audit Toolkit is a read-only audit and privacy-boundary project.
Contributions should improve source traceability, validation, and safe export
workflows without encouraging risky live Home Assistant edits.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

## Guidelines

- Keep the toolkit read-only by default.
- Do not add live mutation commands.
- Do not commit real Home Assistant bundles, entity names, tokens, logs, QR
  codes, dashboards, screenshots, or local exports.
- Keep sample data fake and small.
- Treat raw files as private evidence and normalized/report files as derived
  analysis inputs.
- Update docs when bundle layout, privacy rules, or validation behavior changes.

## Pull Request Checklist

- Tests pass.
- No private Home Assistant data is committed.
- Sample workflow still works.
- Safe exports still exclude raw files.
- Secret scanning patterns are updated when needed.

