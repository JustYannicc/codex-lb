"""Background account deletion: fast-marked accounts drained in bounded chunks.

``DELETE /api/accounts/{id}`` used to detach (or delete) the account's entire
raw history in ONE transaction while holding the fold-state lock: for a
long-lived account that is hundreds of thousands of rows across ``request_logs``
(18 indexes) and ``usage_history``, minutes of fold blockage, one pinned pool
connection, and an HTTP client timeout. The API now only stamps the
pending-deletion marker (``AccountsRepository.begin_delete``); this module
drains the bulk rows afterwards, ``DELETE_BATCH_SIZE`` rows per transaction,
and finalizes with the exact transaction shape the synchronous path used.

Fold-safety argument — why the chunk transactions do NOT take the fold-state
lock, yet a deleted account's folded rows can never resurrect:

1. Chunk transactions touch only raw rows (``usage_history``,
   ``additional_usage_history``, ``request_logs``); they never write a rollup
   table and never move a watermark. ``usage_history`` tables are not
   fold-governed at all.
2. A fold slice that interleaves between chunks may aggregate rows still
   attributed to the account (adding folded rows under the account dimension)
   or rows a chunk already detached (adding them under the orphaned-deleted
   dimension — exactly the soft-path end state). Both are converged by the
   finalization transaction: it takes ``lock_fold_state()`` and only then
   detaches/deletes the residual raw rows and runs the lifecycle mirrors,
   which move or remove EVERY folded row carrying the account dimension,
   including rows folded mid-drain.
3. Every fold slice holds the fold-state row lock from before it reads raw
   rows until its commit. A slice therefore commits either before
   finalization (its account-attributed output exists when the mirrors run
   and is moved/removed by them) or after (it observes the post-finalization
   raw state, which carries no attribution to the account). No slice can
   commit pre-deletion attribution after the mirrors ran — the exact
   resurrection the single-transaction path guarded against.

Restart safety and idempotency: all progress lives in the database (the
marker columns plus the shrinking predicate ``WHERE account_id = :id``), so a
leader restart resumes mid-drain, and re-running any chunk is a no-op.
A credential replacement (re-import/reauth) clears the marker and supersedes
the deletion: every chunk transaction re-reads the marker under the account
row lock (PostgreSQL ``FOR NO KEY UPDATE``; the SQLite writer section
serializes writers) before touching rows, and finalization re-checks it the
same way, so no chunk can commit row work after a replacement committed and
a superseded account is never finalized.

Fairness: a deletion pass round-robins one chunk per pending account and
re-scans for newly marked accounts between rounds, so one account's
multi-minute drain can neither starve another marked account nor delay a
delete request that arrives mid-pass.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol, TypeVar, cast

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.api_key_cache import get_api_key_cache
from app.core.cache.invalidation import NAMESPACE_API_KEY, get_cache_invalidation_poller
from app.core.upstream_proxy.cache import get_upstream_route_cache
from app.core.utils.time import utcnow
from app.db.models import (
    Account,
    AccountStatus,
    AdditionalUsageHistory,
    ApiKeyAccountAssignment,
    RequestLog,
    UsageHistory,
)
from app.db.session import get_background_session, sqlite_writer_section
from app.modules.accounts.repository import (
    ACCOUNT_PENDING_DELETION_REASON,
    AccountsRepository,
    credentials_replaced_since_wipe,
)
from app.modules.proxy.account_cache import get_account_selection_cache, propagate_account_routing_change
from app.modules.usage.repository import _clear_bulk_history_since_sqlite_cache

logger = logging.getLogger(__name__)

# Worker tick; the fast delete path additionally wakes the local worker, so a
# single-replica deployment (or a delete that lands on the leader) starts
# draining immediately and the tick only covers follower-received requests
# and restart resume.
DELETION_INTERVAL_SECONDS = 30
# Rows per chunk transaction. Bounded so no chunk holds a long transaction:
# measured production deletes ran ~1.2s/10k usage_history rows and ~23s/10k
# request_logs detaches (18 indexes, non-HOT updates), so 5k keeps every
# transaction comfortably short on both tables.
DELETE_BATCH_SIZE = 5_000

_T = TypeVar("_T")


class _LeaderElectionLike(Protocol):
    async def run_if_leader(self, fn: Callable[[], Awaitable[_T]]) -> _T | None: ...


def _get_leader_election() -> _LeaderElectionLike:
    module = importlib.import_module("app.core.scheduling.leader_election")
    return cast(_LeaderElectionLike, module.get_leader_election())


async def run_account_deletion_pass(*, batch_size: int = DELETE_BATCH_SIZE) -> dict[str, str]:
    """Drain and finalize every account marked for deletion.

    Round-robin fairness: each round advances every pending account by at
    most one nonempty chunk, and the pending set is re-scanned between
    rounds, so a newly marked account starts draining within one chunk
    transaction of its request even while another account's long drain is in
    progress.

    Returns an outcome per account id: ``finalized`` (rows drained, account
    row removed), ``superseded`` (marker cleared mid-drain by a credential
    replacement — deletion abandoned), or ``error`` (logged; retried on the
    next tick).
    """
    outcomes: dict[str, str] = {}
    while True:
        runnable = [
            account_id for account_id in await _pending_deletion_ids() if outcomes.get(account_id) in (None, "draining")
        ]
        if not runnable:
            break
        for account_id in runnable:
            try:
                outcomes[account_id] = await _advance_account(account_id, batch_size=batch_size)
            except Exception:
                logger.exception("Background account deletion failed account_id=%s", account_id)
                outcomes[account_id] = "error"
    # ``draining`` cannot survive the loop: an account leaves the runnable
    # set only through a terminal outcome or by vanishing from the pending
    # scan (its marker was cleared — a supersede that raced the scan).
    for account_id, outcome in outcomes.items():
        if outcome == "draining":
            outcomes[account_id] = "superseded"
    if outcomes:
        logger.info("Account deletion pass outcomes=%s", outcomes)
    return outcomes


async def _pending_deletion_ids() -> list[str]:
    async with get_background_session() as session:
        rows = await session.execute(
            select(Account.id)
            .where(Account.delete_requested_at.is_not(None))
            .order_by(Account.delete_requested_at.asc(), Account.id.asc())
        )
        return list(rows.scalars().all())


async def _advance_account(account_id: str, *, batch_size: int) -> str:
    """One bounded round of work for one account.

    Runs the drain tables in order (usage snapshots first — not
    fold-governed — then the raw request logs) but stops after the first
    NONEMPTY chunk so the caller can round-robin other pending accounts —
    each round commits at most one row-touching transaction per account:
    ``draining`` means more work may remain. Only tables whose chunk came up
    empty are known drained; when every table is, finalize.
    """
    for chunk_fn in (_usage_history_chunk, _additional_usage_history_chunk, _request_logs_chunk):
        affected = await _run_chunk(chunk_fn, account_id, batch_size=batch_size)
        if affected is None:
            return "superseded"
        if affected and chunk_fn is _usage_history_chunk:
            # Same hygiene as retention pruning: bulk usage-history reads are
            # cached on SQLite and must not serve the drained account.
            _clear_bulk_history_since_sqlite_cache()
        if affected:
            return "draining"
    # Finalization: residual rows (streams that settled a log row mid-drain),
    # folded-bucket mirrors, sticky/rollup rows, and the account row itself —
    # one fold-state-locked transaction, identical in shape to the historical
    # synchronous delete but over a residual row set instead of full history.
    async with get_background_session() as session:
        finalized = await AccountsRepository(session).delete(account_id, only_pending=True)
    if not finalized:
        return "superseded"
    # Invalidate immediately (not at end of pass): the account row is gone
    # and ids are deterministic, so cached routing/API-key snapshots must not
    # outlive it while the pass keeps draining other accounts.
    await _invalidate_account_caches()
    return "finalized"


_ChunkFn = Callable[..., Awaitable[int]]


async def _run_chunk(chunk_fn: _ChunkFn, account_id: str, *, batch_size: int) -> int | None:
    """Run one chunk transaction; None when the pending marker disappeared
    (deletion superseded)."""
    async with get_background_session() as session:
        async with sqlite_writer_section():
            delete_history = await _pending_state(session, account_id)
            if delete_history is None:
                await session.rollback()
                return None
            affected = await chunk_fn(session, account_id, delete_history=delete_history, batch_size=batch_size)
            await session.commit()
    return affected


async def _pending_state(session: AsyncSession, account_id: str) -> bool | None:
    """The frozen ``delete_history`` choice, or None when no longer pending.

    On PostgreSQL the read locks the account row (``FOR NO KEY UPDATE``) for
    the rest of the chunk transaction, so a credential replacement cannot
    clear the marker between this read and the chunk's row mutations — the
    replacement blocks until the chunk commits, then the next chunk observes
    the cleared marker and stops. On SQLite the writer section already
    serializes this transaction against every other writer.

    A replacement handled by a pre-upgrade replica (rolling deploy) writes
    fresh credentials but cannot clear marker columns its ORM does not know;
    fresh non-wiped ciphertext on a marked row is therefore itself the
    supersede signal — the marker is cleared here, under the same lock.
    """
    stmt = select(
        Account.delete_requested_at,
        Account.delete_history_requested,
        Account.access_token_encrypted,
        Account.refresh_token_encrypted,
        Account.id_token_encrypted,
        Account.status,
        Account.deactivation_reason,
    ).where(Account.id == account_id)
    if session.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update(key_share=True)
    row = (await session.execute(stmt)).first()
    if row is None or row[0] is None:
        return None
    if credentials_replaced_since_wipe(row[2], row[3], row[4]):
        await session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(delete_requested_at=None, delete_history_requested=False)
        )
        await session.commit()
        return None
    # Self-heal drift written by pre-upgrade replicas during a rolling
    # deploy (their writers are unfenced): a late settlement may have
    # replaced the terminal status — making the wiped account selectable
    # again — and an unconditional assignment insert may have recreated an
    # API-key assignment begin_delete removed. Re-fence both under the row
    # lock held above; any drift is bounded by one chunk transaction. The
    # credentials check above already excluded genuine replacements, so a
    # non-DEACTIVATED status here can only be such drift.
    if row[5] is not AccountStatus.DEACTIVATED or row[6] != ACCOUNT_PENDING_DELETION_REASON:
        await session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(
                status=AccountStatus.DEACTIVATED,
                deactivation_reason=ACCOUNT_PENDING_DELETION_REASON,
                reset_at=None,
                blocked_at=None,
            )
        )
    await session.execute(delete(ApiKeyAccountAssignment).where(ApiKeyAccountAssignment.account_id == account_id))
    return bool(row[1])


async def _usage_history_chunk(session: AsyncSession, account_id: str, *, delete_history: bool, batch_size: int) -> int:
    batch = select(UsageHistory.id).where(UsageHistory.account_id == account_id).limit(batch_size).scalar_subquery()
    result = await session.execute(delete(UsageHistory).where(UsageHistory.id.in_(batch)).returning(UsageHistory.id))
    return len(result.scalars().all())


async def _additional_usage_history_chunk(
    session: AsyncSession, account_id: str, *, delete_history: bool, batch_size: int
) -> int:
    batch = (
        select(AdditionalUsageHistory.id)
        .where(AdditionalUsageHistory.account_id == account_id)
        .limit(batch_size)
        .scalar_subquery()
    )
    result = await session.execute(
        delete(AdditionalUsageHistory).where(AdditionalUsageHistory.id.in_(batch)).returning(AdditionalUsageHistory.id)
    )
    return len(result.scalars().all())


async def _request_logs_chunk(session: AsyncSession, account_id: str, *, delete_history: bool, batch_size: int) -> int:
    """Detach (soft) or delete (hard) one chunk of the account's raw logs.

    Deliberately NOT fold-state-locked and NOT mirrored: see the module
    docstring for why interleaved fold slices converge at finalization.
    """
    batch = select(RequestLog.id).where(RequestLog.account_id == account_id).limit(batch_size).scalar_subquery()
    if delete_history:
        result = await session.execute(delete(RequestLog).where(RequestLog.id.in_(batch)).returning(RequestLog.id))
    else:
        result = await session.execute(
            update(RequestLog)
            .where(RequestLog.id.in_(batch))
            .values(account_id=None, deleted_at=utcnow())
            .returning(RequestLog.id)
        )
    return len(result.scalars().all())


async def _invalidate_account_caches() -> None:
    """Post-finalization invalidation, mirroring the synchronous delete path.

    Account ids are deterministic (delete-then-re-import regenerates the same
    id), so cached route outcomes and API-key assignment snapshots must not
    survive the account row's removal.
    """
    get_account_selection_cache().invalidate()
    get_api_key_cache().clear()
    await get_upstream_route_cache().invalidate()
    await propagate_account_routing_change()
    poller = get_cache_invalidation_poller()
    if poller is not None:
        await poller.bump(NAMESPACE_API_KEY)


@dataclass(slots=True)
class AccountDeletionScheduler:
    """Leader-gated worker tick with a local wake signal.

    Each tick first checks — with one cheap indexed-table read, before any
    leader-election work — whether any account is pending deletion, so the
    steady state (no pending deletions) costs one SELECT per interval.
    """

    interval_seconds: int
    _task: asyncio.Task[None] | None = None
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _wake: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop.set()
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    def wake(self) -> None:
        """Start the next pass immediately (fast delete path just committed)."""
        self._wake.set()

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            # Clear BEFORE running so a wake that lands mid-pass (a second
            # delete request) schedules another pass instead of being lost.
            self._wake.clear()
            await self._run_once()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def _run_once(self) -> None:
        try:
            if not await _any_pending_deletion():
                return
        except Exception:
            logger.exception("Failed to check for pending account deletions")
            return
        await _get_leader_election().run_if_leader(self._run_as_leader)

    async def _run_as_leader(self) -> None:
        async with self._lock:
            try:
                await run_account_deletion_pass()
            except Exception:
                logger.exception("Account deletion pass failed")


async def _any_pending_deletion() -> bool:
    async with get_background_session() as session:
        row = await session.execute(select(Account.id).where(Account.delete_requested_at.is_not(None)).limit(1))
        return row.scalar_one_or_none() is not None


_scheduler: AccountDeletionScheduler | None = None


def build_account_deletion_scheduler() -> AccountDeletionScheduler:
    global _scheduler
    _scheduler = AccountDeletionScheduler(interval_seconds=DELETION_INTERVAL_SECONDS)
    return _scheduler


def request_account_deletion_run() -> None:
    """Nudge the local worker after a delete request commits.

    A follower's nudge is a no-op (``run_if_leader`` declines) and the
    leader's periodic tick picks the request up within the interval; when the
    receiving replica IS the leader — the common single-replica case — the
    drain starts immediately.
    """
    if _scheduler is not None:
        _scheduler.wake()
