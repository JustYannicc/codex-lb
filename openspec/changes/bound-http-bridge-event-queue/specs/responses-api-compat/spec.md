## ADDED Requirements

### Requirement: HTTP bridge live event buffering is bounded

Each admitted HTTP-bridge Responses request MUST use a finite-capacity in-memory queue for live upstream events. When an attached downstream SSE consumer does not keep pace and that queue reaches capacity, the upstream relay MUST wait for downstream capacity before enqueueing another live event. The relay MUST preserve event order and MUST NOT drop attached-consumer events to relieve pressure.

Across all live HTTP-bridge queues, retained event payload bytes MUST remain within a fixed process-wide internal budget. A payload MUST reserve its UTF-8 byte length before entering a queue and release that reservation when dequeued. If the budget cannot admit a payload, that request's queue MUST fail closed and revoke further producers; the service MUST continue durable persistence, reservation settlement, request logging, and cleanup, and MUST record the pressure without exposing payload content or adding an operator setting.

Downstream detachment or cancellation MUST release any relay wait on that request's full queue so the shared upstream reader and its enqueue tasks do not leak. Revocation of downstream delivery MUST NOT prevent terminal persistence, reservation settlement, request logging, or request/session cleanup.

Completed durable transcript replay MUST remain byte-bounded by the durable spool contract and MUST use finite startup buffering that can hold the selected replay plus its end marker without waiting for a consumer that has not started yet.

#### Scenario: Paused consumer backpressures the live relay

- **GIVEN** an HTTP-bridge request with an attached downstream SSE consumer
- **WHEN** the consumer pauses long enough for the live event queue to reach capacity
- **THEN** the next live upstream enqueue waits without growing the queue beyond its finite capacity
- **AND** resuming the consumer delivers every event in order through the terminal event and end marker

#### Scenario: Paced consumer preserves delivery

- **GIVEN** an HTTP-bridge request whose downstream consumer keeps pace with upstream events
- **WHEN** ordinary and terminal Responses events are relayed
- **THEN** every event is delivered in upstream order
- **AND** reservation settlement, request logging, and request/session cleanup complete under their existing ownership rules

#### Scenario: Detached consumer releases a blocked producer

- **GIVEN** an HTTP-bridge live event enqueue is waiting because its downstream queue is full
- **WHEN** the downstream stream disconnects or is cancelled
- **THEN** the waiting enqueue and every enqueue-owned task terminate without requiring another consumer read
- **AND** terminal persistence, durable spool state, request logging, reservation settlement, and bridge cleanup remain able to complete

#### Scenario: Durable replay starts without a live consumer

- **GIVEN** a completed durable operation has a replayable byte-bounded event transcript
- **WHEN** HTTP-bridge submission selects that replay before the downstream consumer loop starts
- **THEN** the finite replay queue accepts the selected transcript and end marker without deadlock
- **AND** the downstream consumer receives the complete replay in order

#### Scenario: Process byte budget fails closed

- **GIVEN** multiple live HTTP-bridge queues have retained payloads near the fixed process budget
- **WHEN** another payload cannot reserve its UTF-8 byte length
- **THEN** only the affected queue revokes producers and does not retain the rejected payload
- **AND** the retained payloads remain accounted until their queues dequeue them
- **AND** settlement, persistence, logging, and cleanup continue without an operator-configurable memory knob
