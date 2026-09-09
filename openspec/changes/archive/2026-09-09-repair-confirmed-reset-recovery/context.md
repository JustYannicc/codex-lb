The existing recovery contract requires a current usage watermark, a matching block baseline, and the most recent adjacent reset pair. These repairs enforce that contract without adding a recovery policy.

A failed rollback compare-and-set means another writer changed the account. Retrying against a fresh active row can undo an operator's reactivation. The rollback therefore keeps its original expected values and stops on a miss. For example, a changed blocked_at on an otherwise identical active account belongs to the intervening writer.

SQLite stores observation timestamps with microseconds. Converting them to integer epoch seconds can move an observation back across a boundary. Compare those stored timestamps directly with reset boundaries formatted to the same precision.

The reset-transition index is a schema change. Historical migration bytes remain unchanged; a merge revision joins its branch to the current upstream head. SQLite upgrade/downgrade tests prove the index, and an empty-database upgrade/check proves the combined graph. PostgreSQL-specific concurrent-index behavior requires its own database and is not claimed by SQLite tests.
