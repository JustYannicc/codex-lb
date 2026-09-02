## Context

HTTP-bridge request preparation currently attaches `asyncio.Queue(maxsize=0)` to every live downstream stream. The upstream reader awaits each `put`, but an unbounded queue makes that await non-blocking regardless of downstream pace. The same request state also carries terminal events and byte-bounded durable transcript replay, and downstream detachment revokes the mutable queue while the shared upstream reader continues draining the request to terminal settlement.

## Goals / Non-Goals

**Goals:**

- Bound unread live events per HTTP-bridge request and propagate pressure through the existing awaited upstream-reader enqueue.
- Preserve event order, terminal/end-of-stream delivery, reservation and request-log settlement, durable spool/replay, and shared-reader cleanup.
- Make paused, resumed, paced, and detached-consumer behavior deterministic in focused integration coverage.

**Non-Goals:**

- Add an operator setting or reuse the request-admission queue limit for a different unit.
- Change bridge admission, wire events, durable spool byte limits, retry/failover, or account selection.
- Refactor the broader HTTP-bridge lifecycle.

## Decisions

1. **Use a two-event internal live queue.** Request preparation will construct the live queue with capacity for exactly a terminal frame plus its end-of-stream marker. Local startup failures enqueue that pair before the downstream consumer loop begins, so a capacity of one would deadlock submission. The third unread live event blocks the producer; a larger arbitrary count would multiply the existing 16 MiB per-event ceiling without a contract-derived benefit. This is internal flow control rather than an operator policy, so no setting is added.

2. **Make queue revocation unblock a pressured producer.** A request-scoped event will signal that downstream ownership was revoked. Enqueue uses `put_nowait` on the fast path and races only a full-queue `put` against revocation. Dequeue waits on a non-consuming item-ready signal, then removes the item in the consumer task, so cancelling the consumer cannot strand an item removed by a child task. Detachment signals revocation before continuing terminal drain, so a disconnected consumer cannot strand the shared upstream reader or an enqueue task. Terminal settlement and durable persistence continue even when downstream delivery is skipped.
3. **Apply one fixed process-wide byte budget.** Every retained string payload reserves its UTF-8 byte length from a fixed internal 256 MiB envelope before entering a live queue; dequeue releases the reservation. The envelope is deliberately not a setting: queue capacity and upstream payload limits are implementation safety rules. If a reservation cannot be made, that queue revokes producers and fails closed while an attached stream emits its one explicit `response.failed`/`upstream_unavailable` terminal result (or the equivalent HTTP 503), and later upstream failure publication is allowed to no-op on the revoked queue. A pre-consumer queue already revoked by liveness or abandonment is discarded once terminal bookkeeping finishes; this may leave a delayed reader with bare EOS. Durable persistence, settlement, and cleanup continue in every case. The pressure is logged with sizes, without exposing payload content or adding a retry loop.
4. **Size completed durable replay to its already-loaded transcript.** Durable replay is byte-bounded before retrieval and is loaded before the live consumer loop starts. When replay is selected, replace the live queue with a finite queue sized exactly for the retrieved events plus end-of-stream, then enqueue synchronously. This avoids startup deadlock without turning live buffering back into an unbounded queue.
5. **Keep terminal ordering unchanged without blocking cleanup.** Ordinary upstream producer call sites retain their event-then-end-marker order. Failure finalization uses the live queue's existing out-of-band terminal sequence for attached consumers, so it never waits for a stalled consumer while holding session lifecycle ownership. The consumer drains the bounded live deque before the terminal failure and end marker. Queue-full backpressure therefore remains no-drop for an attached consumer, while fail-closed byte-budget revocation has the explicit terminal contract in the change spec.

Alternatives rejected:

- Reusing `http_responses_session_bridge_queue_limit`: it counts admitted requests, not event memory, and would couple unrelated units.
- Reusing durable spool pending-event settings: they govern asynchronous database batching, not downstream live delivery.
- An unbounded queue plus metrics or dropping: neither applies backpressure nor preserves complete Responses streams.
- Replacing the queue with a new channel abstraction: broader than required and riskier across the mature terminal/replay paths.

## Risks / Trade-offs

- **[Head-of-line pressure on the shared upstream socket]** → The response-create gate already serializes active turns; pressure is intentional and bounded to the slow downstream that owns the active response.
- **[Disconnect while a producer awaits capacity]** → Queue revocation wins the enqueue race and all spawned wait tasks are cancelled and awaited.
- **[Concurrent sessions consume the process envelope]** → A failed reservation revokes only the affected queue; already queued payloads remain accounted until consumed, so pressure cannot be hidden by clearing accounting early.
