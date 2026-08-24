## ADDED Requirements

### Requirement: HTTP-bridge prewarm terminal outcomes are authoritative

An HTTP-bridge prewarm MUST classify end-of-stream as successful only when its
live queue records ordered clean terminal delivery. Queue revocation, abort,
discard, or process-budget rejection MUST fail the prewarm and MUST release
pending warmup state, response-create admission, retained byte credits, and
prewarmed session state. If a budget failure occurs after the warmup was sent,
the bridge MUST reconnect or close the socket before the warmup leaves pending
ownership, so a late warmup response cannot be matched to another request.

#### Scenario: Prewarm budget failure cannot look like success

- **GIVEN** an HTTP-bridge prewarm is waiting for its queue and an oversized
  warmup event cannot reserve bytes from the process budget
- **WHEN** queue revocation wakes the prewarm consumer with the terminal `None`
  marker
- **THEN** the prewarm MUST be classified as failed rather than successful
- **AND** the warmup request MUST be removed from pending state
- **AND** response-create admission, queue byte credits, and prewarmed session
  state MUST all be released or reset

#### Scenario: A sent budget-failed prewarm fences late frames

- **GIVEN** the warmup request was sent before its queue exceeded the process
  byte budget
- **WHEN** the prewarm fails
- **THEN** the bridge MUST reconnect or close the old socket before cleanup
  releases the warmup's pending ownership
- **AND** a late warmup response MUST NOT be delivered to a later request

#### Scenario: Aborted prewarm terminal settlement cannot look like success

- **GIVEN** terminal processing has claimed a prewarm request from pending
  ownership
- **WHEN** terminal processing aborts and settlement discards the preconsumer
  live queue
- **THEN** the queue end marker MUST be classified as a failed prewarm rather
  than clean completion
- **AND** the caller receives an HTTP 502 error
- **AND** no warmup remains pending, response-create admission is unlocked,
  retained queue byte credits are zero, and the session is not marked prewarmed
