## Why

The bounded live-event queue can now revoke producers and retain an explicit
terminal state. HTTP-bridge prewarm still treated every end-of-stream marker as
success, so a revoked, aborted, discarded, or byte-budget-rejected warmup could
mark a session prewarmed after its request had already failed. A warmup that
was sent before the budget failure could also leave a late response on the
same socket and be matched to a later request.

## What Changes

- Record the terminal outcome of each bounded live-event queue.
- Treat prewarm end-of-stream as success only for an ordered clean terminal.
- Fail closed and release pending warmup, gate, queue-credit, and session state
  for revoked, aborted, discarded, or budget-exceeded outcomes.
- Reconnect an already-used bridge socket before cleaning up a budget-failed
  prewarm, so late warmup frames cannot contaminate a later request.
- Add deterministic regression coverage for budget and claimed-terminal abort
  paths.

## Dependencies

This change is stacked on `fix/http-bridge-bounded-live-queues` at
`ec48c02e175b0e119778d4928b14526133767823`. It relies on that branch's finite
queue, byte-budget, revocation, discard, and terminal delivery interfaces.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Require failed HTTP-bridge prewarms to release all
  warmup ownership and never report success after a non-clean queue outcome.

## Impact

- Affected code: HTTP-bridge prewarm submission in
  `app/modules/proxy/_service/http_bridge/request_submit.py`.
- Affected tests: focused prewarm lifecycle cases in
  `tests/unit/test_proxy_http_bridge.py`.
- No API, setting, dependency, migration, dashboard, wire-format, or durable
  storage change.
