## Why

An admitted HTTP-bridge Responses stream currently stores upstream events in an unbounded in-memory queue. A paused or slow downstream SSE consumer therefore lets an otherwise bounded request retain every unread event and can exhaust proxy-worker memory.

## What Changes

- Bound each HTTP-bridge request's live downstream event queue with an internal capacity.
- Apply a fixed process-wide byte budget to retained live-event payloads so many
  concurrent sessions cannot multiply the per-queue envelope into worker OOM.
- Make the existing awaited producer enqueue apply backpressure when that queue is full.
- When the process budget is exhausted, fail closed for that queue and record the
  pressure without adding an operator-configurable memory setting.
- Preserve ordered event delivery, terminal settlement, durable spool/replay, disconnect cleanup, and paced-consumer behavior.
- Add deterministic integration coverage for paused, resumed, and paced consumers without adding a user setting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Require bounded live HTTP-bridge event buffering and producer backpressure while preserving delivery and lifecycle contracts.

## Impact

- Affected code: HTTP-bridge request preparation in `app/modules/proxy/_service/http_bridge/request_submit.py`.
- Affected tests: focused HTTP-bridge integration coverage in `tests/integration/test_http_responses_bridge.py`.
- Affected contract: `openspec/specs/responses-api-compat/spec.md` through a change delta.
- No API, setting, dependency, migration, dashboard, wire-format, or durable-storage change.
