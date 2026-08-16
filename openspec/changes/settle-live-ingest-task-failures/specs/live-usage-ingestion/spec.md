# live-usage-ingestion Delta

## ADDED Requirements

### Requirement: Ingestor-owned task failures are settled at completion

Every background task the live usage ingestor creates MUST be settled when it
completes: if the task ends with an exception other than cancellation, the
exception MUST be retrieved at completion time, logged immediately with its
traceback, and recorded in a bounded in-process failure record as
traceback-free metadata (task name and exception representation) so the
record cannot retain the failed task's object graph. An
ingestor-owned task failure MUST NOT surface as a garbage-collection-time
unobserved-task warning. Each task MUST be settled exactly once, including
when an external supervisor (such as test infrastructure) also observes the
task. Settlement MUST NOT extend task lifetime, change ingestion behavior, or
affect the serving path.

#### Scenario: Detached consumer death is logged deterministically

- **GIVEN** a consumer task whose owner lost track of it (for example a stop
  cancelled between clearing the singleton and awaiting the task)
- **WHEN** the task dies with an exception
- **THEN** the exception is retrieved and logged at completion time
- **AND** it is recorded in the bounded failure record
- **AND** no unobserved-task warning fires at garbage collection

#### Scenario: Cancelled tasks settle silently

- **WHEN** an ingestor-owned task ends by cancellation
- **THEN** settlement records no failure and logs no error

#### Scenario: Failure record stays bounded

- **WHEN** ingestor-owned tasks fail repeatedly without the record being
  drained
- **THEN** the failure record retains at most its fixed capacity of entries
- **AND** every failure is still logged

### Requirement: Ingestor lifecycle is instance-scoped

Each application lifespan MUST hold the ingestor instance its startup created
and stop exactly that instance at shutdown. Stopping an instance MUST clear
the process-wide singleton registration and the publisher hook only when the
stopped instance still owns them. When several lifespans are live in one
process, no lifespan's startup or shutdown may orphan another lifespan's
running ingestor or leave it without a stop path.

#### Scenario: Nested lifespan cannot orphan the outer ingestor

- **GIVEN** an app whose lifespan started ingestor A
- **WHEN** a nested lifespan starts ingestor B (taking over the singleton and
  publisher) and later stops it
- **THEN** ingestor A keeps running, strongly rooted by its own lifespan
- **AND** the outer lifespan's shutdown stops ingestor A and its tasks even
  though the singleton no longer points at A
