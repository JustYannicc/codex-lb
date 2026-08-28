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
