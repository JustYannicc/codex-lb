## Why

PR 1749 changes the Codex proxy contract for compact-trigger turns, but the PR
head lacks the focused OpenSpec change required for proxy-routing and API-shape
behavior. We need a narrow change record that matches the existing
implementation without broadening scope.

## What Changes

- Document that `POST /backend-api/codex/responses` terminal compaction
  triggers produce exactly one terminal `compaction` item on the internal
  compact wire.
- Document that malformed top-level trigger placement is rejected locally
  before upstream compact handling.

## Impact

- `responses-api-compat` change record only
- No behavior changes beyond the already-implemented proxy contract
