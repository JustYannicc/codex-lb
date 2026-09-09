# Verification on the rebased implementation

Base: `d3f63331d6ba5e233001fb38c9a059e5a9b681cb`, fetched from upstream main on 2026-09-08. These are scoped local results, not a claim that the full current-head GitHub matrix is green.

## Context and transport

- `pytest tests/integration/test_proxy_transient_retry.py tests/integration/test_codex_context_pool.py tests/integration/test_codex_history_notes.py tests/integration/test_codex_context_dispatch_cost.py tests/unit/test_codex_context_replay.py tests/unit/test_codex_upstream_paths.py tests/simulation/test_proxy_turn_lifecycle_property.py --timeout=60`: 205 passed, 1 skipped, 2 expected failures inherited from the simulation suite. The skipped callback-residue oracle requires CPython 3.14; this local environment uses 3.13.
- After preserving identity on HTTP bridge prewarm and strengthening the native WebSocket parsed-frame assertion, `pytest tests/integration/test_codex_context_dispatch_cost.py tests/integration/test_codex_context_pool.py --timeout=60`: 37 passed.
- The new cases observe actual context SQL on the HTTP route, confirm zero database work for ordinary and repeated dispatches, one participant insert on rotation, durable rejection of a conflicting marked request after cache eviction/clear, no cache publication after a failed commit, and cleanup of all history tasks on an injected deadline or cancellation. The prewarm case asserts the durable key fence before the first send.

## Migrations and PostgreSQL

- `pytest tests/integration/test_migrations.py tests/unit/test_db_migrate.py --timeout=90`: 97 passed, 7 PostgreSQL-only skips on SQLite.
- Against a dedicated temporary PostgreSQL 16 database, `pytest tests/integration/test_codex_context_pool.py tests/integration/test_codex_context_dispatch_cost.py tests/integration/test_migrations.py --timeout=90`: 82 passed.
- The final prewarm case and the four native WebSocket/HTTP bridge quota replay cases passed on PostgreSQL after the final transport adjustment: 5 passed.
- Alembic has a single head, `20260905_120000_add_codex_context_ownership`, parented on current main's `20260908_020000_merge_overflow_transport_heads`. That merge revision includes the subscription-overflow migration from #2165. Schema drift, upgrade/downgrade and rejected-adoption preservation pass on both dialects.

The suites overlap and include reruns; the numbers must not be summed as distinct tests.

## Static checks and specifications

Ruff, formatting and targeted Ty checks pass. `check_proxy_timing_seams.py`, `check_proxy_architecture.py`, `check_cancellation_safety.py` and the beta release guard pass. The beta guard sees no release-managed version delta against main.

The active change and both owning specifications pass strict OpenSpec validation. Whole-repository strict validation reports 37 passing and 22 failing specifications; the failing set matches an untouched export of current main exactly. No unrelated specification is changed to silence those failures.

No production server restart or new live-account test is part of this revision. Earlier live Codex 0.153.1 evidence belongs to the preceding implementation; current validation is the local integration evidence above plus the GitHub checks after publication.
