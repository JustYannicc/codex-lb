## 1. Reproduce and reconcile

- [x] 1.1 Pin current PR/main and reproduce public CLI multiple-head failure in a disposable database.
- [x] 1.2 Add populated public migration regression coverage and observe red.
- [x] 1.3 Add a no-op two-parent merge revision without changing either parent.

## 2. Verify and deliver

- [x] 2.1 Verify SQLite and PostgreSQL populated upgrades, merge-only downgrade, roundtrip, single head and drift.
- [ ] 2.2 Run affected ERR controls, lint, typing and strict OpenSpec validation.
- [ ] 2.3 Complete independent Medium review, archive/sync verified specs and push normally.
- [ ] 2.4 Own hosted CI/review until green and acknowledged handoff.
