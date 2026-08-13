## ADDED Requirements

### Requirement: Leader purge of abandoned bridge sessions reconciles owner replicas

When the leader's cleanup purges abandoned durable HTTP-bridge session rows, the system MUST propagate an invalidation signal to all replicas over the existing cache-invalidation bus. On that signal each replica MUST reconcile its in-memory bridge sessions against the durable table: a quiescent session — one with no pending or queued work, no admission waiter, no handoff in progress, and no unanchored reservation — whose durable row no longer exists MUST be detached from the session registry and closed, releasing any account stream lease it holds. Sessions whose durable rows still exist, and sessions with in-flight work, MUST NOT be affected. The reconcile close MUST NOT write account error health and MUST NOT attempt a durable release for the already-purged row.

#### Scenario: Purged orphan releases its stream lease on the owner replica

- **GIVEN** an owner replica holds an in-memory bridge session with no pending work whose durable row the leader purged as abandoned
- **WHEN** the replica observes the `http_bridge_purge` invalidation bump
- **THEN** the session is detached from the registry and closed
- **AND** its account stream lease is released without waiting for the in-memory lease TTL

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
