# Fence stale-anchor replay admission with retry-circuit generations

## Why

The retry circuit already records hard-affinity failures durably, and the
stale-anchor recovery path captures that state before preparing a one-shot
account-neutral replay. A lookup followed by a later send is not an admission
decision: another replica or a local failure can advance the same circuit in
between. A delayed claim can therefore dispatch a replay after the circuit has
changed, or a successful response can clear a newer failure.

This is the residual retry-circuit part of PR #1867 after the admission-
generation column and model landed in #1863. It keeps the existing failure
counter and cooldown semantics while making replay admission and reset
explicitly generation-fenced.

## What changes

- Represent the captured durable/local state as a typed immutable snapshot.
- Claim the captured generation with a dialect-guarded SQLite/PostgreSQL
  `RETURNING` compare-and-set so the claim receipt is part of the write.
- Bound the claim and one timeout reconciliation attempt by the caller's
  remaining request deadline; an unresolved reconciliation stays fail-closed.
- Recheck local state both before and after the durable CAS so a same-key local
  failure wins over a delayed replay claim.
- Carry the independent `admission_generation` through local loads and delayed
  failure merges; failure observation timestamps remain merge metadata only.
- Clear a circuit only with the captured timestamp and generation, retain local
  admission state on lookup/CAS failure, and report whether the durable clear
  actually matched.

## Scope and non-goals

This change touches retry-circuit state and its direct durable repository/
coordinator boundary plus the call-site deadline/type plumbing and regression
coverage. It does not add a migration, alter the existing admission-generation
column, change cooldown policy, or include operation, quarantine, replay,
account-routing, attribution, or container work from the other PR lanes.

The stale-anchor recovery behavior remains a partial vehicle for #1867; this
delta does not claim to close that broad PR or either continuity issue wholesale.
