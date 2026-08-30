# Tasks

## Specification

- [x] Add the focused retry-circuit delta and context with the process-local vs
  durable/replica-wide ownership boundary.
- [x] Validate the change and all main specs with strict OpenSpec tooling (or
  record the unavailable validator and equivalent checks).

## Implementation

- [x] Normalize elapsed durable cooldowns to the zero sentinel without clearing
  equal/newer active local half-open leases.
- [x] Record the owning session, return only that probe as an elapsed cooldown,
  classify proxy continuity loss as neutral, and preserve genuine upstream
  strikes.
- [x] Order proxy continuity reset lifecycle ownership, detach, disarm, release,
  settlement, and close through cancellation-safe cleanup.

## Coverage

- [x] Cover elapsed/absent rows, real expiry single-flight, owner fencing,
  equal-version and lookup-failure lease retention, and replica-boundary state.
- [x] Cover proxy continuity teardown ordering, cancellation, continuity
  neutrality, and genuine upstream failure through unit and real bridge paths.

## Verification

- [ ] Run affected unit/integration tests, Ruff, formatting, `ty`, architecture,
  diff checks, and exact-head Standards/Input reviews.
