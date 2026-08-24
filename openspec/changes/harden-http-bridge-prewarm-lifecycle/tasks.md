## 1. Terminal outcome contract

- [x] 1.1 Record clean, aborted, revoked, discarded, and budget-exceeded queue
      outcomes without changing ordinary event ordering
- [x] 1.2 Make prewarm success conditional on the clean terminal outcome

## 2. Failure cleanup and socket ownership

- [x] 2.1 Release pending warmup, response-create admission, queue byte credits,
      and prewarmed session state for every non-clean outcome
- [x] 2.2 Reconnect an already-used bridge socket before cleaning up a sent
      budget-failed prewarm
- [x] 2.3 Add regression coverage for budget failure, late-frame fencing, and
      claimed-terminal abort

## 3. Verification

- [x] 3.1 Run focused HTTP-bridge queue and prewarm tests
- [x] 3.2 Run changed-file diagnostics, Ruff, type checks, and strict OpenSpec
      validation
- [x] 3.3 Review the diff for stale-anchor, SQLite, source-routing, and
      unrelated queue behavior leakage
