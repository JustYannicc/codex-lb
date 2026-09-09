## ADDED Requirements

### Requirement: Draining owner-forward rejection can recover only before dispatch

The origin MUST allow local recovery of an owner-forwarded HTTP bridge
`bridge_drain_active` failure only when transport state proves the owner did
not accept the request. The public error code alone MUST NOT change an
ambiguous or acknowledged transport outcome into a rejection. For session,
thread, or turn-state bootstrap requests without `previous_response_id`, a
proven rejection MAY rebind locally, including requests with a turn-state
header. The bootstrap path MUST NOT recover previous-response continuations.
Recovery MUST preserve existing file-owner and continuation-account constraints.

#### Scenario: Pre-dispatch drain rejection rebinds bootstrap request

- **GIVEN** a session, thread, or turn-state bootstrap request has no previous response
- **AND** the owner transport reports a non-200 rejection with `bridge_drain_active`
- **WHEN** the origin evaluates local bootstrap recovery
- **THEN** it may create or reuse a local bridge session under existing account constraints

#### Scenario: Ambiguous drain failure does not rebind

- **GIVEN** the owner transport outcome is ambiguous or already acknowledged
- **AND** the error payload contains `bridge_drain_active`
- **WHEN** the origin evaluates local recovery, with or without a turn-state header
- **THEN** it MUST NOT retry locally

### Requirement: Owner recovery settles the rejected reservation before retry

When a rejected or undispatched owner-forward request recovers locally, the
origin MUST release its original API-key reservation before reserving usage
for the replacement attempt. The origin MUST complete settlement before
applying deferred account-health writes. A settlement failure MUST prevent
replacement dispatch.

#### Scenario: Rejected owner reservation cannot survive successful recovery

- **GIVEN** an owner-forward request carries an API-key usage reservation
- **AND** the owner rejects the request before accepting settlement ownership
- **WHEN** the origin retries locally
- **THEN** the original reservation is released before replacement reservation
- **AND** successful completion leaves no active reservation for either attempt

#### Scenario: Release failure blocks replacement dispatch

- **GIVEN** the rejected owner request still owns its original reservation
- **WHEN** releasing that reservation fails
- **THEN** the origin does not reserve or dispatch a replacement attempt
