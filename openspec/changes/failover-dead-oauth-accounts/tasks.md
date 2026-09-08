## 1. Account health

- [x] 1.1 Classify `token_revoked` as a permanent reauthentication failure.
- [x] 1.2 Preserve canonical HTTP 401 mapping for the upstream error spelling.
- [x] 1.3 Classify `token_revoked` through the shared WebSocket authentication-failure code set.

## 2. Scope and regression coverage

- [x] 2.1 Remove the overlapping compact requirement; #2080 owns forced-refresh failover.
- [x] 2.2 Cover revoked-token classification and its use with existing compact account ownership and settlement behavior.
- [x] 2.3 Make the HTTP bridge file-affinity ordering regression hermetic.

## 3. Validation

- [x] 3.1 Run focused unit and integration regressions.
- [x] 3.2 Run lint, type checks, and strict OpenSpec validation.
