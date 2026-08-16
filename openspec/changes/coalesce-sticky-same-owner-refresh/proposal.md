# Coalesce same-owner sticky refresh writes

## Why

The sticky-session upsert is the single most expensive statement in a production
deployment: over 10 days of `pg_stat_statements` it accounted for 44% of total
database execution time (1,203,934 calls, mean 32.1ms, stddev 259.9ms, max 23.2s,
zero I/O time). The table itself is small (26MB / 27k rows) and healthy; the cost
is row-lock serialization. Every request that retains its pinned owner on a
TTL-based mapping (`prompt_cache`) re-executes
`INSERT ... ON CONFLICT (key, kind) DO UPDATE SET account_id = ..., updated_at = now(), ...`
purely to advance `updated_at`. Concurrent requests of one hot session hit the
same `(key, kind)` row and queue on its row lock through each other's commits,
which produces the heavy tail (stddev 8x the mean) and burns wall-clock time on
the TTFT-critical selection path.

## What Changes

- The owner lookup that selection already performs per request now also reports
  whether the row was observed fresh: `updated_at` within
  `min(15s, 1% of the mapping TTL)` AND no abandonment marker in either
  `continuity_abandoned_at` or `continuity_abandonment_scope`.
- When selection retains the same pinned owner and that flag is set, the
  same-owner refresh upsert is skipped entirely — no statement, no row lock.
  The next request after the window closes performs the normal write-through
  refresh.
- Every state-changing write is unaffected and still immediate: rebinding to a
  different account, deleting a mapping, restoring after failed admission,
  clearing an abandonment tombstone, seeding a new mapping, and the raw legacy
  owner paths. A row carrying any abandonment marker is never skippable because
  the upsert also clears those marker columns.
- The flag is DB-observed within the same request (no cross-request cache), so
  it is correct with any number of workers or replicas: a replica can only skip
  a write whose freshness it just read from the shared database.

## Freshness window rationale

`updated_at` on `prompt_cache` mappings is consumed by two TTL clocks, both
driven by `openai_cache_affinity_max_age_seconds` (default 1800s): the read-path
expiry in the owner lookup and the background cleanup loop. Skipping a refresh
while the row is younger than `min(15s, TTL * 0.01)` means a mapping's effective
expiry can move at most that window earlier — at most 1% of the TTL it protects,
and never more than 15 seconds. Sessions with request gaps longer than the
window (the overwhelming majority) still refresh on every request; only bursts
faster than the window coalesce, and those bursts re-refresh within the window
by construction. Durable kinds (`codex_session`, `sticky_thread` without TTL)
never used the refresh-on-retention write and are untouched.

## Impact

- Affected specs: `sticky-session-operations`
- Affected code: `app/modules/proxy/sticky_repository.py`,
  `app/modules/proxy/_load_balancer/sticky_selection.py`,
  `app/modules/proxy/load_balancer.py`
- No new settings, no migration, no dashboard surface. Routing decisions are
  byte-identical; only the redundant same-owner freshness write is coalesced.
- Operators see `updated_at` in the dashboard sticky-session list advance in
  steps of up to the skip window on hot sessions instead of per request.
