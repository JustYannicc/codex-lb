## Design

The implementation follows the decisions and migration notes in [context.md](context.md). It removes the rollback retry, orders qualifying transitions newest first, and compares SQLite DATETIME text with formatted whole-second reset boundaries. A merge revision preserves historical migration bytes.

## Verification

Database-backed tests reproduced the rollback and both transition selection failures before repair. The focused usage/account/migration suite passed 433 tests with 22 expected skips. Full type checking passed. SQLite upgrade and schema check reached one head with no drift. PostgreSQL-only cases were skipped; PostgreSQL execution is not claimed.
