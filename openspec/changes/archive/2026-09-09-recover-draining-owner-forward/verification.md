# Local verification

Base: upstream/main `f1ff7c7c3309a478a998bd1c66159affd7aed961`.
Source concern: PR2088 `6e6c4c919f19893974da329f553e44f19e928db0`.

The change preserves actual transport outcome, requires pre-dispatch evidence
for drain recovery, and releases the rejected reservation before local
admission. Previous-response drain recovery accepts that evidence only at the
owner-forward call site. Bootstrap recovery never replaces a previous-response
continuation, and file-owner account constraints are passed unchanged.

## Regression evidence

- Original fallback drain allowlist: two failures for ambiguous/acknowledged
  outcomes without turn state. Corrected tests pass.
- Original error-code outcome promotion: two failures through the production
  forwarding wrapper after ambiguous dispatch or receiver acknowledgement.
  Corrected tests pass.
- Original reservation path: the actual HTTP 503 receiver and SQLite key-limit
  test fails with `ApiKeyRateLimitExceededError` while the first reservation is
  still active. With the fix, both reservation rows are released and the limit
  charge is zero. A release failure blocks replacement admission.
- File-pinned variants preserve the required account at recovery admission.

## Checks

- 1,339 tests passed across `test_proxy_http_bridge.py`,
  `test_http_bridge_forwarding.py`, `test_draining_owner_recovery.py`,
  `test_http_promotion_accounting.py`, and `test_http_responses_bridge.py`.
- After the final guard preserving non-drain turn-state behavior, all 47
  affected drain/bootstrap tests passed.
- Full Ruff check and format check passed. Full ty check passed.
- Architecture, cancellation safety, timing seams, and settings-tier checks passed.
- Strict change validation passed; all 64 main specs passed strict validation
  after sync.

All app/test processes set `CODEX_LB_DATABASE_URL` and
`CODEX_LB_TEST_DATABASE_URL` to the same absolute temporary SQLite path before
imports. The test conftest assigns its primary URL from the test URL and
replaces background scheduler builders and leader election with no-ops.

This verifies local behavior. No host database, container, live endpoint, or
GitHub publication was changed.
