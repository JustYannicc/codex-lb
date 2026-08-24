## Context

The queue change that this PR stacks on bounds live event retention and makes
revocation observable. A prewarm is a special request: it owns a response-create
gate and a pending warmup slot, but it has no downstream stream consuming its
queue. Its terminal marker therefore cannot be interpreted using ordinary
stream success semantics.

## Goals / Non-Goals

**Goals:**

- Make prewarm success depend on an explicit clean terminal outcome.
- Release every warmup-owned resource on failure, including queue byte credits,
  pending membership, admission, and prewarmed session state.
- Fence late frames after a sent prewarm fails its queue budget.

**Non-Goals:**

- Change live-stream queue capacity, process byte-budget limits, or ordinary
  downstream event ordering.
- Change bridge admission, retry policy for ordinary requests, account
  selection, or durable storage.

## Decisions

1. **Use the queue's terminal outcome as the prewarm contract.** `None` is
   success only when the queue records `CLEAN`; revocation, abort, discard, and
   budget exhaustion are failures. The prewarm caller reports an upstream
   failure instead of manufacturing a successful session state.
2. **Reconnect after an already-sent budget failure.** If the warmup frame was
   sent before the queue failed closed, reconnect while the warmup remains
   pending, then perform normal cleanup. This prevents a late warmup response
   from being consumed by a later request on the old socket.
3. **Keep cleanup owned by the existing interruption path.** The new outcome
   check selects the failure classification; the existing cleanup releases the
   gate, pending state, queue credits, and session state. Reconnect failure
   marks the session closed and remains visible to the caller.

## Risks / Trade-offs

- **[A prewarm failure briefly occupies a socket during reconnect]** → The
  reconnect is bounded by the existing bridge lifecycle and prevents a stale
  warmup response from corrupting subsequent request ownership.
- **[A queue failure is reported as a 502]** → This is fail-closed behavior;
  retaining a false prewarmed state would be less recoverable.
