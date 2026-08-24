## Context

The queue change that this PR stacks on bounds live event retention and makes
revocation observable. A prewarm is a special request: it owns a response-create
gate and a pending warmup slot, but it has no downstream stream consuming its
queue. Its terminal marker therefore cannot be interpreted using ordinary
stream success semantics.

## Goals / Non-Goals

**Goals:**

- Make prewarm success depend on both an explicit clean terminal outcome and
  successful terminal settlement.
- Release every warmup-owned resource on failure, including queue byte credits,
  pending membership, admission, and prewarmed session state.
- Fence late frames after a sent prewarm fails its queue budget.
- Return HTTP 502 when terminal settlement is aborted or cancelled, even if a
  clean end-of-stream marker was already delivered to the prewarm consumer.

**Non-Goals:**

- Change live-stream queue capacity, process byte-budget limits, or ordinary
  downstream event ordering.
- Change bridge admission, retry policy for ordinary requests, account
  selection, or durable storage.

## Decisions

1. **Use queue outcome and settlement as the prewarm contract.** `None` is
   only an end-of-stream marker. The prewarm caller commits success after the
   queue records `CLEAN` *and* the completed-delivery scope reports successful
   terminal settlement. Revocation, abort, discard, budget exhaustion, and
   aborted or cancelled settlement are failures; the caller reports HTTP 502
   instead of manufacturing successful session state.
2. **Reconnect after an already-sent budget failure.** If the warmup frame was
   sent before the queue failed closed, reconnect while the warmup remains
   pending, then perform normal cleanup. This prevents a late warmup response
   from being consumed by a later request on the old socket.
3. **Keep cleanup owned by the existing interruption path.** The new outcome
   and settlement checks select the failure classification; the existing
   cleanup releases the gate, pending state, queue credits, and session state.
   Reconnect failure marks the session closed and remains visible to the
   caller.

## Affected files

- `app/modules/proxy/_service/http_bridge/request_submit.py`: waits for
  terminal settlement before committing prewarm success and maps failed
  settlement to HTTP 502.
- `app/modules/proxy/_service/http_bridge/upstream_events.py`: publishes
  settlement completion and success/failure after terminal cleanup.
- `app/modules/proxy/_service/support.py`: carries the settlement event and
  result on the completed-delivery scope.
- `tests/unit/test_proxy_http_bridge.py`: covers clean-EOS success, aborted
  settlement, and cancellation after clean delivery.

## Risks / Trade-offs

- **[A prewarm failure briefly occupies a socket during reconnect]** → The
  reconnect is bounded by the existing bridge lifecycle and prevents a stale
  warmup response from corrupting subsequent request ownership.
- **[A queue failure is reported as a 502]** → This is fail-closed behavior;
  retaining a false prewarmed state would be less recoverable.
