## Implementation
- [x] Add authenticated context routing, ownership, bounded fan-out and trusted result replay.
- [x] Preserve scope, cancellation and replay boundaries with integration tests.
- [x] Fix dashboard request-log schema and add a mixed-page regression.
- [x] Rebase onto current main and consolidate OpenSpec into one active change.
- [x] Re-parent the context migration after subscription overflow and verify the graph.
- [x] Route clocks, deadlines and fan-out through injected collaborators.
- [x] Remove duplicate frame parsing and repeated context database work.
- [x] Add focused regressions for cache behavior, ownership, transactions and injected scheduling.

## Verification
- [x] Run affected context/transport/migration tests and relevant static guards.
- [x] Validate the active change and owning specs.
- [ ] Update PR description and respond to the maintainer with evidence and design tradeoffs.

Full CI runs in GitHub Actions. Local verification here is scoped to the affected behavior; earlier test counts belong to earlier commits and are not cumulative.
