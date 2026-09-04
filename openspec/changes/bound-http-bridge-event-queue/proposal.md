## Why

An admitted HTTP-bridge Responses stream currently stores upstream events in an unbounded in-memory queue. A paused or slow downstream SSE consumer therefore lets an otherwise bounded request retain every unread event and can exhaust proxy-worker memory.

## What Changes

- Bound each HTTP-bridge request's live downstream event queue with an internal capacity.
- Apply a fixed process-wide byte budget to retained live-event payloads so many
  concurrent sessions cannot multiply the per-queue envelope into worker OOM.
- Make the existing awaited producer enqueue apply backpressure when that queue is full.
- When the process budget is exhausted, fail closed for that queue and record the
  pressure without adding an operator-configurable memory setting. An attached
  stream receives one explicit upstream-unavailable terminal result; a revoked
  pre-consumer queue may be discarded after terminal bookkeeping and expose only
  the public bare-EOS/truncated-stream result.
- Preserve ordered event delivery for attached consumers, terminal settlement,
  durable spool/replay, disconnect cleanup, and paced-consumer behavior.
- Add deterministic integration coverage for paused, resumed, and paced consumers without adding a user setting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Require bounded live HTTP-bridge event buffering and producer backpressure while preserving delivery and lifecycle contracts.

## Impact

- Affected code: HTTP-bridge request preparation, upstream event publication, streaming, shared request state, and
  websocket lifecycle handling in `app/modules/proxy/_service/http_bridge/request_submit.py`,
  `app/modules/proxy/_service/http_bridge/upstream_events.py`,
  `app/modules/proxy/_service/http_bridge/streaming.py`,
  `app/modules/proxy/_service/support.py`, and
  `app/modules/proxy/_service/websocket/mixin.py`.
- Affected tests and fixture boundary: `tests/conftest.py`,
  `tests/integration/test_http_responses_bridge.py`, `tests/unit/test_proxy_http_bridge.py`,
  `tests/unit/test_http_bridge_abort_eos.py`, `tests/unit/test_http_bridge_cancel_drain.py`, and
  `tests/unit/test_http_bridge_terminal_delivery.py`.
- Affected contract: `openspec/specs/responses-api-compat/spec.md` through a change delta.
- No API, setting, dependency, migration, dashboard, wire-format, or durable-storage change.
