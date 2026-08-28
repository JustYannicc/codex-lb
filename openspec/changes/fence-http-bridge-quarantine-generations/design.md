## Design

The quarantine registry remains an in-memory map owned by one proxy service.
Each entry keeps its key, reason, TTL/last-touch fields, and a weak reference
to the session that armed the entry. A service-level counter allocates the next
generation before the entry is updated. The counter survives entry pruning and
is never derived from the current map alone.

Primary-key cleanup is identity fenced. A completion may clear the entry when
the entry's weak owner is the completing session, or when the completing
session is the current value in `_http_bridge_sessions` for that key. A
detached predecessor therefore cannot clear a replacement's entry, even if a
mutable `session.quarantined` flag was reset or an object id was recycled.

Recovery-origin cleanup is observation fenced. The recovery captures the active
generation before authorization. If it observed no entry, it passes `None` and
must not clear an entry that appeared later. If it observed a generation, only
the exact surviving generation may be cleared; a pruned-and-reused key or any
new arm is left intact. The same rule applies when the recovery-origin key is
also the completing session's primary key.

TTL and size pruning remain the only automatic expiry mechanisms. Successful
completion clears only quarantine state; it does not touch retry-circuit,
account-health, routing, or durable-owner state. Delta-only anchor selection is
kept explicit in the main Responses contract: a quarantined live session is
absent as a local session candidate, but the durable anchor remains available
when the request itself does not carry a full resend.

## Proof seams

- Direct retirement and completion on one session clear a matching entry.
- A replacement under the same key keeps its newer entry when the detached
  predecessor completes.
- A generation captured before TTL pruning cannot clear a newly armed entry on
  the reused key.
- A recovery that observed absence cannot clear an entry armed while it was in
  flight, for both distinct-key and same-key cleanup.
- Weak references compare object lifetime rather than integer ids.
