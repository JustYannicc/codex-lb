## 1. Quarantine registry fencing

- [x] 1.1 Add a service-lifetime monotonic generation counter.
- [x] 1.2 Store a weak session lifetime token on each quarantine entry.
- [x] 1.3 Fence primary-key cleanup by the canonical session registry and
  completing-session identity.
- [x] 1.4 Fence recovery-origin cleanup by exact observed generation, treating
  observed absence as a non-clearing fence.
- [x] 1.5 Keep TTL and size pruning bounded and preserve independent quarantine
  cleanup on successful replay.
- [x] 1.6 Add direct-retirement, key-reuse, detached-predecessor, TTL, and
  same-key race regressions.
- [x] 1.7 Run focused tests, lint, type checks, diff checks, and strict
  OpenSpec validation where the executable is available.
