## Why

The accepted local runtime is 95 upstream commits behind and carries older PR revisions. Refresh it without losing pooled Desktop usage, context ownership, routing safeguards, or access to its existing database.

## What Changes

- Rebuild the local integration from a pinned upstream main and explicitly selected PR revisions.
- Preserve accepted local migration ancestry and prove upgrades from the deployed schema.
- Record included, superseded and held inputs in an immutable source manifest.
- Retain the accepted Desktop relay and pooled usage contracts throughout integration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: compose existing marker authentication and input-shape proof without breaking predecessor v2 verification.
- `deployment-installation`: a local integration upgrade recognizes deployed revision ancestry and preserves persistent state and accepted client endpoints.

## Impact

Local aggregate source and image, Alembic ancestry, current upstream dependencies/native helper/dashboard, proxy composition, and deployment verification. Upstream PR merging and policy choices remain separate.
