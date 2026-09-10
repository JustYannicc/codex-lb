## Verification and repair

- [x] Reconcile upstream main and verify one migration head with preserved data.
- [x] Reproduce and fix inventory connection retention and binding conflict responses through the existing reset route.
- [x] Verify relay close handling, lifecycle cleanup and independent quota expectations.
- [x] Run affected checks and inspect hosted checks against the pushed candidate.

- [x] Verify expired-token inventory refresh releases database connections across OAuth HTTP.
- [x] Guard destructive PostgreSQL test setup before any database reset.
