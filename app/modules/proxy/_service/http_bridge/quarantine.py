from __future__ import annotations

import logging
import time
import weakref
from dataclasses import dataclass
from typing import Any

from app.modules.proxy._service.http_bridge.helpers import _log_http_bridge_event
from app.modules.proxy._service.support import (
    _REQUEST_TRANSPORT_HTTP,
    _HTTPBridgeSession,
    _HTTPBridgeSessionKey,
    _WebSocketRequestState,
)
from app.modules.proxy.affinity import _extract_model_class

logger = logging.getLogger("app.modules.proxy.service")

# Quarantine is a bounded, in-memory, session-scoped (never account-scoped)
# marker for HTTP bridge session keys that have proven silent/wedged: a later
# request must not re-attach to them and must take the existing fresh
# session/no-anchor path instead (#1534). It complements — and never replaces
# — the in-flight recovery machinery: the eventless watchdog and bounded
# replay (#1394) recover the request that is currently stuck, the fenced
# durable-anchor clear (#1563) stops a *fully eventless* full-resend anchor
# from being re-injected, and the durable retry circuit backs off in-place
# retries. Quarantine covers what those leave open: the reattached stream
# that delivers response events but never gets ``response.created`` (the
# ``response_event_count == 0`` gates in the stale/eventless detection never
# trip on it), and the repeated-wedge case where consecutive eventless
# timeouts keep rebuilding the same reattach.
_HTTP_BRIDGE_QUARANTINE_TTL_SECONDS = 600.0
_HTTP_BRIDGE_QUARANTINE_EVENTLESS_TIMEOUT_THRESHOLD = 2
_HTTP_BRIDGE_QUARANTINE_MAX_ENTRIES = 1024

_HTTP_BRIDGE_QUARANTINE_WEDGED_REATTACH_REASON = "reattach_missing_response_created"
_HTTP_BRIDGE_QUARANTINE_REPEATED_EVENTLESS_REASON = "repeated_eventless_timeout"
# The hard-affinity retry circuit opened on an eventless poison-class failure
# (``stream_incomplete`` / ``stream_idle_timeout``): the anchor it opened on
# must not be re-injected into the probe admitted after the cooldown (#1852).
_HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON = "retry_circuit_poisoned_anchor"


@dataclass(slots=True)
class _HTTPBridgeQuarantineEntry:
    generation: int = 0
    # Keep a weak lifetime token rather than a strong session reference. A
    # detached session may finish after the key is reused; retaining it here
    # would defeat the registry's bounded lifetime and an integer object id
    # could be recycled before that completion arrives.
    owner_ref: weakref.ReferenceType[_HTTPBridgeSession] | None = None
    quarantined_until: float = 0.0
    consecutive_eventless_timeouts: int = 0
    last_touched_monotonic: float = 0.0
    reason: str | None = None
    # Generation at the most recent poison arm. Weaker arms during a
    # speculative poison window bump ``generation`` without touching this,
    # so a revocation can still recognize its own arm.
    poison_generation: int = 0
    # The poison classification's OWN deadline. The shared
    # ``quarantined_until`` keeps the session fenced under whatever
    # evidence extended it last, but only a poison arm may extend this
    # one: weaker arms landing near the end of a poison window must not
    # prolong the anchor-is-dead classification indefinitely.
    poison_quarantined_until: float = 0.0
    # A weaker fence that arrived while the poison reason was active: the
    # no-downgrade guard keeps the poison reason, and a later revocation of
    # the poison evidence downgrades to this instead of evicting the entry.
    # The deadline is the weaker arm's own expiry, so a downgrade does not
    # keep serving the disproved poison arm's longer floor.
    suppressed_weaker_reason: str | None = None
    suppressed_weaker_until: float = 0.0


def _http_bridge_quarantine_owner_ref(
    session: Any,
) -> weakref.ReferenceType[_HTTPBridgeSession] | None:
    """Return an owner token when the quarantine source supports weak refs.

    Planning-time retry-circuit loads use a lightweight key probe rather than
    a real bridge session. That probe is intentionally not weak-referenceable;
    leaving an existing token untouched preserves the identity fence for a
    real session that already owns the key.
    """
    try:
        return weakref.ref(session)
    except TypeError:
        return None


def _http_bridge_quarantine_registry(
    service: Any,
) -> dict[_HTTPBridgeSessionKey, _HTTPBridgeQuarantineEntry]:
    registry = getattr(service, "_http_bridge_quarantined_keys", None)
    if registry is None:
        registry = {}
        service._http_bridge_quarantined_keys = registry
    return registry


def _next_http_bridge_quarantine_generation(
    service: Any,
    registry: dict[_HTTPBridgeSessionKey, _HTTPBridgeQuarantineEntry],
) -> int:
    """Return a generation unique for this service lifetime."""
    current = max(
        getattr(service, "_http_bridge_quarantine_generation_counter", 0) or 0,
        getattr(service, "_http_bridge_quarantine_generation_high_water", 0) or 0,
    )
    # A test/recovery restore may seed the map independently of the lazy
    # service counter. Preserve the greatest observed value before advancing so
    # the counter remains monotonic even in that state. The separate high-water
    # mark survives a counter or registry reset, so a reset cannot recycle a
    # generation that was already observed during this service lifetime.
    current = max(current, max((entry.generation for entry in registry.values()), default=0))
    next_generation = current + 1
    service._http_bridge_quarantine_generation_counter = next_generation
    service._http_bridge_quarantine_generation_high_water = next_generation
    return next_generation


def _prune_http_bridge_quarantine_registry(
    registry: dict[_HTTPBridgeSessionKey, _HTTPBridgeQuarantineEntry],
    now: float,
) -> None:
    expiry = now - _HTTP_BRIDGE_QUARANTINE_TTL_SECONDS
    for key, entry in list(registry.items()):
        if entry.last_touched_monotonic <= expiry and entry.quarantined_until <= now:
            registry.pop(key, None)
    overflow = len(registry) - _HTTP_BRIDGE_QUARANTINE_MAX_ENTRIES
    if overflow > 0:
        # An active poison quarantine is the only record that a key's anchor
        # was proven dead, and its deadline is a required minimum: evicting
        # it early hands the poisoned anchor back to the very probe it
        # exists to protect. The cap therefore evicts only expired or
        # weaker-fence entries and holds as a correctness bound, not an
        # unconditional one, when an incident quarantines more keys than the
        # cap at once.
        evictable = [
            key
            for key, entry in registry.items()
            if not (entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON and entry.quarantined_until > now)
        ]
        for stale_key in sorted(evictable, key=lambda candidate: registry[candidate].last_touched_monotonic)[:overflow]:
            registry.pop(stale_key, None)


def _revoke_http_bridge_poison_quarantine(
    service: Any,
    key: _HTTPBridgeSessionKey,
    *,
    generation: int | None,
    restore_reason: str | None = None,
    restore_until: float = 0.0,
) -> bool:
    """Remove a poison quarantine whose opening did not survive persistence.

    A strike arms the poison quarantine before its durable write; when the
    returned row shows the lineage was actually reset or opened clean, that
    speculative quarantine would suppress a valid anchor for its full
    deadline. The generation fence removes exactly the entry this strike
    armed: any concurrent re-arm bumps the generation and is preserved.

    When the speculative arm upgraded a weaker quarantine that was active in
    its own right — a wedged reattach or repeated eventless fence — revoking
    the poison evidence must not evict that fence with it: the prior reason
    and deadline are restored instead, since only the poison upgrade is what
    the lost race disproved.
    """
    if generation is None:
        return False
    registry = _http_bridge_quarantine_registry(service)
    entry = registry.get(key)
    if (
        entry is not None
        and entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
        # The poison provenance, not the raw generation: a weaker fence
        # arming during the speculative window bumps the generation while
        # the no-downgrade guard keeps the poison reason, and that must not
        # let disproved poison evidence outlive its revocation.
        and entry.poison_generation == generation
    ):
        entry.poison_quarantined_until = 0.0
        if entry.suppressed_weaker_reason is not None and entry.suppressed_weaker_until > time.monotonic():
            entry.reason = entry.suppressed_weaker_reason
            entry.quarantined_until = entry.suppressed_weaker_until
            entry.suppressed_weaker_reason = None
            entry.suppressed_weaker_until = 0.0
            entry.generation += 1
            return True
        if restore_reason is not None and restore_until > time.monotonic():
            entry.reason = restore_reason
            entry.quarantined_until = restore_until
            entry.generation += 1
            return True
        registry.pop(key, None)
        return True
    return False


def _http_bridge_request_state_wedged_reattach(request_state: _WebSocketRequestState) -> bool:
    """Identify the #1534 wedge shape on a request that is being failed/retired.

    A reattached stream (proxy-injected ``previous_response_id``) whose
    ``response.create`` was sent and that observed upstream response events,
    but whose ``response.created`` was never assigned. This is only evaluated
    when the request is already being failed or its session retired — never
    against a live owned turn — so legitimate long event gaps (for example
    deferred-reasoning streams) can never trip it, and any request whose
    ``response.created`` was observed (``response_id`` or created latency set)
    is excluded by construction.
    """
    return (
        getattr(request_state, "transport", None) == _REQUEST_TRANSPORT_HTTP
        and not getattr(request_state, "skip_request_log", False)
        and getattr(request_state, "proxy_injected_previous_response_id", False)
        and getattr(request_state, "response_create_sent_at", None) is not None
        and getattr(request_state, "response_id", None) is None
        and getattr(request_state, "latency_response_created_ms", None) is None
        and getattr(request_state, "response_event_count", 0) > 0
    )


def _http_bridge_session_key_quarantined(service: Any, key: _HTTPBridgeSessionKey) -> bool:
    registry = _http_bridge_quarantine_registry(service)
    now = time.monotonic()
    _prune_http_bridge_quarantine_registry(registry, now)
    entry = registry.get(key)
    return entry is not None and entry.quarantined_until > now


def _http_bridge_session_key_poison_quarantined(service: Any, key: _HTTPBridgeSessionKey) -> bool:
    """Return whether the key is fenced because its anchor was proven dead.

    The registry is shared with the wedged-reattach and repeated-eventless
    quarantines, which fence the *session* and say nothing about the anchor it
    carried. Only the retry circuit's poison quarantine records that the anchor
    itself kept failing, so callers that drop a continuity anchor must ask for
    the reason rather than for an active window: dropping it on either of the
    other two turns a valid delta-only continuation into a context-free
    request.
    """
    registry = _http_bridge_quarantine_registry(service)
    now = time.monotonic()
    _prune_http_bridge_quarantine_registry(registry, now)
    entry = registry.get(key)
    return (
        entry is not None
        and entry.quarantined_until > now
        and entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
        # The classification expires on the poison arm's OWN deadline even
        # while weaker evidence keeps the shared session fence alive.
        and entry.poison_quarantined_until > now
    )


def _http_bridge_quarantine_generation(service: Any, key: _HTTPBridgeSessionKey) -> int | None:
    """Return the active quarantine generation observed for one recovery."""
    registry = _http_bridge_quarantine_registry(service)
    now = time.monotonic()
    _prune_http_bridge_quarantine_registry(registry, now)
    entry = registry.get(key)
    if entry is None or entry.quarantined_until <= now:
        return None
    return entry.generation


def _http_bridge_quarantine_clear_fence(service: Any, key: _HTTPBridgeSessionKey) -> int | None:
    """Capture the provenance fence a later completion clear must present.

    Poison entries fence on their poison provenance so a weaker arm during
    the completion's durable awaits cannot block the clear; other entries
    fence on the raw generation. ``None`` records that nothing was active at
    capture, so a quarantine armed afterwards survives the clear.
    The first eventless timeout is retained as an inactive strike entry with
    its own generation. It still needs an observation fence: an older
    completion that observed no entry must not pop that strike after a
    settlement await.
    """
    registry = _http_bridge_quarantine_registry(service)
    now = time.monotonic()
    _prune_http_bridge_quarantine_registry(registry, now)
    entry = registry.get(key)
    if entry is None:
        return None
    if entry.quarantined_until > now and entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON:
        return entry.poison_generation
    return entry.generation


def _quarantine_http_bridge_session(
    service: Any,
    session: _HTTPBridgeSession,
    *,
    reason: str,
    minimum_seconds: float | None = None,
) -> None:
    """Quarantine a bridge session that has proven silent/wedged.

    Session-scoped only: no account-health writes happen here, and the entry
    is bounded by TTL, a registry size cap, and the healthy-completion clear.

    ``minimum_seconds`` raises the floor for callers whose suppression window
    is itself bounded elsewhere. The default TTL equals the retry circuit's
    maximum cooldown, so a poison quarantine armed at that cooldown would
    otherwise expire in the same instant the cooldown does, handing the
    poisoned anchor straight back to the request that cooldown was holding.
    """
    now = time.monotonic()
    registry = _http_bridge_quarantine_registry(service)
    entry = registry.setdefault(session.key, _HTTPBridgeQuarantineEntry())
    already_quarantined = entry.quarantined_until > now
    # Captured before the deadline extension below: a poison arm upgrading
    # over an active weaker fence must stash the weaker's OWN deadline, not
    # the extended one, so a later poison revocation downgrades to exactly
    # the window the weaker evidence earned.
    prior_reason = entry.reason
    prior_quarantined_until = entry.quarantined_until
    entry.generation = _next_http_bridge_quarantine_generation(service, registry)
    # Store object lifetime, not ``id(session)``: a detached predecessor can
    # finish after a replacement reuses this key, and CPython may recycle an
    # integer id before that completion arrives.
    owner_ref = _http_bridge_quarantine_owner_ref(session)
    if owner_ref is not None:
        entry.owner_ref = owner_ref
    ttl_seconds = _HTTP_BRIDGE_QUARANTINE_TTL_SECONDS
    if minimum_seconds is not None:
        ttl_seconds = max(ttl_seconds, minimum_seconds)
    entry.quarantined_until = max(entry.quarantined_until, now + ttl_seconds)
    entry.last_touched_monotonic = now
    # The registry holds one entry per key, so a wedged-reattach or
    # repeated-eventless quarantine arriving while a poison quarantine is still
    # active would otherwise overwrite the only record that the anchor was
    # proven dead. Callers that drop a continuity anchor test this reason, and
    # losing it re-attaches the poisoned anchor. The weaker fence still extends
    # the deadline above; it just cannot downgrade the evidence.
    if not (
        entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
        and already_quarantined
        # An expired poison classification no longer outranks the weaker
        # arm: the anchor-is-dead window ended on its own deadline, and
        # the weaker evidence takes the reason normally.
        and entry.poison_quarantined_until > now
        and reason != _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
    ):
        if (
            reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
            and already_quarantined
            and prior_reason is not None
            and prior_reason != _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
        ):
            # The mirror of the weaker-over-poison stash below: the wedged
            # or repeated-eventless fence stands on its own evidence, and a
            # later load disproving the poison episode must downgrade to it
            # instead of evicting the entry and freeing the still-wedged
            # session before its original TTL.
            entry.suppressed_weaker_reason = prior_reason
            entry.suppressed_weaker_until = max(entry.suppressed_weaker_until, prior_quarantined_until)
        entry.reason = reason
        if reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON:
            entry.poison_generation = entry.generation
            entry.poison_quarantined_until = max(entry.poison_quarantined_until, now + ttl_seconds)
    else:
        # The weaker fence stands on its own evidence; record it, with its
        # own expiry, so a later revocation of the poison arm can downgrade
        # to it instead of evicting the entry or serving the disproved
        # arm's longer deadline.
        entry.suppressed_weaker_reason = reason
        entry.suppressed_weaker_until = max(entry.suppressed_weaker_until, now + ttl_seconds)
    _prune_http_bridge_quarantine_registry(registry, now)
    session.quarantined = True
    if already_quarantined:
        return
    _log_http_bridge_event(
        "session_quarantined",
        session.key,
        account_id=session.account.id,
        model=session.request_model,
        detail=f"reason={reason}, ttl_seconds={ttl_seconds:.0f}",
        cache_key_family=session.key.affinity_kind,
        model_class=_extract_model_class(session.request_model) if session.request_model else None,
    )


def _record_http_bridge_quarantine_wedged_pending(
    service: Any,
    session: _HTTPBridgeSession,
    request_states: Any,
) -> bool:
    """Quarantine the session when a failed/retired pending request proves the wedge shape."""
    if not any(_http_bridge_request_state_wedged_reattach(request_state) for request_state in request_states):
        return False
    _quarantine_http_bridge_session(
        service,
        session,
        reason=_HTTP_BRIDGE_QUARANTINE_WEDGED_REATTACH_REASON,
    )
    return True


def _record_http_bridge_quarantine_eventless_timeout(service: Any, session: _HTTPBridgeSession) -> None:
    """Count a ``missing_response_created_timeout`` retire; quarantine on repeats.

    The first eventless timeout is left to the merged recovery machinery
    (bounded pre-created retry, fenced durable-anchor clear). A second
    consecutive one for the same session key proves that path is also
    rebuilding a wedged attach, so later requests must stop re-attaching.
    """
    now = time.monotonic()
    registry = _http_bridge_quarantine_registry(service)
    # Prune before touching the entry: a strike whose TTL already lapsed must
    # not be resurrected into a "consecutive" second strike hours later.
    _prune_http_bridge_quarantine_registry(registry, now)
    entry = registry.get(session.key)
    if entry is None:
        entry = _HTTPBridgeQuarantineEntry(
            generation=_next_http_bridge_quarantine_generation(service, registry),
        )
        registry[session.key] = entry
    else:
        # Mutating an existing strike/quarantine entry changes the evidence a
        # captured completion is allowed to clear. Allocate a new generation so
        # a stale completion cannot remove a post-capture first strike.
        entry.generation = _next_http_bridge_quarantine_generation(service, registry)
    # The strike entry is shared with the eventual quarantine record. Keep an
    # owner token from the first strike onward so a detached predecessor can
    # never clear or reset state after the key has been reused.
    owner_ref = _http_bridge_quarantine_owner_ref(session)
    if owner_ref is not None:
        entry.owner_ref = owner_ref
    entry.consecutive_eventless_timeouts += 1
    entry.last_touched_monotonic = now
    if entry.consecutive_eventless_timeouts < _HTTP_BRIDGE_QUARANTINE_EVENTLESS_TIMEOUT_THRESHOLD:
        return
    _quarantine_http_bridge_session(
        service,
        session,
        reason=_HTTP_BRIDGE_QUARANTINE_REPEATED_EVENTLESS_REASON,
    )


def _clear_http_bridge_quarantine(
    service: Any,
    session: _HTTPBridgeSession,
    *,
    key_generation: int | None = None,
    key_generation_captured: bool = False,
    additional_key: _HTTPBridgeSessionKey | None = None,
    additional_key_generation: int | None = None,
) -> None:
    """Clear only quarantine evidence this completion is authorized to clear.

    The primary key is fenced by the completing session's identity, the
    canonical session registry, and the generation observed before any
    completion awaits. A recovery-origin key is fenced by its exact observed
    generation; ``None`` means the recovery observed absence and is
    intentionally not a wildcard. Direct callers that do not provide a
    pre-await fence capture one immediately before clearing. Poison entries
    fence on their own provenance, so a weaker arm during the completion's
    durable awaits does not block a matched clear or get evicted with the
    disproved poison arm.
    """
    registry = _http_bridge_quarantine_registry(service)
    if additional_key == session.key:
        # A same-key recovery carries the origin fence separately from the
        # completing session's primary fence. It is the stronger authority:
        # use it before the primary clear runs, so an observed absence stays
        # an absence fence instead of being replaced by an auto-captured
        # generation for the entry armed during recovery.
        key_generation = additional_key_generation
        key_generation_captured = True
    elif not key_generation_captured:
        key_generation = _http_bridge_quarantine_clear_fence(service, session.key)
    now = time.monotonic()

    def clear_fenced(
        key: _HTTPBridgeSessionKey,
        captured_generation: int | None,
        *,
        is_primary: bool = False,
    ) -> bool:
        entry = registry.get(key)
        if entry is None:
            return True
        if is_primary:
            active_sessions = getattr(service, "_http_bridge_sessions", None)
            has_current_primary_session = False
            is_current_primary_session = False
            if isinstance(active_sessions, dict):
                has_current_primary_session = key in active_sessions
                is_current_primary_session = has_current_primary_session and active_sessions.get(key) is session
            if has_current_primary_session and not is_current_primary_session:
                # A detached predecessor can finish after a replacement has
                # reused the key. The canonical registry wins over the stale
                # object's mutable marker.
                return False
            if not is_current_primary_session and (entry.owner_ref is None or entry.owner_ref() is not session):
                # If no canonical primary is present, the weak owner token
                # is the only identity authority. Restored/legacy ownerless
                # entries cannot be cleared by a completion guessing its
                # ownership.
                return False
        fence_generation = (
            entry.poison_generation
            if (entry.quarantined_until > now and entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON)
            else entry.generation
        )
        if captured_generation is None or fence_generation != captured_generation:
            return False
        if entry.quarantined_until <= now:
            # An inactive entry still carries the eventless strike counter;
            # a healthy completion resets it only when the observed
            # generation still matches.
            registry.pop(key, None)
            return True
        if (
            entry.reason == _HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
            and entry.suppressed_weaker_reason is not None
            and entry.suppressed_weaker_until > now
        ):
            # The concurrent weaker fence stands on its own evidence:
            # downgrade to it instead of evicting the entry with the
            # disproved poison classification.
            entry.reason = entry.suppressed_weaker_reason
            entry.quarantined_until = entry.suppressed_weaker_until
            entry.suppressed_weaker_reason = None
            entry.suppressed_weaker_until = 0.0
            entry.poison_generation = 0
            entry.poison_quarantined_until = 0.0
            entry.generation += 1
            return False
        registry.pop(key, None)
        _log_http_bridge_event(
            "session_quarantine_cleared",
            key,
            account_id=session.account.id,
            model=session.request_model,
            detail=f"reason={entry.reason}",
            cache_key_family=key.affinity_kind,
            model_class=_extract_model_class(session.request_model) if session.request_model else None,
        )
        return True

    if clear_fenced(session.key, key_generation, is_primary=True):
        session.quarantined = False
    if additional_key is not None and additional_key != session.key:
        clear_fenced(additional_key, additional_key_generation)
