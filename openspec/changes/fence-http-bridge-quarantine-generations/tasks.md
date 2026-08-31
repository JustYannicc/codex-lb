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
