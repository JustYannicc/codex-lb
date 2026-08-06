## MODIFIED Requirements

### Requirement: Executing warmup claims self-heal

An executing warmup decision MUST carry an expiry timestamp. A terminal completion or skip/failure MUST clear that expiry, and a later claim attempt MUST be able to reclaim an expired executing decision atomically so a crashed worker cannot strand daily warmup capacity.

#### Scenario: Stranded claim is reclaimed after its TTL

- **GIVEN** a warmup decision is `executing` and its claim expiry is in the past
- **WHEN** the scheduler evaluates the due warmup
- **THEN** the expired claim is reclaimed and execution can complete
- **AND** the terminal decision has no active claim expiry
