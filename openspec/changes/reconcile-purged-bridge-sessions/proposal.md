## Why

The leader's abandoned-session purge (`purge_abandoned_before`) deletes durable HTTP-bridge rows whose lease expired, but the owner replica's in-memory session object survives — along with any account stream lease it holds. This is the residual leg of issue #1354's approved design: fix (a) (turn-scoped leases, landed in #1476) removed the structural hold by idle reusable sessions, but an orphaned in-memory session whose durable row the leader purged still occupies registry slots and, in edge paths, a stream-cap slot until the in-memory lease TTL (default 900s) or a restart — the observed "the `http_bridge_sessions` table is empty but the in-memory cap stays full" state.

## What Changes

- After a leader purge deletes one or more abandoned durable bridge rows, it bumps a new `http_bridge_purge` cache-invalidation namespace (the existing cross-replica bus).
- On that bump, every replica reconciles its in-memory bridge sessions against the durable table: a quiescent session (no pending work, no admission waiter, no handoff in progress, no unanchored reservation) whose durable row no longer exists is detached and closed, releasing its account stream lease. Sessions with live rows or in-flight work are untouched.
- The close skips the durable-release round trip (the row is already gone) and performs no account-health writes — identical health semantics to idle eviction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sticky-session-operations`: leader purge of abandoned durable bridge sessions propagates to owner replicas' in-memory state.
