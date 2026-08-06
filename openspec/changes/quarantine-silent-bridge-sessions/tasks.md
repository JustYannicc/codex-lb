## 1. Spec

- [x] 1.1 Add the `responses-api-compat` delta requirement: silent/wedged bridge sessions (reattached stream with response events but no `response.created`, or two consecutive eventless-timeout retires) are quarantined — excluded from reuse and from full-resend anchor re-injection — with bounded, account-neutral, self-clearing state; deferred-reasoning live turns and delta-only anchors are explicitly protected.

## 2. Implementation

- [x] 2.1 Add `app/modules/proxy/_service/http_bridge/quarantine.py`: bounded in-memory registry keyed by `_HTTPBridgeSessionKey` (TTL 600s, size cap, prune-on-touch), the wedge-shape predicate, the two trigger recorders, the key-quarantined check, and the completion clear. No settings; module constants only.
- [x] 2.2 Trigger 1 hooks: evaluate the wedge shape over pending requests in `_fail_http_bridge_reader_and_maybe_retire` (upstream_events.py) and over the stale set in `_fail_stale_http_bridge_pending_requests` (request_submit.py).
- [x] 2.3 Trigger 2 hooks: record an eventless strike in both `missing_response_created_timeout` branches of the reader loop (force-retire and ordinary), quarantining at the second consecutive strike; the first stays on the merged #1394 recovery path.
- [x] 2.4 Effect 1: `_http_bridge_session_reusable_for_lookup` (helpers.py) rejects quarantined sessions; `_HTTPBridgeSession.quarantined` flag added in support.py.
- [x] 2.5 Effect 2: in streaming.py, skip `fresh_reattach_can_use_durable_anchor` for full-resend payloads when the key is quarantined, emitting `fresh_reattach_anchor_skipped_quarantined`; delta-only payloads keep the anchor (same boundary as `invalidate-durable-bridge-anchor-after-stuck-timeout`).
- [x] 2.6 Recovery: clear quarantine and strikes on `response.completed` alongside the retry-circuit clear (upstream_events.py); TTL expiry and size cap bound everything else. No durable rows and no account-health writes anywhere in the path.

## 3. Coverage

- [x] 3.1 Unit tests (`tests/unit/test_proxy_http_bridge.py`): wedge-shape predicate truth table (including created-assigned, created-latency, fully-eventless, non-injected, websocket, internal shapes), registry TTL expiry and size bound, two-strike eventless threshold with completion reset, reuse-gate exclusion, reader-failure trigger (positive and deferred-reasoning negative), stale-gate-holder trigger, and a reader-loop regression proving the real `missing_response_created_timeout` path records exactly one strike without quarantining.
- [x] 3.2 Integration regression (`tests/integration/test_http_responses_bridge.py`) modeling #1534: reattach injects the durable anchor, upstream streams reasoning deltas but never `response.created`, the turn fails and the key is quarantined; the next full-resend request is sent unanchored on a fresh path and completes, and the completed response clears the quarantine. Verified the test fails when quarantine is neutralized (third attempt rebuilds the identical wedged reattach).

## 4. Verification

- [x] 4.1 `uv run ruff check app tests` and `uv run ruff format --check` on touched files.
- [x] 4.2 `uv run ty check`.
- [x] 4.3 `uv run python scripts/check_proxy_architecture.py` (no budget raised; new logic lives in un-ratcheted `quarantine.py`).
- [x] 4.4 Targeted suites: `tests/unit/test_proxy_http_bridge.py`, `tests/unit/test_http_bridge_cancel_drain.py`, `tests/unit/test_http_bridge_safe_continuity.py`, `tests/unit/test_responses_streaming_timeout_hardening.py`, `tests/integration/test_http_responses_bridge.py`.
- [x] 4.5 `openspec validate quarantine-silent-bridge-sessions --strict` and `openspec validate --specs`.
