## 1. Terminal outcome contract

- [x] 1.1 Record clean, aborted, revoked, discarded, and budget-exceeded queue
      outcomes without changing ordinary event ordering
- [x] 1.2 Make prewarm success conditional on a clean end-of-stream marker and
      successful terminal settlement
- [x] 1.3 Return HTTP 502 for aborted or cancelled terminal settlement, even
      when clean end-of-stream was already delivered

## 2. Failure cleanup and socket ownership

- [x] 2.1 Release pending warmup, response-create admission, queue byte credits,
      and prewarmed session state for every non-clean outcome
- [x] 2.2 Reconnect an already-used bridge socket before cleaning up a sent
      budget-failed prewarm
- [x] 2.3 Add regression coverage for budget failure, late-frame fencing,
      claimed-terminal abort, and cancellation after clean delivery
- [x] 2.4 Keep settlement signaling and prewarm commit state aligned across
      `request_submit.py`, `upstream_events.py`, and `support.py`

## 3. Verification

- [x] 3.1 Run focused HTTP-bridge queue and prewarm tests
- [x] 3.2 Run changed-file diagnostics, Ruff, type checks, and strict OpenSpec
      validation
- [x] 3.3 Review the diff for stale-anchor, SQLite, source-routing, and
      unrelated queue behavior leakage
