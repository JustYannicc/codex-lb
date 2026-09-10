## 1. Repair

- [ ] 1.1 Pin actual main and reproduce populated public head-upgrade failure.
- [ ] 1.2 Preserve historical tests and add populated role/user/receipt parent and merge-only downgrade regressions.
- [ ] 1.3 Append the no-op join without modifying published migration history.

## 2. Verify

- [ ] 2.1 Verify CLI/drift and affected migrations, roles/users/permissions/CSRF contracts and PostgreSQL selection.
- [ ] 2.2 Run affected static and strict spec checks, preserving unchanged proof.
- [ ] 2.3 Obtain independent Medium review, sync and archive the locally verified change before normal publication.
