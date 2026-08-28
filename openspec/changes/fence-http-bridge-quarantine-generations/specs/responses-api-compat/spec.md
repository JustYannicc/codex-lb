## MODIFIED Requirements

### Requirement: HTTP bridge quarantine cleanup is generation and identity fenced

The in-memory HTTP bridge quarantine registry MUST allocate generations from a
service-lifetime monotonic counter. TTL and size-cap pruning MUST NOT allow a
later arm for a reused session key to receive a generation already observed by
an earlier completion. Each entry MUST retain only a weak reference to the
session that armed it, so the bounded registry cannot retain detached websocket
sessions until TTL expiry.

A primary-key completion MAY clear quarantine only when its completing session
is the entry's live owner or is the current canonical session for that key in
the service's primary session registry. A detached predecessor MUST NOT clear a
replacement session's newer primary-key quarantine entry, regardless of a
mutable per-session marker or recycled object id.

A stale-anchor recovery MUST capture the quarantine generation for its
recovery-origin key before authorization. A matching generation MAY be cleared
on successful completion. An observed absence (`None`) and a mismatched,
expired, pruned, or replaced generation MUST NOT clear an entry armed while the
recovery is in flight. This fence MUST apply when the origin key is distinct
from the completing session's key and when both keys are the same.

Quarantine cleanup MUST remain independent from retry-circuit state, account
health, routing score, account eligibility, and durable bridge ownership. A
successful replay MAY clear quarantine without clearing or settling a retry
circuit. TTL and size-cap pruning MUST remain bounded and self-recovering.

#### Scenario: Detached predecessor cannot clear a replacement

- **GIVEN** a predecessor session quarantines a primary bridge key
- **AND** a replacement session becomes the canonical registry value for that
  key and receives a newer quarantine generation
- **WHEN** the detached predecessor completes and runs primary-key cleanup
- **THEN** the replacement's quarantine remains active
- **AND** the replacement generation remains authoritative

#### Scenario: TTL pruning and key reuse do not recycle a generation

- **GIVEN** a recovery observes a quarantine generation for a key
- **WHEN** that entry expires and is pruned, the key is quarantined again, and
  the recovery completes
- **THEN** the new quarantine generation differs from the observed generation
- **AND** the stale recovery cannot clear the new entry

#### Scenario: Observed absence cannot clear a raced quarantine

- **GIVEN** a recovery observes no quarantine for its origin key
- **WHEN** another session quarantines that key before recovery completion
- **THEN** the raced quarantine remains active
- **AND** this holds for both distinct-origin-key and same-key recovery

#### Scenario: Weak identity fences object lifetime

- **GIVEN** two distinct session objects reuse one primary key
- **WHEN** the predecessor completes after the replacement is canonical
- **THEN** cleanup compares weak object identity and leaves the replacement
  quarantine active even if an integer object id would collide

### Requirement: Quarantine selection distinguishes local reuse from durable context

An active quarantine MUST make every live session under its key unavailable for
local session reuse and MUST make that live session count as absent when
determining whether a local bridge can supply an anchor. A full-conversation
resend MAY therefore suppress proxy anchor injection and proceed with its own
untrimmed input. A genuine delta-only continuation MUST retain access to its
durable anchor, because quarantine does not erase durable context and the
request has no equivalent replacement context source. This distinction MUST
not mutate account health, routing, or durable ownership.

#### Scenario: Quarantine preserves durable context for delta-only requests

- **GIVEN** a live bridge session is quarantined and its durable anchor is
  available
- **WHEN** a genuine delta-only continuation arrives for that session key
- **THEN** the quarantined live session is excluded from local reuse and
  full-resend anchor injection
- **AND** the request still resolves and receives its durable anchor
- **AND** no account health, routing, or durable ownership state changes
