# Tasks

## 1. Operational and configuration guards

- [ ] 1.1 Set Compose backend stop grace above the application drain deadline and add a rationale comment.
- [ ] 1.2 Validate token-refresh exchange timeout values as positive and bounded; include the database exchange term in refresh-claim TTL derivation.

## 2. Quota planner claim recovery

- [ ] 2.1 Add completion release and TTL-based reclamation for executing warmup claims.

## 3. Verification

- [ ] 3.1 Add Compose grace-period assertion and settings validator regression coverage.
- [ ] 3.2 Add quota-planner stranded-claim reclamation coverage.
- [ ] 3.3 Run focused settings and quota-planner suites plus OpenSpec validation.
