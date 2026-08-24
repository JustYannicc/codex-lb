## Why

SQLite recovery can leave WAL, shared-memory, rollback-journal, or
master-journal files beside the source or output. Installing a recovered file
with those sidecars present can attach stale state to the replacement.

## What Changes

- Remove fixed SQLite sidecars around output dump import and source replacement.
- Match master journals literally so glob metacharacters in a database name
  cannot remove another database's journal.
- Hold an exclusive SQLite recovery lock across the final import and source
  replacement boundary, failing closed if an active writer prevents the lock.

The recovery output and backup naming remain unchanged.

## Impact

This is isolated to file-backed SQLite recovery. It adds no migration, setting,
or runtime startup behavior.

## Dependencies

None. This focused change is based directly on beta.4 and does not require the
SQLite startup run-state changes from the other local candidate.
