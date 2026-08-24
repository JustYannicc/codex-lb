## 1. Recovery cleanup

- [x] 1.1 Remove fixed source/output SQLite sidecars around replacement.
- [x] 1.2 Fail closed when sidecar removal cannot complete.
- [x] 1.3 Escape database basenames before matching master journals.

## 2. Verification

- [x] 2.1 Cover stale source/output WAL and journal cleanup.
- [x] 2.2 Cover literal wildcard filename matching.
- [x] 2.3 Run focused recovery tests, Ruff, formatting, and `ty`.
