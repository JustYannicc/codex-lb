# Context

## Purpose and boundary

The retry circuit protects a hard bridge key after repeated eventless upstream
failures. It has two distinct state planes:

1. The durable row carries failure count, last detail, version, and a wall-clock
   cooldown deadline. Those fields merge across replicas and are the shared
   protection against repeated upstream failures.
2. The in-memory state carries the monotonic deadline and the active half-open
   lease. The upstream websocket and its pending request objects live in one
   process, so lease ownership is process-local and is bound to that session.

Keeping those planes explicit avoids pretending that an in-memory lease can be
recovered or fenced cluster-wide without a schema/API change. A replica that
loads an already elapsed durable row may admit its own local probe; it still
honors any real future durable cooldown and any durable failure updates.

## Decisions

- A durable cooldown with `cooldown_until_epoch <= now` is represented as the
  in-memory zero sentinel, not as `now_monotonic`. A row written below the
  failure threshold also commonly has a wall-clock value at write time, so the
  same normalization applies there.
- Expiry itself remains a single-flight boundary within a process. The first
  local admission after a real cooldown sets `half_open_until` and records the
  owning session. A continuity-loss return clears the active lease and sets
  `cooldown_until` to the current monotonic time; the next admission sees an
  elapsed, non-zero marker and installs one fresh lease, while siblings are
  suppressed by that lease. A local release timestamp keeps that marker across
  a transient durable miss until the next admission can claim the new lease.
- Equal-version reloads do not erase an active local lease. The reload can
  reconcile the durable cooldown and failure count, but it cannot prove that a
  local probe is stale. This preserves the single-flight signal used by later
  poison/quarantine work.
- A newer durable reset or lower failure count also cannot erase an active
  local lease or lower its local failure fence while the probe is in flight.
  When no local probe is active, a newer durable reset clears stale local
  failure detail together with the count and cooldown.
- Reset ordering is lifecycle ownership -> bridge registry -> pending attempts:
  claim the session lifecycle, detach it from active routing, mark its pending
  response-create attempts disarmed, then return the owner lease and settle/close
  the resources. The critical transition is shielded from cancellation; the
  caller's cancellation is observed after the cleanup task has published the
  detached and settled state.

## Issue and vehicle map

This change is intentionally split from the neighboring current-head
vehicles. The comparison was made against `upstream/main`
`2268f8caf1fe9d74a8734bd3f9cd8bd5152b5d3f` and these exact heads:

- #1908 `ed8ee1222999bf6b58164529af3ae5724e09c4ec` contains the accepted
  elapsed/absent-row arithmetic root cause, but its equal/newer lease-clearing
  behavior is superseded here because it breaks #1394 single-flight.
- #1947 `2a1ce9962b7daccd335f1f10fc2595f6ea9ab702` is the focused vehicle for
  #1943 cooldown-created undispatched WebSocket session freshness/retirement;
  it does not own this retry-circuit arithmetic or probe-return contract.
- #1857's accepted semantic source is limited to commits
  `d007582968d0c9b41ed29a6002226bbd63d07313`,
  `9a7dc342148cf471b13a9980d411ea96d654e19e`, and
  `2a822b4f9b522d4972e12a357d019a033b900805`: owner-tracked release, cancellation-safe
  teardown, and replica-boundary reasoning. Its broad/relanded branch is not
  carried as a vehicle.
- #1891 owns poisoned-anchor quarantine and episode/generation-proven
  replacement invalidation; this change preserves equal/unchanged elapsed
  snapshots and does not import quarantine.
- #1867 remains the broad stale-anchor hardening vehicle; no migration,
  attribution, or broad anchor changes belong here.
- #1902 is the sole attribution carrier. This change does not edit contributor
  files or recreate closed #1951.

The successor PR must cite maintainer comments #1908 `5423573461` and #1857
`5423566424`, and the issue-separation statement in #1943, alongside this map.

## Failure modes and controls

- A stale session cannot return a newer session's probe because the release
  checks the owning session identity.
- A continuity-owner failure does not increment `consecutive_failures` or
  persist a new row. An actual `stream_incomplete`, `stream_idle_timeout`, or
  `clean_close` still increments and opens the circuit at the configured
  threshold. A previous-response rejection is neutral only when request state
  proves proxy anchor injection or a dead durable owner; a client-supplied
  unknown anchor remains chargeable upstream failure.
- Disarming before the first await prevents the reader from classifying reset
  teardown as an eligible eventless send. Acquiring `lifecycle_lock` closes the
  submit-vs-reset gap in which a late submit could append an undisarmed attempt.
- If durable lookup fails, the existing local state remains authoritative for
  the process. The release is still best-effort and fenced by the active local
  owner; no durable clear is invented for a process-local lease.

## Example

Two failures open a hard key for 60 seconds. After the deadline, local session
A is the only admitted probe. The upstream rejects the proxy's stale anchor;
the reset detaches A, disarms its pending attempt, and returns the lease as an
elapsed cooldown. A concurrent reconnect on the same process is suppressed
until the next request acquires a fresh probe. A different replica may admit a
local probe after loading the same elapsed durable row, but both replicas still
honor a future durable cooldown and merge genuine failures through the durable
row.

## Validation note

Strict validation of this change passes with
`pnpm --silent dlx @fission-ai/openspec@1.10.0 validate
return-half-open-probe-exclusively --strict`. The full main-spec validation
passes 57 of 58 specs; the unrelated existing `model-source-routing` spec
fails its own validation and is outside this change.
