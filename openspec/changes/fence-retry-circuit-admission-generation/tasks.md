## 1. Specification

- [x] 1.1 Define the immutable generation, atomic claim, deadline, and reset
  contracts in the delta spec.
- [x] 1.2 Record the current-main boundary: the admission-generation column
  and model are inherited from merged #1863; no migration is added here.

## 2. Implementation

- [x] 2.1 Add the typed immutable local/durable generation snapshot and carry
  it through stale-anchor claim state.
- [x] 2.2 Make the durable claim dialect-guarded and `RETURNING`-based, and
  make conditional clears return whether they matched the captured generation.
- [x] 2.3 Bound claims and one timeout reconciliation by the caller deadline;
  perform local pre/post-CAS checks and retain local state on failures.
- [x] 2.4 Preserve admission generation while merging delayed failure writes.

## 3. Coverage

- [x] 3.1 Cover local/remote claim races, stateless marker cleanup, and the
  timeout reconciliation outcomes.
- [x] 3.2 Cover generation-fenced clear races, lookup failure retention, and
  delayed clock-skewed failure merges on SQLite.
- [x] 3.3 Run focused retry-circuit/durable bridge tests plus lint, format,
  type, architecture, and strict OpenSpec validation where the environment
  provides the CLI.

## 4. Review follow-ups

- [x] 4.1 Keep failed-claim cooldown diagnostics within the caller's remaining
  request deadline, including cancellation-resistant durable lookups.
- [x] 4.2 Detach cancellation-resistant claim operations at the deadline and
  suppress concurrent reconciliation while the original write is still
  running.
- [x] 4.3 Fence per-key and batch stale purges on captured `updated_at_epoch`
  plus `admission_generation`; cover claim-versus-purge and delayed-failure
  races.
