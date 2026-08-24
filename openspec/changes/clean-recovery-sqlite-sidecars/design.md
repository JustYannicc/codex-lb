## Context

Recovery exports the source and imports a dump into a new output before an
optional replacement. SQLite sidecars are separate filesystem entries and are
not part of the dump, so they must be removed at each replacement boundary.

## Decisions

- Remove `-wal`, `-shm`, and `-journal` by exact path.
- Remove `-mj*` master journals by globbing an escaped database basename.
- Hold `BEGIN EXCLUSIVE` on the source across final output import, sidecar
  cleanup, and source replacement. A lock failure aborts before any rename,
  so an active connection cannot write the old inode after installation.
- Fail recovery rather than install an ambiguous replacement when sidecar
  removal reports an error.

## Proof seam

Recovery tests hold a source WAL open across dump creation, seed output
sidecars, and verify the installed database and both sidecar sets. A boundary
test attempts a write while the exclusive lock is held and verifies that a
fresh connection writes to the installed database. A wildcard filename test
proves unrelated master journals remain untouched.

## Dependencies

None. The implementation and proof stand on the beta.4 base without the
startup run-state candidate.
