## 1. Quarantine registry fencing

- [x] 1.1 Add a service-lifetime monotonic generation counter.
- [x] 1.2 Store a weak session lifetime token on each quarantine entry.
- [x] 1.3 Fence primary-key cleanup by canonical-session precedence, with the
  weak owner as a fallback only when no canonical primary is registered; keep
  detached predecessors from clearing first-strike evidence.
- [x] 1.4 Capture the primary generation before completion awaits and fence its
  cleanup by the exact observed generation, including observed absence.
- [x] 1.5 Fence recovery-origin cleanup by exact observed generation, treating
  observed absence as a non-clearing fence.
- [x] 1.6 Keep TTL and size pruning bounded and preserve independent quarantine
  cleanup on successful replay.
- [x] 1.7 Add direct-retirement, key-reuse, detached-predecessor, TTL, and
  same-key race regressions.
- [x] 1.8 Add a completion-path regression for a quarantine armed while
  retry-circuit settlement awaits.
- [x] 1.9 Run focused tests, lint, type checks, diff checks, and strict
  OpenSpec validation where the executable is available.
- [x] 1.10 Preserve the pre-await completion fence through durable load and
  settlement awaits, including an observed absence, with a regression for a
  quarantine armed during that load.
- [x] 1.11 Allocate quarantine-generation transitions through the service
  allocator and cover revoke/downgrade cross-key uniqueness regressions.
- [x] 1.12 Preserve a post-fence first eventless strike when clearing matched
  poison provenance, define the full-resend/delta-only classifier boundaries
  and precedence in the Responses contract, and add regressions.
- [x] 1.13 Capture raw generation alongside poison provenance so pre-fence
  first strikes reset correctly, and classify one-item arrays using the
  compact serialization of the entire array.
- [x] 1.14 Preserve the original raw-string input length through request
  validation so array normalization cannot change the full-resend boundary.
- [x] 1.15 Discard expired suppressed-weaker markers before deciding whether
  a post-capture first eventless strike survives poison cleanup.
- [x] 1.16 Preserve raw-string input provenance across the internal owner
  forwarding wire and bind its signature to the exact posted body.
- [x] 1.17 Preserve post-capture first-strike evidence when durable merge
  revokes speculative poison, and keep legacy-origin normalized one-item
  owner forwards delta-only when no exact-body signature proves raw shape.
- [x] 1.18 Fence poison cleanup by the captured eventless-timeout count so an
  expired weaker arm cannot make a pre-capture strike look new.
- [x] 1.19 Carry the full poison cleanup fence through durable-load miss,
  purge, and reset revocation paths so a post-capture first strike survives.
