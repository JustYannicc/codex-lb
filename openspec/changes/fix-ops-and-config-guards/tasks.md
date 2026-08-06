# Tasks

## 1. Operational and configuration guards

- [x] 1.1 Set Compose backend stop grace above the application drain deadline and add a rationale comment.
- [x] 1.2 Validate token-refresh exchange timeout values as positive and bounded; include the database exchange term in refresh-claim TTL derivation.

## 2. Quota planner claim recovery

- [x] 2.1 Add completion release and TTL-based reclamation for executing warmup claims.

## 3. Verification

- [x] 3.1 Add Compose grace-period assertion and settings validator regression coverage.
- [x] 3.2 Add quota-planner stranded-claim reclamation coverage.
- [x] 3.3 Run focused settings and quota-planner suites plus OpenSpec validation.
