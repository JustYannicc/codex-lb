# live-usage-ingestion Delta

## ADDED Requirements

### Requirement: Ingestor-owned task failures are settled at completion

Every background task the live usage ingestor creates MUST be settled when it
completes: if the task ends with an exception other than cancellation, the
exception MUST be retrieved at completion time, logged immediately with its
traceback, and recorded in a bounded in-process failure record. An
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
