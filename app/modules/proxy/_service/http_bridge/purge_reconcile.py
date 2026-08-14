from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_session_has_admission_waiter,
    _log_http_bridge_event,
)
from app.modules.proxy._service.http_bridge.protocol import _HTTPBridgeServiceProtocol
from app.modules.proxy._service.support import _HTTPBridgeSession, _HTTPBridgeSessionKey
from app.modules.proxy.affinity import _extract_model_class

logger = logging.getLogger("app.modules.proxy.service")

# Task name for the detached-orphan close batch. Registered in the bridge
# background-cleanup drain and activity snapshot prefixes, so shutdown waits
# for it and an in-progress batch counts as bridge activity.
_PURGE_RECONCILE_CLOSE_TASK_NAME = "http-bridge-purge-reconcile-close"


class _HTTPBridgePurgeReconcileMixin:
    async def reconcile_purged_http_bridge_sessions(self: Any) -> int:
        """Close idle in-memory bridge sessions whose durable row was purged.

        The leader's abandoned-session purge only deletes durable rows; the
        owner replica's in-memory session — and the account stream lease it
        may hold — survives it, which is the observed "DB empty but the
        in-memory stream cap stays full" state from issue #1354. Invoked from
        the ``http_bridge_purge`` cache-invalidation bump, this pass releases
        those orphans. Only quiescent sessions are eligible: anything with
        pending work, an admission waiter, an in-progress handoff, or an
        unanchored reservation is left to its own lifecycle.
        """
        candidates = await self._collect_purge_reconcile_candidates()
        if not candidates:
            return 0
        lookups = await self._durable_bridge.lookup_sessions(
            session_ids=[durable_session_id for _key, _session, durable_session_id in candidates]
        )
        live_session_ids = {lookup.session_id for lookup in lookups}
        sessions_to_close = await self._detach_purged_http_bridge_sessions(candidates, live_session_ids)
        if sessions_to_close:
            # Release every orphan's stream lease BEFORE closing any of them.
            # Releasing the cap slot is the point of this pass, while closing
            # can block on a slow upstream-reader cancel; folding the release
            # into the serial close loop would hold later sessions' capacity
            # for as long as earlier readers take to unwind.
            await self._release_purged_http_bridge_leases(sessions_to_close)
            # Close in a tracked background task: the reader cancels would
            # otherwise pin the sole cache-invalidation poller. The sessions
            # are already detached, so a concurrent bump cannot double-process
            # them; shutdown drains the tracked task.
            close_task = asyncio.create_task(
                self._close_purged_http_bridge_sessions(sessions_to_close),
                name=_PURGE_RECONCILE_CLOSE_TASK_NAME,
            )
            self._background_cleanup_tasks.add(close_task)
            close_task.add_done_callback(self._background_cleanup_tasks.discard)
        return len(sessions_to_close)

    async def _release_purged_http_bridge_leases(self: Any, sessions: list[_HTTPBridgeSession]) -> None:
        """Return every detached orphan's account stream lease to the pool.

        ``_close_http_bridge_session`` performs the same release, so this is
        idempotent: clearing ``account_lease`` here makes the later close a
        no-op for the lease. One session's failure must not strand the rest.
        """
        for session in sessions:
            account_lease = getattr(session, "account_lease", None)
            if account_lease is None:
                continue
            try:
                await self._load_balancer.release_account_lease(account_lease)
            except Exception:
                logger.warning(
                    "Failed to release purged HTTP bridge account lease account_id=%s model=%s",
                    session.account.id,
                    session.request_model,
                    exc_info=True,
                )
            finally:
                session.account_lease = None

    async def _collect_purge_reconcile_candidates(
        self: _HTTPBridgeServiceProtocol,
    ) -> list[tuple[_HTTPBridgeSessionKey, _HTTPBridgeSession, str]]:
        async with self._http_bridge_lock:
            candidates: list[tuple[_HTTPBridgeSessionKey, _HTTPBridgeSession, str]] = []
            for key, session in self._http_bridge_sessions.items():
                durable_session_id = _purge_reconcile_eligible_durable_id(self, session)
                if durable_session_id is None:
                    continue
                candidates.append((key, session, durable_session_id))
            return candidates

    async def _detach_purged_http_bridge_sessions(
        self: _HTTPBridgeServiceProtocol,
        candidates: list[tuple[_HTTPBridgeSessionKey, _HTTPBridgeSession, str]],
        live_session_ids: set[str],
    ) -> list[_HTTPBridgeSession]:
        sessions_to_close: list[_HTTPBridgeSession] = []
        async with self._http_bridge_lock:
            for key, session, durable_session_id in candidates:
                if durable_session_id in live_session_ids:
                    continue
                # Re-validate the FULL candidate predicate under the lock: the
                # session may have picked up work, gained an unanchored
                # reservation, re-claimed a fresh durable row, or been replaced
                # while the durable lookup ran.
                if _purge_reconcile_eligible_durable_id(self, session) != durable_session_id:
                    continue
                detached = self._detach_http_bridge_session_locked(key, expected_session=session)
                if detached is None:
                    continue
                _log_http_bridge_event(
                    "evict_purged",
                    key,
                    account_id=session.account.id,
                    model=session.request_model,
                    cache_key_family=key.affinity_kind,
                    model_class=_extract_model_class(session.request_model) if session.request_model else None,
                )
                sessions_to_close.append(detached)
        return sessions_to_close

    async def _close_purged_http_bridge_sessions(self: Any, sessions: list[_HTTPBridgeSession]) -> None:
        for session in sessions:
            try:
                # The durable row is already gone, so skip the release round trip.
                await self._close_http_bridge_session(session, release_durable_session=False)
            except Exception:
                logger.warning(
                    "Failed to close purged HTTP bridge session account_id=%s model=%s",
                    session.account.id,
                    session.request_model,
                    exc_info=True,
                )


def _purge_reconcile_eligible_durable_id(
    service: _HTTPBridgeServiceProtocol,
    session: _HTTPBridgeSession,
) -> str | None:
    """Return the session's durable id when it is a purge-reconcile candidate.

    Callers MUST hold the bridge lock. Returns ``None`` for any session that
    owns work (pending/queued requests, an admission waiter, a handoff, or an
    unanchored reservation), is already closed, or carries no durable claim —
    those are left to their own lifecycle.
    """
    if session.closed or session.handoff_in_progress:
        return None
    if _http_bridge_session_has_admission_waiter(session):
        return None
    if getattr(session, "unanchored_reservation_id", None) is not None:
        return None
    durable_session_id = getattr(session, "durable_session_id", None)
    if durable_session_id is None:
        return None
    pending_count = service._http_bridge_pending_count_nowait(session, context="purge_reconcile")
    if pending_count is None or pending_count:
        return None
    return durable_session_id
