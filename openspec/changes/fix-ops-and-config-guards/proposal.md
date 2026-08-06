# Fix operational grace and durable claim guards

## Why

The production Compose service can be killed before the application's drain deadline, refresh configuration accepts an unbounded OAuth exchange timeout, and quota warmup claims can remain executing forever after a crash.

## What Changes

- Give the Compose backend a stop grace period above the application drain budget.
- Reject non-positive token-refresh exchange timeouts and make refresh-claim TTL calculation include the database exchange term.
- Make quota-planner executing claims expire and reclaim stranded work, while releasing claims on terminal completion.
- Add focused regression tests for each failure mode.

## Impact

Affected surfaces are Compose deployment configuration, application settings/refresh admission, and quota planner persistence. No public API or migration is intended.
