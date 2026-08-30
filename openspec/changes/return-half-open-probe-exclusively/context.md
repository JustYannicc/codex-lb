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
  suppressed by that lease.
- Equal-version reloads do not erase an active local lease. The reload can
  reconcile the durable cooldown and failure count, but it cannot prove that a
  local probe is stale. This preserves the single-flight signal used by later
  poison/quarantine work.
- Reset ordering is lifecycle ownership -> bridge registry -> pending attempts:
  claim the session lifecycle, detach it from active routing, mark its pending
  response-create attempts disarmed, then return the owner lease and settle/close
  the resources. The critical transition is shielded from cancellation; the
  caller's cancellation is observed after the cleanup task has published the
  detached and settled state.

## Failure modes and controls

- A stale session cannot return a newer session's probe because the release
  checks the owning session identity.
- A continuity-owner failure does not increment `consecutive_failures` or
  persist a new row. An actual `stream_incomplete`, `stream_idle_timeout`, or
  `clean_close` still increments and opens the circuit at the configured
  threshold.
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
