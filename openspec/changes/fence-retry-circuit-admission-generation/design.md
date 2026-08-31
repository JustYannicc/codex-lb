# Design: retry-circuit generation fencing

## Boundary

The durable `http_bridge_retry_circuits.admission_generation` integer is the
linearization point for one internally authorized stale-anchor replay. The
existing `updated_at_epoch`, failure count, and cooldown remain the observed
failure state. They are compared in the claim so a stale snapshot cannot win,
but they are not used as the admission version because wall clocks can be
skewed and delayed failure writes must still merge.

Each successful claim also records its generation, start epoch, and expiry in
nullable columns. The default lease is the two-hour HTTP bridge request budget
plus 60 seconds of cleanup grace. A request with a shorter configured budget
uses that exact remaining budget plus the same grace. The marker is active only
until its expiry; legacy rows with a null expiry are reclaimable by the normal
generation CAS. The migration leaves all three columns nullable so existing
rows remain valid. Its downgrade first checks for an unexpired receipt and
refuses before DDL or Alembic version stamping when one exists; once no live
receipt remains, it drops the marker columns so the parent revision's ORM
schema does not trip startup drift checks. The check and drop run under one
critical section: PostgreSQL uses `LOCK TABLE ... IN ACCESS EXCLUSIVE MODE`,
while SQLite uses `BEGIN IMMEDIATE` to take the writer slot. A direct Alembic
rollback therefore cannot race a durable claim that does not use the broader
migration lock.

## Claim path

At stale-anchor authorization, the bridge captures an immutable
`_HTTPBridgeRetryCircuitGeneration` containing the durable fields and the
process-local failure/cooldown state. Immediately before queue publication,
the submitter checks the local state under the retry-circuit lock, releases the
lock for durable I/O, and issues one conditional insert/update. SQLite and
PostgreSQL are the only supported durable dialects for this path; the
statement uses `RETURNING` so a successful receipt is returned by the same
atomic write rather than a second read that could time out after consuming the
generation. A missing row is created only when the captured generation proves
absence (`generation == 0`). The conditional update may reclaim an expired
marker, but it must reject an active marker and always writes a new expiry
alongside the incremented generation.

If the first bounded claim times out, cancellation does not prove whether the
database committed. One identical compare-and-set may be retried within the
remaining request deadline when the first operation has settled cancellation.
A cancellation-resistant first operation is detached and no concurrent retry
is issued; its eventual commit is therefore fail-closed for this request. A
committed first claim rejects a settled reconciliation through the incremented
generation; an uncommitted one can be recovered. Refusal, store errors, a
second timeout, or an expired deadline all remain fail-closed.
After a successful receipt, the local state is checked again under the lock;
any intervening same-key failure or cooldown suppresses the replay.

## Reset path

Successful response settlement first loads the durable row. A failed lookup
does not establish a version fence, so it leaves the local state and marker
sets intact. A confirmed miss may remove only a local marker that has not been
updated since the lookup began. A present row is cleared by a conditional
update matching both its observed timestamp and admission generation. A false
row-count result means a newer durable writer won and the local state is kept.
A same-key success may reset the failure observation while an active replay
receipt remains in place; the receipt is cleared only by its owning replay's
generation-matched release.
Only after a successful CAS does the local state get removed, and a local
failure that arrived after the lookup still wins the post-CAS check.

Expired-row purges compare both the observed timestamp and
``admission_generation`` and only delete rows with no active claim lease. The
per-key loader and the batch cleanup scheduler carry the generation and claim
receipt selected by their read into the delete predicate, so a claim that
advances the generation cannot be deleted by a stale purge and later recreated
from generation zero. A terminal request releases its marker by matching the
claimed generation and optional timestamps; a release from an older owner
cannot clear a reclaimed marker. If that conditional delete returns no match
or cannot complete, the loader reports an uncertain stale purge to its caller;
pre-created admission remains fail-closed for that call rather than using an
untrusted local fallback. The result is carried per call so concurrent loads
cannot clear each other's uncertainty.

## Delayed failure merge

Failure persistence continues to merge by the existing base observation
timestamp and failure-count rules. It never rewrites `admission_generation`.
Thus a failure write delayed by a skewed wall clock can merge after a replay
claim while the independent integer continues to fence a later claim.

## Proof seams

- Unit tests cover immutable snapshot construction, local pre/post checks,
  unrelated-key concurrency, timeout reconciliation, and marker cleanup.
- Durable integration tests cover SQLite `RETURNING` claims, stale-generation
  refusal, active-lease purge blocking, expired-marker reclaim, absent-row
  races, generation/receipt-fenced clears, migration upgrade/downgrade, and
  delayed failures.
- The call-site regression passes the original bridge request deadline into the
  claim; no retry can spend an unbounded second claim timeout.
