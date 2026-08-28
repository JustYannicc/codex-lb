## Why

HTTP bridge quarantine is process-local state keyed by a reusable session key.
The current entry generation is allocated from the entry itself, and cleanup
uses only that key (or a caller-provided generation). After TTL/size pruning,
the same key can receive a recycled generation. A detached predecessor can
then finish after a replacement has reused the key and clear the replacement's
quarantine. A completion can also clear a quarantine that was armed after the
recovery observed an absent entry.

## What changes

- Allocate quarantine generations from a service-lifetime monotonic counter so
  pruning never makes an old observation valid for a reused key.
- Keep a weak session lifetime token on each entry and require the completing
  session to remain the canonical primary session (or the entry owner) before
  clearing the primary key.
- Treat an observed quarantine generation, including an observed absence, as an
  exact cleanup fence for recovery-origin keys.
- Keep quarantine bounded by its existing TTL and size cap, and keep successful
  replay cleanup independent from retry-circuit state, account health, routing,
  and durable ownership.
- Clarify the selection contract: quarantine makes a live session unavailable
  for local reuse and anchor-presence checks, while a delta-only request may
  still use its durable anchor because it has no other context source.

## Non-goals

- No retry-circuit threshold, cooldown, half-open lease, poison policy, or
  durable-anchor mutation.
- No account-health, routing-score, account-eligibility, or durable-owner
  writes.
- No replay payload, operation journal, attribution, or transport recovery
  changes.
