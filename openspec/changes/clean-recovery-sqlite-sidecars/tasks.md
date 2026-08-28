## 1. Recovery cleanup

- [x] 1.1 Remove fixed source/output SQLite sidecars around replacement.
- [x] 1.2 Fail closed when sidecar removal cannot complete.
- [x] 1.3 Escape database basenames before matching master journals.
- [x] 1.4 Fence final import and cleanup with an exclusive SQLite lock, then
  close the lock before filesystem renames.

## 2. Verification

- [x] 2.1 Cover stale source/output WAL and journal cleanup.
- [x] 2.2 Cover literal wildcard filename matching.
- [x] 2.3 Cover a write attempt during the fenced preparation boundary.
- [x] 2.4 Cover Windows-style rename behavior with a tracked-handle seam.
- [x] 2.5 Cover partial cleanup and busy-source failures.
- [x] 2.6 Cover second-rename failure and source restoration.
- [x] 2.7 Run focused recovery tests, Ruff, formatting, `ty`, and strict OpenSpec.
