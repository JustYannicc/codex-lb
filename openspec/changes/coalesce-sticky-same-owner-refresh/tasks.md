# Tasks

## 1. Repository freshness observation

- [x] 1.1 Extend `StickyOwnerLookup` with `refresh_can_be_skipped`, computed only on
      the fresh-row TTL lookup path: `updated_at` within `min(15s, 1% of TTL)` and
      both abandonment marker columns NULL
- [x] 1.2 Keep the flag False on the stale-delete recovery path, on lookups without a
      TTL, and on rows carrying any abandonment marker

## 2. Selection wiring

- [x] 2.1 Thread the flag from `run_sticky_selection_path`'s per-attempt owner lookup
      through `_select_with_stickiness`; reset it when the raw legacy owner shadows
      the namespaced row and when the inner helper re-resolves the owner itself
- [x] 2.2 Skip only the three same-owner pinned-retention refresh persists; rebinds,
      deletes, restores, and seed initialization keep writing immediately

## 3. Verification

- [x] 3.1 Unit tests: skip on fresh same-owner retention, write-through when the flag
      is unset, rebind/departed-owner writes never suppressed, grace-period retention
      honors the window, internal re-resolution resets the flag
- [x] 3.2 Integration tests: flag conditions against the real repository (fresh row,
      TTL-scaled window, marker disqualification, no-TTL lookup), concurrent upserts
      on one `(key, kind)` keep RETURNING/self-write and single-row semantics, a
      skipped refresh never clobbers a concurrent rebind
- [x] 3.3 `uv run pytest tests/unit/test_select_with_stickiness.py
      tests/integration/test_proxy_sticky_sessions.py`, `uv run ruff check`,
      `uv run ruff format --check`, `make typecheck`
- [x] 3.4 `openspec validate coalesce-sticky-same-owner-refresh --strict`
