from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_session_has_admission_waiter,
    _log_http_bridge_event,
    _service_get_settings,
    _service_get_settings_cache,
    _service_time,
)
from app.modules.proxy._service.http_bridge.protocol import _HTTPBridgeServiceProtocol
from app.modules.proxy._service.support import _HTTPBridgeSession, _HTTPBridgeSessionKey
from app.modules.proxy.affinity import _extract_model_class
from app.modules.sticky_sessions.cleanup_scheduler import _abandoned_bridge_retention_seconds

logger = logging.getLogger("app.modules.proxy.service")

# Task name for the detached-orphan close batch. Registered in the bridge
# background-cleanup drain and activity snapshot prefixes, so shutdown waits
# for it and an in-progress batch counts as bridge activity.
_PURGE_RECONCILE_CLOSE_TASK_NAME = "http-bridge-purge-reconcile-close"


# Secondary guard for the pre-submit window. The PRIMARY guard is the durable
# liveness check: an anchored reuse renews the session's durable row under the
# bridge lock before it yields, so a session a request is about to use is
# found live by ``lookup_sessions`` and skipped. This floor covers only the
# narrow residue — the row renewal failed, or the leader purged between the
# renewal and the lookup — by ignoring sessions touched since the reuse path
# last released the bridge lock.
#
# It deliberately does NOT scale with the bridge request budget (7200s by
# default). That budget exceeds the abandoned-row retention cutoff
# (``_abandoned_bridge_retention_seconds``, 3600s by default), and the purge
# emits its bump only when it deletes a row, so a floor above the cutoff would
# skip every session the single bump was meant to reconcile and never see them
# again. The floor is therefore clamped below the cutoff: correctness against
# the pre-submit window comes from the durable check, not from outwaiting the
# whole request budget.
_PURGE_RECONCILE_MIN_IDLE_SECONDS = 30.0
_PURGE_RECONCILE_MAX_IDLE_FLOOR_RATIO = 0.5


def _purge_reconcile_min_idle_seconds(retention_seconds: float | None = None) -> float:
    """Idle floor a session must clear before this pass may reconcile it.

    Clamped to a fraction of the abandoned-row retention cutoff so a deployment
    that shortens retention can never end up with a floor that silently
    disables the pass.
    """
    if retention_seconds is None or retention_seconds <= 0:
        return _PURGE_RECONCILE_MIN_IDLE_SECONDS
    return min(_PURGE_RECONCILE_MIN_IDLE_SECONDS, retention_seconds * _PURGE_RECONCILE_MAX_IDLE_FLOOR_RATIO)


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
        min_idle_seconds = _purge_reconcile_min_idle_seconds(await self._purge_reconcile_retention_seconds())
        candidates = await self._collect_purge_reconcile_candidates(min_idle_seconds)
        if not candidates:
            return 0
        lookups = await self._durable_bridge.lookup_sessions(
            session_ids=[durable_session_id for _key, _session, durable_session_id in candidates]
        )
        live_session_ids = {lookup.session_id for lookup in lookups}
        sessions_to_close = await self._detach_purged_http_bridge_sessions(
            candidates, live_session_ids, min_idle_seconds
        )
        if sessions_to_close:
            # Create and track the settle task with NO await between detaching
            # and tracking it: the sessions are already out of the registry, so
            # a concurrent shutdown would otherwise see an empty registry and
            # finish its only bridge-cleanup drain before this task exists —
            # and a cancellation landing in that window would drop the task
            # entirely, leaking the detached sessions' upstream sockets.
            settle_task = asyncio.create_task(
                self._settle_purged_http_bridge_sessions(sessions_to_close),
                name=_PURGE_RECONCILE_CLOSE_TASK_NAME,
            )
            self._background_cleanup_tasks.add(settle_task)
            settle_task.add_done_callback(self._background_cleanup_tasks.discard)
        return len(sessions_to_close)

    async def _purge_reconcile_retention_seconds(self: Any) -> float | None:
        """Abandoned-row retention cutoff the leader purged against, if readable.

        Used only to clamp the idle floor below it; an unreadable settings row
        just falls back to the static floor.
        """
        try:
            dashboard_settings = await _service_get_settings_cache().get()
            return _abandoned_bridge_retention_seconds(dashboard_settings, _service_get_settings())
        except Exception:
            logger.debug("Purge reconcile could not read the retention cutoff", exc_info=True)
            return None

    async def _settle_purged_http_bridge_sessions(self: Any, sessions: list[_HTTPBridgeSession]) -> None:
        """Release every orphan's stream lease, then close them.

        Runs off the caller's stack because closing can block on an upstream
        reader awaiting cancellation, which would otherwise pin the sole
        cache-invalidation poller. Leases are returned for ALL sessions first:
        freeing the cap slot is the point of this pass, so a slow close must
        not hold later orphans' capacity behind it.
        """
        await self._release_purged_http_bridge_leases(sessions)
        await self._close_purged_http_bridge_sessions(sessions)

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
        min_idle_seconds: float,
    ) -> list[tuple[_HTTPBridgeSessionKey, _HTTPBridgeSession, str]]:
        async with self._http_bridge_lock:
            candidates: list[tuple[_HTTPBridgeSessionKey, _HTTPBridgeSession, str]] = []
            for key, session in self._http_bridge_sessions.items():
                durable_session_id = _purge_reconcile_eligible_durable_id(self, session, min_idle_seconds)
                if durable_session_id is None:
                    continue
                candidates.append((key, session, durable_session_id))
            return candidates

    async def _detach_purged_http_bridge_sessions(
        self: _HTTPBridgeServiceProtocol,
        candidates: list[tuple[_HTTPBridgeSessionKey, _HTTPBridgeSession, str]],
        live_session_ids: set[str],
        min_idle_seconds: float,
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
                if _purge_reconcile_eligible_durable_id(self, session, min_idle_seconds) != durable_session_id:
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
    min_idle_seconds: float,
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
    if _service_time().monotonic() - session.last_used_at < min_idle_seconds:
        # Recently handed to a request that has not reached submit yet.
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
