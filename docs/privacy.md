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

## Fail-Closed Export Preflight

Before the output directory is created or cleaned, `export-safe` checks every
candidate file. It refuses the export when:

- the canonical bundle or a candidate path escapes the audit root
- a symlink resolves outside the canonical bundle
- raw evidence is marked upload-safe
- an upload-safe source is missing or is not a regular file
- a configured secret pattern matches an upload-safe source
- the output overlaps the audit root or canonical source bundle

Use `export-safe --dry-run` to run the same preflight and inspect the flat copy
plan without writing files. A passing scan is a guardrail, not proof that the
content is appropriate to share.

## Secret Patterns

Export preflight and validation scan for obvious token forms:

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
