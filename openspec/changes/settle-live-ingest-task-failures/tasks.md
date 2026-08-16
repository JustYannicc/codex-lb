## 1. Implementation

- [x] 1.1 Enroll ingestor-created tasks (consumer, trailing invalidation) in a
      weak ownership registry with named tasks.
- [x] 1.2 Attach a done callback that settles each task exactly once:
      retrieve the exception, log it with its traceback, and record it in the
      bounded failure handoff.
- [x] 1.3 Add the autouse test fence that stops leaked ingestor singletons,
      reaps pending ingestor-owned tasks (only those bound to the loop the
      reap runs on; foreign-loop tasks are enrolled and left inert), and
      drains the failure handoff after every test.
- [x] 1.4 Make the lifecycle instance-scoped: the lifespan holds the started
      instance and stops exactly that instance; stop clears the module global
      and publisher only when the stopped instance still owns them, so nested
      lifespans cannot orphan the outer ingestor into a GC-collectable cycle.

## 2. Validation

- [x] 2.1 Order-dependent regression pair proving a leaked consumer no longer
      crosses a test boundary (fails on main without the fence).
- [x] 2.2 Regressions for dead-consumer settlement, orphaned-task sweep,
      detached-death recording, queued-callback settlement, and exactly-once
      reporting.
- [x] 2.3 Regression for nested lifespans: a nested start/stop pair must not
      orphan, kill, or unhook the outer lifespan's ingestor, and the outer
      stop must reap its own consumer even after the global moved on.
- [x] 2.4 Run the full unit suite, live-usage integration tests, lint, type
      checks, and strict OpenSpec validation.
