## Context

Recovery exports the source and imports a dump into a new output before an
optional replacement. SQLite sidecars are separate filesystem entries and are
not part of the dump, so they must be removed at each replacement boundary.

## Decisions

- Remove `-wal`, `-shm`, and `-journal` by exact path.
- Remove `-mj*` master journals by globbing an escaped database basename.
- Fail recovery rather than install an ambiguous replacement when sidecar
  removal reports an error.

## Proof seam

Recovery tests hold a source WAL open across dump creation, seed output
sidecars, and verify the installed database and both sidecar sets. A wildcard
filename test proves unrelated master journals remain untouched.

## Dependencies

None. The implementation and proof stand on the beta.4 base without the
startup run-state candidate.
