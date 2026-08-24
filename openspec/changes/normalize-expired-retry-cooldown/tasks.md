## 1. Specification

- [x] Add the expired-cooldown and future-cooldown requirements.
- [x] Validate the change in strict mode.

## 2. Implementation

- [x] Normalize non-positive durable cooldown remaining time to the zero
      sentinel while preserving future deadlines.
- [x] Add regression coverage proving an elapsed row does not burn a
      half-open probe lease.

## 3. Verification

- [x] Run focused retry-circuit tests, Ruff, and `git diff --check`.
