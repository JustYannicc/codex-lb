## Why

SQLite recovery can leave WAL, shared-memory, rollback-journal, or
master-journal files beside the source or output. Installing a recovered file
with those sidecars present can attach stale state to the replacement.

## What Changes

- Remove fixed SQLite sidecars around output dump import and source replacement.
- Match master journals literally so glob metacharacters in a database name
  cannot remove another database's journal.
- Fence final output import and sidecar cleanup with an exclusive SQLite
  transaction, then close every recovery connection before sidecar or database
  renames so Windows can perform the file mutations. Fail closed if the lock or
  any sidecar cleanup cannot complete. If the second replacement rename fails,
  restore the original source path before reporting the error. Closing the
  transaction leaves a bounded post-probe window before the operator CLI's
  renames; all preparation work remains fenced.

The recovery output and backup naming remain unchanged.

## Impact

This is isolated to file-backed SQLite recovery. It adds no migration, setting,
or runtime startup behavior.

## Dependencies

The implementation is self-contained and does not require the SQLite startup
run-state changes from the other local candidate. The hosted Contributors
attribution check is intentionally carried by #1902, which is the sole PR
allowed to change contributor metadata; merge #1902 first (or otherwise satisfy
that check) before merging this PR.
