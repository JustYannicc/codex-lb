## Implementation
- [x] Accept context request-log rows and add a regression for mixed pages.
- [x] Synchronize the owning specification.

## Verification
- [x] Demonstrate the regression fails before the fix and passes afterward.
- [x] Run focused dashboard checks and strict OpenSpec validation.

Validation: the new mixed-page regression failed before the schema fix. Afterward, 94 tests passed across dashboard schemas, request-log hooks and the recent-requests table. Type checking and targeted ESLint passed. The captured 25-row production response, including a context row, also validates. Strict validation passed for this change and the owning specification. Global strict spec validation has the same 22 failures as unchanged HEAD, with no new failures. Full CI is delegated to GitHub Actions.
