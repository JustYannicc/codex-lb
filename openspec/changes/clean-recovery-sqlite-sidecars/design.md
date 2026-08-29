## Context

Recovery exports the source and imports a dump into a new output before an
optional replacement. SQLite sidecars are separate filesystem entries and are
not part of the dump, so they must be removed at each replacement boundary.

## Decisions

- Remove `-wal`, `-shm`, and `-journal` by exact path.
- Remove `-mj*` master journals by globbing an escaped database basename.
- Remove pre-existing output sidecars before opening the recovery lock so stale
  WAL/journal state cannot attach during import. Hold `BEGIN EXCLUSIVE` on the
  source across final output import. Release and close that connection before
  final output/source sidecar cleanup or either database rename because Windows
  rejects filesystem mutation with an open SQLite handle. Repeat source cleanup
  after moving the source to its backup so sidecars recreated around that move
  are removed before the recovered output is installed. The exclusive
  transaction remains the pre-replacement race/ownership fence: active writers
  fail closed while the replacement is prepared, and a lock failure aborts
  before any rename. Closing the probe necessarily leaves a bounded post-probe
  window before the cleanup and renames; the operator must keep external
  writers quiescent throughout that window.
- Fail recovery rather than install an ambiguous replacement when sidecar
  removal reports an error.
- Treat the two filesystem renames as a small transaction: if installing the
  output fails after the source moved to its backup, restore the backup to the
  source path and report the original failure. If restoration also fails,
  include both errors so the operator can recover the preserved backup.

## Proof seam

Recovery tests hold a source WAL open across dump creation, seed output
sidecars, and verify the installed database and both sidecar sets. A boundary
test attempts a write while the exclusive lock is held and verifies that a
fresh connection writes to the installed database. A filesystem seam tracks
every sidecar unlink and database rename, asserting that every tracked recovery
connection is closed first; it also recreates a source sidecar around the
source move to prove the repeat cleanup. Partial cleanup, busy-source, and
second-rename failures prove the replacement fails closed, and a wildcard
filename test proves unrelated master journals remain untouched.

## Dependencies

The implementation and proof stand on the beta.4 base without the startup
run-state candidate. The hosted Contributors attribution check is a merge
dependency on #1902, the sole carrier of contributor metadata; this change
must not duplicate `.all-contributorsrc` or README edits.
