# Verification

Pinned target: 9cfce7f21bbad6595acf688be2864f3e466ee5c0. Previous candidate: 250dd214d1f48eaabc7ecd49e0f5b84ef62204b0.

Public CLI and both populated parent tests failed with MultipleHeads before the added merge. CLI upgrade/check now reports one head, valid policy and no schema drift. All ten SQLite migration cases passed; ten PostgreSQL cases skipped locally. The strengthened new pair passed again with two PostgreSQL skips. Hosted Makefile selects this entire file on the dedicated codex_lb_test database.

The broader roles/users/permission/CSRF/guest/reset run passed 70 tests and exposed one stale head-equality assertion. The assertion now requires a single head containing the published credential-reprojection revision. All 16 user-schema cases then passed. These runs overlap and must not be summed. Five added public settings controls passed; the seven guest-generation cases also passed. Both database environment variables used identical dedicated disposable URLs before imports. No real credit or live database was used.

Historical guest merge-only assertions now target their original named merge, retaining the later latest-head drift check. New populated controls retain every user/identity/role/grant column, nonzero generations, settings and complete redemption rows through upgrade and merge-only downgrade/re-upgrade. Missing users receive main's original backfill and reprojection. Published migration blobs remain unchanged.

Ruff, architecture, settings checks, full typing, the strict change validation and all 67 main specifications passed before final documentation synchronization. The migration test file remains cohesive around one guarded database fixture and successive reset-history compositions; its length does not justify duplicating the destructive-database guard.

Independent Medium review identified missing initial redemption-timestamp and final settings comparisons. Both were added and the affected pair passed. The reviewer confirmed the graph parents, main authorization parity, head-ancestry adaptation and hosted PostgreSQL selection. Final review completion and final-head hosted evidence are recorded separately in the immutable PR receipt.
