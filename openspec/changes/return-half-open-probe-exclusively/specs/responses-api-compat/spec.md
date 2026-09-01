# responses-api-compat delta

## ADDED Requirements

### Requirement: Hard bridge retry-circuit cooldowns use an explicit zero sentinel

For a hard HTTP bridge key, the proxy MUST load an absent or already elapsed
durable `cooldown_until_epoch` as the in-memory `0.0` sentinel. A real future
durable deadline MUST remain an active monotonic cooldown, and durable failure
counts MUST remain available for admission and later recovery decisions.

#### Scenario: Elapsed durable row does not manufacture a probe transition

- **GIVEN** a durable hard-key row whose cooldown is absent or at/before the
  current wall-clock time
- **WHEN** the row is loaded for retry admission
- **THEN** the local cooldown is `0.0`
- **AND** no half-open lease is created solely because the row was reloaded
- **AND** repeated admissions remain allowed until a real cooldown transition
  occurs

### Requirement: Half-open retry probes are exclusive within their owning process

After a real hard-key cooldown expires, the proxy MUST admit exactly one local
  half-open probe and suppress concurrent local admissions until that probe
  settles. The lease MUST record the owning HTTP bridge session. A probe return
  MUST be accepted only from that owner, MUST leave the durable failure count
  unchanged, and MUST represent the returned probe as an elapsed local cooldown
  so the next admission acquires a fresh lease.

The durable retry row remains the replica-wide source for failure counts and
future cooldown deadlines. The active half-open owner is intentionally
process-local because the owner is the process holding the upstream socket; a
different replica may admit its own local probe after loading an elapsed row.
If a newer durable reset or lower failure count arrives while a local probe is
active, the process MUST retain that active lease and its local failure fence
until the probe settles. A newer durable reset MUST clear stale local detail
only when no local probe is active.

#### Scenario: Real expiry admits one local probe

- **GIVEN** a hard-key circuit at or above the failure threshold with a real
  cooldown that has elapsed
- **WHEN** concurrent local requests ask for retry admission
- **THEN** one request is admitted and owns a half-open lease
- **AND** another request for the same key is suppressed

#### Scenario: Continuity loss returns only the owning probe

- **GIVEN** session A owns the active half-open lease for a hard key
- **WHEN** session B reports a proxy-side continuity-ownership failure
- **THEN** the active lease remains intact
- **WHEN** session A reports that same continuity loss
- **THEN** the lease is returned as an elapsed cooldown
- **AND** the failure count, last upstream failure detail, and durable row are
  unchanged
- **AND** the next local admission acquires one fresh half-open lease

#### Scenario: Replica-wide durable state and local lease state stay distinct

- **GIVEN** two proxy processes load the same future durable cooldown
- **WHEN** either process asks for admission
- **THEN** both honor the durable cooldown
- **AND** after the durable deadline has elapsed, each process may manage only
  its own process-local half-open lease

### Requirement: Proxy continuity reset teardown is ordered and cancellation-safe

When a proxy-owned continuity reset returns a half-open probe, the proxy MUST
hold the session lifecycle ownership while detaching the session from active
bridge routing and marking every pending response-create attempt on that session
as disarmed. It MUST return the probe only after detachment and disarming, then
settle pending requests and close the session through a cancellation-shielded
cleanup path. A late submit MUST NOT append an undisarmed attempt between the
reset's disarm and detach steps. This ordering MUST also apply when an in-place
reconnect fails because its required continuity owner is unavailable. Failure
to release a selected account lease during that terminal cleanup MUST NOT
replace the stable continuity-owner error returned to the client.

#### Scenario: Reset teardown cannot manufacture a circuit strike

- **GIVEN** a proxy-owned continuity reset has an active half-open probe and
  pending response-create attempts
- **WHEN** the reset runs
- **THEN** the session is detached and its attempts are disarmed before the
  probe is returned
- **AND** reader teardown classifies those attempts as settled rather than
  eligible
- **AND** cancellation does not leave the session registered or the probe
  owner unresolved

### Requirement: Retry-circuit failure accounting distinguishes proxy continuity loss

The proxy MUST NOT increment or persist retry-circuit failures for explicitly
identified proxy continuity-ownership loss, including
`continuity_owner_unavailable`, `previous_response_owner_unavailable`,
`previous_response_not_found`, `bridge_previous_response_not_found`,
`bridge_owner_unreachable`, and `bridge_instance_mismatch`. It MUST continue to
increment and persist genuine upstream `stream_incomplete`,
`stream_idle_timeout`, and `clean_close` failures when their attempt is
eligible. Anchor replay and error-provenance policy remain governed by their
existing contracts.

#### Scenario: Proxy continuity loss is neutral

- **GIVEN** an eligible local half-open probe
- **WHEN** the proxy loses continuity ownership
- **THEN** the circuit count does not increase
- **AND** the owner lease is returned when the reporting session owns it

#### Scenario: Genuine upstream failure still opens the circuit

- **GIVEN** two eligible eventless upstream failures for one hard key
- **WHEN** each failure is recorded
- **THEN** the circuit reaches its configured threshold and suppresses later
  admissions with a real cooldown
