# database-migrations Delta

## ADDED Requirements

### Requirement: SQLite recovery MUST fence replacement sidecars

When recovery writes or installs a file-backed SQLite replacement, it MUST
remove the target's `-wal`, `-shm`, `-journal`, and master-journal sidecars
before and after dump import. With `--replace`, it MUST remove source sidecars
before moving the source to its corrupt backup. Master-journal matching MUST
treat the database basename literally. Before that final import and replacement
boundary, recovery MUST hold an exclusive SQLite transaction on the source;
if an active connection prevents the lock, recovery MUST fail without moving
the source or installing the output.

#### Scenario: A stale source WAL cannot attach to the replacement

- **GIVEN** recovery is replacing a file-backed SQLite database
- **AND** a source WAL is created after the dump is read
- **WHEN** recovery moves the source aside and installs the output
- **THEN** source and output SQLite sidecars MUST be absent
- **AND** reopening the installed database MUST not apply stale WAL rows

#### Scenario: An active writer cannot cross the replacement boundary

- **GIVEN** a source connection is open while recovery is replacing the database
- **WHEN** that connection attempts a write during the final import and rename
- **THEN** the write MUST fail with the source's exclusive recovery lock held
- **AND** a fresh connection MUST be able to write to the installed database

#### Scenario: A busy source fails closed before replacement

- **GIVEN** another process already holds a conflicting SQLite write lock
- **WHEN** recovery cannot acquire its exclusive source lock
- **THEN** recovery MUST fail
- **AND** the source MUST remain at its original path
- **AND** no replacement MUST be installed

#### Scenario: Wildcard names do not broaden cleanup

- **GIVEN** the database basename contains a glob metacharacter
- **AND** an unrelated database has a matching-looking master journal
- **WHEN** recovery cleans the target sidecars
- **THEN** the target journal MUST be removed
- **AND** the unrelated journal MUST remain
