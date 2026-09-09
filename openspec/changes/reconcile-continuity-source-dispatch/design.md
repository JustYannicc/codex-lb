## Context

See proposal.md for motivation. Initial candidate is `2ce9335614`; the pinned
target is `5794d8d7a`. Upstream archives the original ownership change and adds
source dispatch plus dashboard resilience binding. The canonical Responses
ownership requirement and the upstream source-dispatch requirements remain
authoritative. Prior candidate verification is historical, not composition proof.

## Goals / Non-Goals

Preserve both accepted behaviors without changing overflow activation,
conversation scoping, replay policy, or account-deletion visibility. Do not
replace source lifecycle ownership with test doubles in positive route proofs.

## Decisions

Keep the enum-valued ownership resolver and boolean wrapper next to the new
overflow selector. Choosing one side wholesale either returns a boolean from
the enum resolver or removes the upstream selector.

Resolve subscription continuity before source admission and dispatch. A recorded
`resp_*` owner stays on its subscription account even when a source serves the
model. The same anchor without a recorded owner may reach that source and
finalize one reservation. Wrapping construction/claim spies, real request logs,
ASGI responses, and a local upstream prove the distinction. Existing upstream
tests retain cancellation, admission, limited-key estimate, and cleanup proof.

Keep compact's moved ownership and settlement block. Transplant only the
dashboard resilience binding after its moved settings read. Keeping both blocks
would duplicate cleanup and restore the old owner-count behavior. The forwarded
receiver still leaves failed pre-acknowledgement reservations with the origin;
deferred health and cancellation handling remain behind confirmed settlement.

## Risks / Trade-offs

Provider portability keeps its stricter generated-marker shape check separate
from subscription marker compatibility. A readable `turn_example` marker can
use the subscription sole-owner fallback, but that does not make its body safe
to move to another provider. The portability predicate retains upstream's
32-lowercase-hex marker rule. Its closed decline reason remains
`turn_state_bound`; overflow activation and subscription compatibility are
unchanged. The two upstream assertions exposed this coupling in hosted CI.

- Text composition can hide lifecycle regressions. Run route-level ownership
  cases plus existing source-dispatch and compact-settlement controls.
- Removed environment settings can survive in older tests. Keep their values
  on the existing dashboard snapshot, not a new configuration fallback.
- A passing earlier head does not clear this one. Bind local reviews and hosted
  checks to the final composition; retain old failures and reviews separately.

## Migration Plan

No migration or deployment is part of this reconciliation. Publish the reviewed
composition with an exact expected-head lease. Preserve the previous commit and
its evidence as the recovery point. Inherited upstream migrations are unchanged.
