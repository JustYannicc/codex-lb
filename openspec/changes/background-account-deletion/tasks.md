## 1. Schema

- [x] 1.1 Add `accounts.delete_requested_at` and
      `accounts.delete_history_requested` columns (model + Alembic revision
      `20260816_000000_add_account_pending_deletion` on the current head,
      guarded upgrade/downgrade).

## 2. Fast delete path

- [x] 2.1 `AccountsRepository.begin_delete`: terminal `DEACTIVATED` mark +
      pending marker + sticky/bridge cleanup in one short transaction;
      idempotent, first request freezes the `delete_history` choice.
- [x] 2.2 Hide marked accounts from `list_accounts` / `list_accounts_by_ids`;
      block reactivation of marked accounts; keep the DELETE response
      contract (`{"status": "deleted"}`).
- [x] 2.3 Clear the marker in `_apply_account_updates` so credential
      replacement supersedes a pending deletion.

## 3. Background worker

- [x] 3.1 `app/modules/accounts/deletion.py`: chunked drain
      (usage_history, additional_usage_history, request_logs; 5k rows per
      transaction, marker re-check per chunk, no fold-state lock) for both
      variants.
- [x] 3.2 Finalization via `AccountsRepository.delete(only_pending=True)`:
      historical transaction shape (identity lock → fold-state lock →
      residual rows → mirrors → sticky/rollup/account) plus marker guard and
      persisted-variant read.
- [x] 3.3 Leader-gated scheduler (30 s tick, cheap pending pre-check before
      leader election, local wake from the delete path), wired into the app
      lifespan; post-finalization cache invalidation mirroring the old
      synchronous path.

## 4. Validation

- [x] 4.1 Integration coverage: chunk-boundary drain (both variants), fold
      pass interleaved between chunks (no folded-row resurrection, orphaned
      dimension preserves history), restart resume, straggler row settled
      mid-drain, repeat-request idempotency without variant escalation,
      supersede by replacement (including the drain/finalize race), fast-path
      API contract (immediate hide, 404 reactivate).
- [x] 4.2 Update the existing delete API tests to drive the worker pass;
      keep the direct synchronous `AccountsRepository.delete` coverage.
- [x] 4.3 `ruff check` + `ruff format` + architecture checks + focused
      account/rollup/migration test suites + strict OpenSpec validation.
