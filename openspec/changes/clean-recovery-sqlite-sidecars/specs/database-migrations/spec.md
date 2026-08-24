# database-migrations Delta

## ADDED Requirements

### Requirement: SQLite recovery MUST fence replacement sidecars

When recovery writes or installs a file-backed SQLite replacement, it MUST
remove the target's `-wal`, `-shm`, `-journal`, and master-journal sidecars
before and after dump import. With `--replace`, it MUST remove source sidecars
before moving the source to its corrupt backup. Master-journal matching MUST
treat the database basename literally.

#### Scenario: A stale source WAL cannot attach to the replacement

- **GIVEN** recovery is replacing a file-backed SQLite database
- **AND** a source WAL is created after the dump is read
- **WHEN** recovery moves the source aside and installs the output
- **THEN** source and output SQLite sidecars MUST be absent
- **AND** reopening the installed database MUST not apply stale WAL rows

#### Scenario: Wildcard names do not broaden cleanup

- **GIVEN** the database basename contains a glob metacharacter
- **AND** an unrelated database has a matching-looking master journal
- **WHEN** recovery cleans the target sidecars
- **THEN** the target journal MUST be removed
- **AND** the unrelated journal MUST remain
