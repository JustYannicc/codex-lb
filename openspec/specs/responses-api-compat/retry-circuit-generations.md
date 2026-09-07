# Retry-circuit generation context

The generation and claim-receipt requirements in [spec.md](spec.md) describe
the implementation in `fence-retry-circuit-admission-generation`. A successful
claim owns one immutable receipt; terminal cleanup uses that receipt so an
older request cannot clear a later replay's protection.

Local deadline arithmetic and scheduled cleanup use the service clock and
scheduler. Durable expiry and reclaim continue to use database statement time.
For example, a caller with one attempt left cannot spend a second attempt on
timeout reconciliation. A caller with remaining budget may reconcile once
after the first write settles cancellation.

An ambiguous send or unconfirmed release can retain a receipt until expiry.
The stranded-receipt policy remains an explicit maintainer decision in the
[change design](../../changes/fence-retry-circuit-admission-generation/design.md#open-decision-stranded-claim-receipt-lockout).
Syncing these requirements does not resolve task 4.11, approve a shorter
lease or reclaim owner, or make `Retry-After` lease-aware. The change remains
active until that decision and the remaining delivery gates are satisfied.
