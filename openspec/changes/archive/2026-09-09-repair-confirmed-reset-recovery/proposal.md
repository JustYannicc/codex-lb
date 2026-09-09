## Why

PR #2070 can roll back a concurrent operator change, choose an older reset tuple, and accept a timestamp just past a reset boundary on SQLite. Its migration is also missing from the stated deployment impact.

## What Changes

- Preserve a concurrent account change when the recovery rollback compare-and-set misses.
- Select the newest valid adjacent reset transition and preserve subsecond boundary checks.
- Declare the usage-history index migration and join it to the current migration graph without editing historical migrations.

## Capabilities

### Modified Capabilities

- `usage-refresh-policy`: enforce existing reset evidence and concurrent-change guarantees.

## Impact

Background usage refresh and persisted transition lookup change. The usage-history reset lookup gains an index through Alembic. No settings, API, or dashboard changes.
