# Privacy And Export Safety

Home Assistant data is often more revealing than it looks. Entity IDs, area
names, device classes, state history, and integration names can expose routines,
occupancy, security devices, and household layout.

## Defaults

The toolkit uses conservative privacy defaults:

- `raw/` files are high sensitivity and not upload-safe.
- `normalized/entities.json`, `devices.json`, and state snapshots are medium
  sensitivity.
- reports and index files are lower sensitivity, but still require review.
- generated exports include only files marked `safe_to_upload`.

## Secret Patterns

Validation scans for obvious token forms:

- bearer tokens
- access/refresh token URL parameters
- `password`, `secret`, `api_key`, and token assignments
- private key blocks
- Home Assistant long-lived-token-like strings

This scan is a guardrail, not a proof of safety. Manual review still matters.

## Recommended Public Workflow

1. Generate or receive a bundle locally.
2. Build the registry.
3. Validate the bundle.
4. Export the safe pack.
5. Validate the export.
6. Review the safe pack before sharing.

