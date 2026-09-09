# Aggregate source verification

Pinned upstream base: `f1ff7c7c3309a478a998bd1c66159affd7aed961` (the initial selection snapshot used `efe0f581a18a36f4d491b92a36ef79b0c432d252`). The commit containing this document and `source-manifest.json` identifies the composed candidate. Later deployment receipts must bind its full commit/tree to the image digest and backup. The branch is `codex/integrated-runtime` on the user fork.

## Automated checks

All Python test processes set `CODEX_LB_DATABASE_URL` and `CODEX_LB_TEST_DATABASE_URL` to the same dedicated disposable SQLite database before importing the app. The runner asserts both main and background engine paths. No test used the live database. Interpreter: the worktree's frozen CPython 3.13.5 environment.

- Unit/simulation/request-options gate: **10,039 passed, 99 skipped, one known expected failure**, on the final application code. Skips include unavailable Helm and pre-existing retired/version-specific scenarios. The expected failure records redundant idempotent reservation release calls.
- Integration full pass: **3,397 passed, 13 failed, 360 skipped**. All 13 failures were diagnosed as composition fixtures and repaired. Follow-up proofs passed: all **46 migration tests** (including the four failed cases), all **four draining-owner reservation cases** (including the two failed cases), and all **seven context-prewarm/delayed-terminal cases**. A final combined retest of every repaired case and both already-passing drain variants passed **15 tests**. The full integration suite was not repeated after these test-only repairs. PostgreSQL-only cases and optional environment-specific tests remain skipped.
- E2E: **27 passed, one skipped**. The installed-Codex opt-in profile test remains for deployment acceptance.
- The real WebSocket stale-anchor regression was extended: upstream rejects an injected anchor, then a later request reconnects with the original complete input and without that anchor. **One passed**.
- Ruff, formatting, Ty, architecture, cancellation safety, timing seams and settings-tier checks passed. Strict OpenSpec validation passed for **67 main specs** and the aggregate change.
- The deployment owner independently verified the unchanged frontend tree: frozen install, lint, **1,290 tests in 158 files**, TypeScript and Vite build. The unchanged Rust tree passed formatting, Clippy, **27 tests** and release build. Verified tree IDs: frontend `5db217db36a57f7aa4206739525947ec3eef8731`, crates `6e958360f2c40587e89a8b587af9ff6c8691ef61`, Cargo.lock blob `5e007dd2d611d0c9fe9bb17d7db91ce33db0ae32`.

The delayed-terminal oracle remains intact and is stronger: the fixture uses one shared first-turn placeholder, propagates synthesized-marker registration provenance, and asserts that cleanup revoked the delayed request queue and queued its terminal before releasing the consumer. An ordinary session header generated separate bridge identities for the two requests; reusing one fake socket across those distinct sessions was not the intended sibling-cleanup race.

## Migration proof

All four deployed local migration files listed in the manifest are byte-identical to accepted runtime `1a58a0065010cae81bedd0351792d183761a74cc`. The candidate has one Alembic head, `20260909_220000_merge_local_runtime_refresh`.

A synthetic database upgraded from deployed head `20260905_140000_merge_retry_claim_and_codex_context_heads` retained account/token blobs, API keys, usage, pooled context owners/participants, retry claim receipts and operator settings. The existing upstream migration intentionally normalizes transport sentinel `default` to `auto`; no other old field changed. Schema drift and migration policy checks returned no findings. Separate migration tests prove active receipt downgrade rejection, concurrent claim-write exclusion, branch-only downgrade while retaining current upstream state, and rejection of unowned context tables without changing those tables.

The actual populated deployment backup still needs the owner's isolated container rehearsal. Synthetic migration proof does not claim production acceptance.

## Review and remaining acceptance

The deployment owner reviewed the forwarding composition at `160c03adac4780128a239ee3ebed1981d7e95ef7`, focusing on raw-input proof, old v2 compatibility, epoch fences and pre-dispatch ownership. No functional finding was reported; its documentation precision comment was fixed. The forwarding code has not changed since that review except those comments.

Aggregate Standards/Input review, exact remote-commit image build, populated-backup rehearsal and live Desktop identity/pooled quota/Astra checks remain with the deployment owner. The active change is intentionally not archived. No hosted aggregate CI result, live cutover, production acceptance or upstream merge is claimed here.

## Retained evidence

The local handoff bundle is `/tmp/codex-lb-relevance-audit/`: `container-final-unit-r2.log`, `container-final-integration.log`, `container-final-repaired-proof.log`, `branchmigrationfix1.log`, `branchmigrationfinal.log`, `container-drain-product-path-r2.log`, `container-integration-fixes-r2.log`, `container-final-e2e.log`, `container-denied-anchor-path-r2.log`, `container-final-migration-r4.log`, `container-final-ruff-r3.log`, `container-final-format-r3.log`, `container-final-ty-r5.log`, `container-final-specs.log`, `root-independent-checks.json` and `root-forwarding-review.md`. The source selection, pins, composition repairs, migration hashes and result summary are tracked in Git; the logs are additional local evidence, not future deployment authority.
