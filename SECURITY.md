# Security Policy

This project is designed around private Home Assistant evidence. Audit bundles
may include device names, room names, entity IDs, state history, integration
metadata, URLs, and secrets if a collector is misconfigured.

## Reporting

Please report vulnerabilities privately through GitHub security advisories or by
contacting the repository owner through GitHub. Do not include real Home
Assistant tokens, logs, or private audit bundles in public issues.

## Secret Handling

- Do not commit `.env`, tokens, raw bundles, generated exports, local logs, or
  screenshots.
- Rotate Home Assistant long-lived access tokens if they are accidentally
  exposed.
- Review generated safe exports before uploading them to any assistant or third
  party.

## Scope

This toolkit does not perform live Home Assistant mutations. If future features
add live collectors, they should remain read-only and clearly separate raw,
normalized, and upload-safe outputs.

