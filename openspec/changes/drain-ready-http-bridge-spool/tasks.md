## 1. Background persistence

- [x] 1.1 Reproduce stalled burst drain through enqueue and the injected writer, record a failing test, then make the smallest scheduling fix that passes.
- [x] 1.2 Verify multi-operation fairness, ordered bounded batches, terminal completion and cancellation through public interfaces.

## 2. Verification and delivery

- [x] 2.1 Repeat pinned-base and candidate measurements with identical synthetic workloads and report percentiles, throughput, write count and limitations.
- [x] 2.2 Run affected tests, lint, type checks, architecture gates and strict OpenSpec validation; review exact base and candidate.
- [ ] 2.3 Sync and archive verified requirements, publish one issue-linked standalone PR and record hosted state plus monitoring ownership.
