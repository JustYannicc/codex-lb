# responses-api-compat Delta

## ADDED Requirements

### Requirement: Expired durable retry cooldowns do not consume a half-open lease

When a durable retry-circuit row has an absent or elapsed cooldown, the proxy
MUST load the in-memory cooldown deadline as zero. It MUST NOT interpret that
row as a cooldown that just ended, consume an exclusive half-open probe lease,
or suppress subsequent requests solely because the persisted cooldown elapsed.
Future cooldown deadlines MUST remain represented as a positive in-memory
deadline, with thresholds, backoff, persistence, ownership, and retry
classification unchanged.

#### Scenario: Elapsed cooldown reloads open without a probe lease

- **GIVEN** a hard-affinity durable retry row whose cooldown deadline is in the past
- **WHEN** retry admission loads the row
- **THEN** the in-memory cooldown deadline is zero
- **AND** the half-open lease is zero
- **AND** repeated admission checks remain allowed

#### Scenario: Future cooldown remains enforced

- **GIVEN** a hard-affinity durable retry row whose cooldown deadline is in the future
- **WHEN** retry admission loads the row
- **THEN** the positive cooldown remains enforced until it expires
