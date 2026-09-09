## 1. Drain recovery

- [x] 1.1 Preserve actual owner transport outcome; never derive rejection from an error code.
- [x] 1.2 Require pre-dispatch proof for drain bootstrap recovery with or without turn state.
- [x] 1.3 Preserve previous-response and file-owner constraints.
- [x] 1.4 Release the old reservation before recovery and replacement reservation.

## 2. Validation

- [x] 2.1 Prove drain rejection and reservation settlement through actual HTTP transport.
- [x] 2.2 Cover ambiguous and acknowledged outcomes and existing continuity behavior.
- [x] 2.3 Run focused tests, lint, typing, and strict OpenSpec validation; sync and archive.
