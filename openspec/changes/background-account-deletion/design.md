## Context

Reference commit: `origin/main` 0c8d9219. Verified surfaces:
`AccountsRepository.delete()` and its fold-state lock comment,
`app/modules/accounts/usage_rollup.py` (lifetime fold, `lock_fold_state`),
`app/modules/accounts/usage_time_rollup.py` (hourly/demand/error/conversation
folds, lifecycle mirrors, history-rewrite discipline), `app/core/retention/`
(chunked prune precedent, BATCH_SIZE=10k), duplicate-account consolidation
(`_reconcile_chatgpt_identity_duplicates`, same fold lock), scheduler + leader
election pattern, Alembic single head `20260812_120000_add_sticky_abandonment_scope`.

Production measurements (10.0.0.113): account deletion = single transaction
holding the fold-state lock for the whole drain; ~93k `usage_history` rows ≈
11.6 s each for two accounts; ~133k `request_logs` soft-detach = 313 s (18
indexes ≈ 8.3 GB, every row non-HOT); fold blocked; 73 pool timeouts in 36 h;
HTTP client timeout on the DELETE call.

## Goals / Non-Goals

**Goals:**

- DELETE API returns in milliseconds; the account is immediately invisible to
  listings and unroutable.
- Bulk row work proceeds in bounded background transactions (5k rows each) so
  the fold, the pool, and vacuum are never blocked for minutes.
- Same end state as the synchronous delete for both `delete_history`
  variants, including the folded-bucket lifecycle mirrors and the
  "rollup row deleted with the account row" invariant.
- Restart-safe resume, idempotent repeat requests, explicit supersede path.

**Non-Goals:**

- No change to duplicate-account consolidation (still synchronous under the
  fold lock; its row volume is bounded by the duplicate's history and it must
  stay atomic with the identity swap).
- No change to retention, fold cadence, or watermark semantics.
- No new settings; no dashboard UI for drain progress (the account is simply
  gone; the worker logs outcomes).

## Decisions

### D1: Terminal mark = existing `DEACTIVATED` status + marker columns, not a new enum value

Serving-path exclusion lists are written as denylists
(`status not in (REAUTH_REQUIRED, DEACTIVATED, PAUSED)` in
`proxy/helpers.py`, `load_balancer.py`, `account_cache.py`, `proxy/api.py`,
`realtime_live.py`): a new `DELETING` enum value would be *routable* until
every denylist was found and extended, and would require a PostgreSQL enum
migration. Reusing `DEACTIVATED` inherits every existing exclusion (sticky
purge, bridge close, selection caches) with zero new status handling. The
pending-deletion state itself lives in `accounts.delete_requested_at`
(authoritative marker + queue ordering) and `delete_history_requested`
(variant, frozen at request time); `deactivation_reason="pending_deletion"`
is operator-facing only.

### D2: The account row is the queue (no new table)

The marker columns make the `accounts` row its own durable work item: the
worker scans `delete_requested_at IS NOT NULL`, progress is the shrinking
`WHERE account_id = :id` predicates, and finalization's row delete is the
dequeue. Restart resume and idempotency need no extra state machine; a
crash between any two chunk transactions loses nothing.

### D3: Chunks do NOT take the fold-state lock; only finalization does

The single-transaction delete held the fold lock to prevent an in-flight
fold slice from committing pre-delete attribution after the mirrors ran
(resurrecting folded rows). The chunked drain preserves that invariant with
lock-free chunks because:

1. Chunk transactions touch only raw rows; they never write a rollup table
   or move a watermark (`usage_history` tables are not fold-governed at all).
2. An interleaved fold slice aggregates either still-attached rows (folded
   under the account dimension) or already-detached rows (folded under the
   orphaned-deleted dimension — the soft-path end state). Both converge at
   finalization: it takes `lock_fold_state()`, detaches/deletes residual raw
   rows, and runs the lifecycle mirrors, which move or remove EVERY folded
   row carrying the account dimension — including rows folded mid-drain.
3. Every fold slice holds the fold-state row lock (`FOR UPDATE` on the
   `account_usage_rollup_state` row) from before it reads raw rows until its
   commit. A slice therefore commits strictly before finalization (its
   output is mirrored) or strictly after (it sees no attributed raw rows).
   Post-finalization resurrection is impossible.

Per-chunk fold-lock acquisition was considered and rejected: it adds fold
stalls proportional to drain length while providing nothing the finalization
lock does not already guarantee (the mirrors are a pure dimension move over
whatever is folded at mirror time).

The letter of the history-rewrite discipline in `usage_time_rollup.py`
("mutations of folded dimensions below the watermark take the fold lock and
mirror or skip **in the same transaction**") is relaxed for this one path:
mid-drain, folded buckets may still attribute to an account whose raw rows a
chunk already detached. That intermediate state never double- or
under-counts a read (folded side serves below-watermark, raw tail above) and
is bounded by drain duration; the end state is byte-identical to the
synchronous path. The module docstring of `deletion.py` documents this as
the single sanctioned exception, converged by finalization.

### D4: Finalization reuses `AccountsRepository.delete()` with a marker guard

`delete(only_pending=True)` is the historical transaction verbatim —
identity-membership lock (PostgreSQL), fold-state lock, residual
usage-history delete, residual detach/delete + mirrors, sticky + rollup +
account row — plus: it aborts (touching nothing) unless the marker is still
set, and it reads the `delete_history` variant from the persisted flag
rather than the caller. The identity-membership `FOR NO KEY UPDATE` row lock
(PostgreSQL) keeps the marker stable through the transaction; on SQLite the
writer section serializes writers. Lock order (identity → fold) matches
consolidation, so no new deadlock ordering is introduced. Residual rows also
cover stragglers: a stream that started before the mark settles its
request-log row at stream end, possibly after every chunk ran.

### D5: Supersede-by-replacement, first-request-wins idempotency

`_apply_account_updates` (every credential replacement: re-import, reauth,
slot reuse) clears the marker: account ids are deterministic, so
delete-then-reimport lands on the marked row, and letting the worker delete
a just-reimported account would be data loss. Every chunk transaction and
finalization re-read the marker under the account row lock (PostgreSQL
`FOR NO KEY UPDATE`, compatible with the `KEY SHARE` taken by concurrent
rollup FK inserts; on SQLite the writer section serializes writers), so a
replacement either commits before the marker read (the chunk sees the
cleared marker and stops) or blocks until the chunk commits — no chunk can
mutate rows after a replacement has successfully returned, and a superseded
account is never finalized (rows already drained stay detached — history
loss was requested by the earlier delete). The chunk takes only the account
row lock and touches only that account's child rows, so no new lock ordering
is introduced. Marked accounts are also absent from the credential-export
endpoints: the synchronous delete made exports 404 immediately, and the
asynchronous drain window must not keep decrypted tokens retrievable after
a successful DELETE. Repeat DELETE requests return
success without escalating `delete_history` (first request wins), matching
the synchronous world where a second DELETE arrived after the account was
already gone. `reactivate_account` treats a marked account as not found
rather than racing the worker back to ACTIVE.

### D6: Worker = leader-gated 30 s tick + local wake, cheap pre-check, round-robin pass

Same scheduler shape as retention. Each tick runs one `LIMIT 1` existence
probe *before* leader election — served by the partial index
`idx_accounts_delete_requested_at` (`WHERE delete_requested_at IS NOT
NULL`), which is empty in the steady state — so a tick with nothing to do
costs one tiny index probe. `delete_account` wakes the local worker after
commit: on the leader (the single-replica common case) draining starts
immediately; a follower's wake is a no-op and the leader's tick picks the
request up within 30 s. Batch size 5k: measured ~1.2 s/10k `usage_history`
deletes and ~23 s/10k `request_logs` detaches put 5k comfortably under a few
seconds per transaction on the worst table.

A deletion pass round-robins: each round advances every pending account by
at most one full chunk and the pending set is re-scanned between rounds.
A multi-minute drain (the measured 133k-row account is ~27 chunks) therefore
cannot starve another marked account, and a DELETE that lands mid-pass is
picked up by the next round's re-scan rather than waiting for the whole pass
to finish.

### D7: API contract unchanged (`{"status": "deleted"}`)

The dashboard's delete mutation only toasts and refetches the listing, which
already excludes the marked account — the operator-visible contract ("after
DELETE, the account is gone from the list") holds exactly. Returning a new
`"deleting"` status would break any consumer comparing against "deleted"
while conveying nothing actionable: the deletion is irrevocable (modulo
re-import) once the API returns. The spec states row purge is asynchronous.

## Risks / Trade-offs

- **Mid-drain visibility**: statistics pages may briefly attribute folded
  history to the (invisible) account while raw rows are already detached.
  Bounded by drain duration; strictly better than the previous minutes-long
  fold outage.
- **Interleaved folds vs hard delete**: a fold slice between hard-delete
  chunks may fold rows (account and API-key aggregates) that the
  single-transaction path would have deleted first. This is inherent fold
  timing (a fold 1 s before the DELETE captured them under the old code
  too); the account side is removed by the mirrors, and API-key folded sums
  keeping settled traffic is the documented behavior for folded history.
- **Supersede after partial drain**: a re-import that lands mid-drain keeps
  the account but its already-detached rows stay detached. Documented; the
  operator asked for deletion first.
- **Alembic head races**: the revision sits on the current single head;
  parallel PRs adding revisions require the usual head merge.

## Migration

`20260816_000000_add_account_pending_deletion`: adds
`accounts.delete_requested_at` (nullable DateTime),
`accounts.delete_history_requested` (Boolean, `server_default false`), and
the partial queue index `idx_accounts_delete_requested_at`
(`(delete_requested_at, id) WHERE delete_requested_at IS NOT NULL`), with
existence guards and a symmetric downgrade. Existing rows are
untouched (no pending deletions can predate the feature). Rolling upgrade: an
old replica neither sets nor reads the marker; a delete handled by an old
replica is simply the old synchronous delete.
