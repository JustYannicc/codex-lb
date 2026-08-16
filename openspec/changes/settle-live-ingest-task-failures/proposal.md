## Why

An ingestor-owned background task (the `live-usage-ingestor` consumer or the
trailing cache-invalidation sleeper) that dies with an exception after its
owner lost track of it — for example a shutdown cancelled between clearing the
singleton and awaiting the task — surfaces only as a nondeterministic
"Task exception was never retrieved" loop warning at garbage-collection time.
In production that hides the failure until an arbitrary later moment; in the
test suite's shared session loop it poisons unrelated tests (issue #1755:
the otel lifespan-drain test and test_proxy_utils' startup-probe assertions
fail together).

## What Changes

- Enroll every task the live-usage ingestor creates in a weak ownership
  registry and attach a done callback that settles the task at completion:
  retrieve its exception, log it immediately with its traceback, and record it
  in a bounded in-process failure handoff.
- Settle each task exactly once (a settled-task registry gates recording) so
  the callback and any external sweep cannot double-report.
- Keep ingestion behavior unchanged: enqueueing, coalescing, throttling,
  shutdown ordering, and the fire-and-forget contract are untouched.
- Test infrastructure (out of spec scope): an autouse fence stops leaked
  ingestor singletons after every test and drains the failure handoff so no
  ingestor task or unretrieved exception crosses a test boundary.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `live-usage-ingestion`: unexpected ingestor-owned task deaths MUST be
  settled at completion — exception retrieved, logged, and recorded in a
  bounded handoff — instead of surfacing as garbage-collection-time
  unobserved-task warnings.

## Impact

`app/modules/usage/live_ingest.py` (task enrollment, done-callback
settlement, bounded failure record), `tests/conftest.py` (leak fence), and
`tests/unit/test_live_ingest_leak_fence.py` (regression coverage). No API,
schema, setting, or dashboard change.
