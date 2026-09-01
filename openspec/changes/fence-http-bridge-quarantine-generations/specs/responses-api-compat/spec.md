## MODIFIED Requirements

### Requirement: HTTP bridge quarantine cleanup is generation and identity fenced

The in-memory HTTP bridge quarantine registry MUST allocate generations from a
service-lifetime monotonic counter. Generation values MUST never be reused,
including after per-key removal, TTL/size-cap pruning, registry
reinitialization, or an allocator reset; any allocator reset MUST resume above
every generation already observed during that service lifetime. TTL and
size-cap pruning MUST NOT allow a later arm for a reused session key to receive
a generation already observed by an earlier completion. Each HTTP bridge
session lifetime MUST have an immutable, unique session-identity token
represented by that session object's object identity, distinct from reusable
bridge keys, account IDs, and session headers. Each entry MUST retain only a
weak reference to the session that armed it, so the bounded registry cannot
retain detached websocket sessions until TTL expiry; that weak reference is the
session-identity token used for fallback equality checks.

A primary-key completion MAY clear quarantine only when its completing session
is the current canonical session for a registered key, or when no canonical
primary is registered and the entry's weak owner is the completing session. If
the key is registered to a different session, the canonical registry wins and a
detached predecessor MUST NOT clear any entry or first-strike evidence for that
key, and an ownerless entry MUST remain uncleared when no canonical primary is
registered, regardless of a mutable per-session marker or recycled object id.
The completion MUST capture its immutable session-identity token together with
the primary-key quarantine generation, including an observed absence, before
taking its first await that can arm a replacement entry. Cleanup and equality
checks MUST use only those captured identity and generation/absence values. Only
the exact captured generation MAY be cleared; an observed absence or generation
mismatch MUST leave a raced entry active.

A stale-anchor recovery MUST capture the quarantine generation for its
recovery-origin key before authorization. A matching generation MAY be cleared
on successful completion. An observed absence (`None`) and a mismatched,
expired, pruned, or replaced generation MUST NOT clear an entry armed while the
recovery is in flight. This fence MUST apply when the origin key is distinct
from the completing session's key and when both keys are the same.

For a poison quarantine, the cleanup fence MUST capture the poison provenance
generation, the entry's raw generation, and its eventless-timeout count at the
same observation.
Clearing matched poison provenance MUST retain an inactive first-strike counter
only when both the raw generation and eventless-timeout count advanced after
that capture; a strike already present at capture MUST be reset with the poison
arm. An expired suppressed weaker fence MUST be discarded before cleanup
decides whether a post-capture first strike survives. The same captured-count
rule MUST apply when a durable retry-circuit merge revokes a speculative poison
arm.

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

#### Scenario: Primary completion cannot clear a first strike recorded during settlement

- **GIVEN** a primary completion observes no active quarantine for its key
- **WHEN** retry-circuit settlement yields and another request records the first
  eventless strike for that key before completion cleanup resumes
- **THEN** the completion leaves that inactive first-strike evidence in the
  registry
- **AND** the next eventless timeout can still observe it as the prior strike

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

For this requirement, the canonical full-resend-shape predicate MUST inspect
the decoded Responses request's `input` before durable lookup or replay
projection. It is true for a string with at least 4096 characters, an array
with more than one item, or a one-item array whose compact serialization of the
entire array (`ensure_ascii=true` and no separator whitespace) is at least 4096
characters. Shorter strings and arrays, empty or null input, and any other
shape MUST remain delta-only; exactly 4096 is included and 4095 is not. A
serialization failure MUST classify the one-item array as delta-only. This is
only a payload-shape signal and does not establish durable full-resend proof,
prefix identity, or account-neutral replay safety. Request validation MUST
preserve a client-supplied string's original shape and character length for
this decision; normalizing that string into a one-item array MUST NOT add the
array envelope to its boundary calculation. An internal HTTP bridge
owner-forward hop MUST preserve that original string shape so the owner's
request validation reaches the same classification as the origin. During a
rolling upgrade, when an older origin forwards only a normalized one-item
array and the owner cannot validate the additive exact-body signature, the
owner MUST classify that ambiguous one-item array as delta-only instead of
counting normalization-envelope bytes toward the full-resend boundary.

#### Scenario: Quarantine preserves durable context for delta-only requests

- **GIVEN** a live bridge session is quarantined and its durable anchor is
  available
- **WHEN** a genuine delta-only continuation arrives for that session key
- **THEN** the quarantined live session is excluded from local reuse and
  full-resend anchor injection
- **AND** the request still resolves and receives its durable anchor
- **AND** no account health, routing, or durable ownership state changes

#### Scenario: Legacy owner forwarding does not inflate a raw string

- **GIVEN** an older origin normalized a below-boundary client string into a
  one-item array before forwarding it to a newer owner
- **AND** the forward validates only through the rolling-upgrade legacy
  signature fallback
- **WHEN** the newer owner classifies the request shape
- **THEN** it MUST treat the ambiguous one-item array as delta-only
- **AND** it MUST retain the durable previous-response anchor
