# Verification

Public regressions reproduced the original migration-head ambiguity, invalid empty WebSocket close status, retained database checkout during inventory HTTP, and wrong 503 response for a permanent binding conflict. The fixes passed 236 combined Desktop/usage checks and 110 migration controls on disposable SQLite, with PostgreSQL-only cases skipped locally. Hosted PostgreSQL migration and test jobs passed for the first repair candidate, 2bc905f81.

A follow-up expired-token route regression found database connections retained across OAuth HTTP. A detached account and the existing per-operation background repository remove that retention. The route now passes both normal refresh and request-timeout cases; a retry joins the continuing refresh without exchanging the token twice. The reset control run passed 38 cases. The subsequent focused OAuth, migration, guard and CI-contract run passed 22 cases, with four PostgreSQL cases skipped locally. Counts overlap.

The migration fixture's old db_setup dependency reset the database before a guard could run. A public pytest probe reproduced that ordering without opening a database. The corrected fixture validates the explicitly configured codex_lb_test target before creating its engine, and the CI services and Makefile default use that disposable name. The fixture probes reject ordinary, misleading, missing and mismatched database targets.

The timeout suggestion is not a defect: the existing context specifies a ten-second aggregate deadline. The existing GET/POST timeout tests prove cancellation of active and queued refreshes and no consumption. That contract is preserved.

Ruff, full type and architecture checks, main specifications and repair deltas passed. Current-head hosted checks and review remain owned by the PR repair task until its explicit readiness handoff. No real credit, live database, Docker service or routing configuration was changed. Hosted results do not establish live Desktop acceptance.
