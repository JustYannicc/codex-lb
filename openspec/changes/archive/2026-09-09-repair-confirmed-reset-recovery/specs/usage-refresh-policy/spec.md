## ADDED Requirements

### Requirement: Reset recovery preserves concurrent changes and precise evidence

Recovery rollback MUST only restore an account whose status, reason, block markers, plan, and credential still match the recovery write. A failed compare-and-set MUST leave the concurrent account state untouched. Persisted reset evidence MUST select the newest qualifying adjacent pair ordered by observation timestamp and row identifier. SQLite comparisons MUST preserve the subsecond ordering of observations against reset boundaries.

#### Scenario: Operator changes an active account during recovery rollback
- **GIVEN** recovery has activated a blocked account and its usage watermark becomes stale
- **WHEN** an operator changes the active account markers before rollback
- **THEN** rollback leaves the operator's state untouched

#### Scenario: Several reset transitions qualify
- **GIVEN** persisted history contains several valid adjacent transitions after the matching block baseline
- **WHEN** the scheduler resolves reset evidence
- **THEN** it uses the newest qualifying pair for recovery and warm-up

#### Scenario: Baseline observation is just past the reset boundary
- **GIVEN** a SQLite observation occurs a fraction of a second after its old reset boundary
- **WHEN** a later sample advances the reset deadline without a valid re-anchor
- **THEN** that pair does not prove the old boundary was crossed between observations
