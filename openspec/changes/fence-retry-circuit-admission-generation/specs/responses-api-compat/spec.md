## ADDED Requirements

### Requirement: Retry-circuit admission uses an immutable generation fence

For a hard-affinity HTTP bridge key, a verified stale-anchor replay MUST capture
the durable retry-circuit state and local admission state in one typed immutable
snapshot. Immediately before queue publication, the replay MUST atomically
claim that snapshot by advancing only `admission_generation`; it MUST compare
the captured durable timestamp, failure count, cooldown, and generation, and it
MUST compare the captured local failure/cooldown state before and after the
durable operation. The claim MUST use a dialect-guarded SQLite/PostgreSQL
`RETURNING` statement so a successful claim receipt is part of the same write.

#### Scenario: A newer same-key local failure suppresses a delayed claim

- **GIVEN** a stale-anchor replay captured a hard-key generation
- **WHEN** a local failure advances that key before the durable claim returns
- **THEN** the post-claim local check MUST reject the replay
- **AND** the failure's local admission state MUST remain installed

#### Scenario: A competing durable claim wins first

- **GIVEN** two replicas captured the same hard-key generation
- **WHEN** one replica advances `admission_generation`
- **THEN** the other replica's conditional claim MUST return no receipt
- **AND** it MUST fail closed without dispatching a second replay

#### Scenario: A timed-out claim is reconciled within the request budget

- **GIVEN** the first durable claim attempt times out
- **WHEN** the request still has budget remaining
- **THEN** the service MAY retry the identical conditional claim once
- **AND** a committed first claim MUST make that retry refuse through the generation fence
- **AND** a second timeout, store error, refusal, or expired deadline MUST remain fail-closed

### Requirement: Retry-circuit settlement is generation-fenced

When a hard-key retry circuit is cleared, the service MUST retain local
admission state if durable lookup fails. A present durable row MUST be cleared
only when both its observed `updated_at_epoch` and `admission_generation` still
match. A conditional-clear refusal MUST report no match and MUST NOT remove
local state. A confirmed durable miss MAY remove a local marker only when no
newer local failure arrived during the lookup. Delayed failure persistence MUST
merge using the existing failure observation metadata without rewriting the
independent `admission_generation`.

#### Scenario: A newer durable failure survives an older success

- **GIVEN** a response captured generation `g`
- **WHEN** another writer records a failure and advances the row before the
  response clears it
- **THEN** the generation-fenced clear MUST return no match
- **AND** the newer durable failure and local admission guard MUST remain

#### Scenario: Durable lookup outage does not erase local protection

- **GIVEN** a local hard-key circuit is installed
- **WHEN** durable lookup raises during successful-response settlement
- **THEN** settlement MUST leave the local circuit and marker sets intact
- **AND** the request MUST not claim that the circuit was cleared
