## Why

On the reference PostgreSQL deployment the dashboard projections bulk
usage-history read returns ~307k rows per call (540 calls over 10 days,
avg 2.54 s, max 56 s, `usage_history` at ~3M rows / 2.8 GB). Live snapshot
ingestion appends usage rows per proxied request, so one busy account's
7-day secondary window holds tens of thousands of rows — yet the projection
consumers only read the recent tail: EWMA depletion/burn rates decay a
sample's contribution by 0.6^n within a few dozen newer samples, the
weekly-pace recent-burn window is 6 hours, and the pace smoothing mean is at
most 240 minutes. Fetching every in-window row burns database reads, row
transfer, and Python row-building for values no consumer can observe.

## What Changes

- Bound the PostgreSQL projections bulk usage-history read to each
  account's newest rows (newest-first per-account row cap) inside the
  existing per-account cutoffs, via one lateral top-N probe per account
  over the existing covering indexes (backward index-only scan that stops
  at the cap or cutoff).
- The dashboard projections caller supplies the cap, sized so every
  consumer-visible value is unchanged (covers the 6-hour recent-burn
  window at a 5-second sample cadence; 12x headroom over the default
  60-second refresh).
- SQLite keeps its shared-floor snapshot cache and ignores the cap, the
  same way it ignores per-account cutoffs.
- No schema change: the existing covering indexes already serve the capped
  probes index-only.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `query-caching`: the projections history bulk read MUST additionally
  bound each account's slice to its newest in-cutoff rows on PostgreSQL;
  under-cap accounts MUST return slices equal to the shared-floor fetch
  after per-account trimming.

## Impact

`app/modules/usage/repository.py` (capped PostgreSQL fetch shape),
`app/modules/dashboard/repository.py` / `app/modules/dashboard/service.py`
(cap plumbed from the projections caller), repository/plan/unit regression
coverage. No API, response-schema, setting, migration, or dashboard UI
change.
