## ADDED Requirements

### Requirement: Leader purge of abandoned bridge sessions reconciles owner replicas

When the leader's cleanup purges abandoned durable HTTP-bridge session rows, the system MUST propagate an invalidation signal to all replicas over the existing cache-invalidation bus. Because the purge commits its deletions in batches, the signal MUST be emitted for each committed batch rather than once per purge run, and each signal MUST be persisted synchronously with a retry path when that write fails, so a purge that is cancelled or whose process dies mid-run cannot leave an already-committed batch unsignalled. A signalling failure MUST NOT abort the purge. The signal write MUST be shielded from cancellation: because it runs only after its batch is already committed, a cancellation arriving mid-write MUST be given a bounded grace for the write to land, and MUST fall back to the retry queue when it does not, before the cancellation propagates. A write still blocked at the deadline MUST be ended deterministically rather than left running untracked. The invalidation poller MUST flush queued bumps when it stops, so a retry queued during shutdown is not discarded with the polling task. On that signal each replica MUST reconcile its in-memory bridge sessions against the durable table: a quiescent session — one with no pending or queued work, no admission waiter, no handoff in progress, and no unanchored reservation — whose durable row no longer exists MUST be detached from the session registry and closed. Detaching and tracking the settle work MUST NOT be separated by an await, so a concurrent shutdown cannot observe an empty registry and complete its bridge-cleanup drain before the work is tracked. Every detached orphan's account stream lease MUST be released before any of them are closed, so a slow close (an upstream reader awaiting cancellation) cannot hold other orphans' capacity. Sessions whose durable rows still exist, and sessions with in-flight work, MUST NOT be affected. The reconcile close MUST NOT write account error health and MUST NOT attempt a durable release for the already-purged row.

#### Scenario: Purged orphan releases its stream lease on the owner replica

- **GIVEN** an owner replica holds an in-memory bridge session with no pending work whose durable row the leader purged as abandoned
- **WHEN** the replica observes the `http_bridge_purge` invalidation bump
- **THEN** the session is detached from the registry and closed
- **AND** its account stream lease is released without waiting for the in-memory lease TTL

#### Scenario: Capacity is freed before any close blocks

- **GIVEN** a reconcile detaches several orphans and the first close blocks on an upstream-reader cancellation
- **WHEN** the pass runs
- **THEN** every detached orphan's stream lease is already released while that close is still blocked
- **AND** one orphan's release failing does not strand the others

#### Scenario: Sessions with live durable rows survive the reconcile

- **GIVEN** an in-memory bridge session whose durable row still exists
- **WHEN** the purge invalidation bump is processed
- **THEN** the session remains registered and its lease is untouched

#### Scenario: In-flight work exempts a session from the reconcile

- **GIVEN** an in-memory bridge session with pending requests whose durable row is missing
- **WHEN** the purge invalidation bump is processed
- **THEN** the session is left to its own turn lifecycle and is not closed by the reconcile

#### Scenario: Purge without deletions does not signal

- **WHEN** the leader's abandoned purge deletes zero rows
- **THEN** no `http_bridge_purge` invalidation bump is requested

#### Scenario: Every committed purge batch is signalled

- **GIVEN** an abandoned purge whose deletions span multiple committed batches
- **WHEN** each batch commits
- **THEN** an `http_bridge_purge` signal is emitted for that batch before the purge continues
- **AND** a run interrupted after a batch commits has already signalled that batch

#### Scenario: Shutdown cancellation does not drop a committed batch's signal

- **GIVEN** the cleanup scheduler is cancelled while a committed batch's signal write is in flight
- **WHEN** the cancellation is delivered
- **THEN** the shielded write is drained to completion within the grace before the cancellation propagates
- **AND** the bump is queued for retry if it still did not land

#### Scenario: A failed signal write falls back to the retry queue

- **GIVEN** the synchronous invalidation write fails or raises
- **WHEN** the purge signals a committed batch
- **THEN** the bump is queued for retry on the poller's next cycle
- **AND** the purge continues rather than aborting
