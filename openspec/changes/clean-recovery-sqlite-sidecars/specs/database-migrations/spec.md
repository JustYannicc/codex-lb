# database-migrations Delta

## ADDED Requirements

### Requirement: SQLite recovery MUST fence replacement sidecars

When recovery writes or installs a file-backed SQLite replacement, it MUST
remove the target's `-wal`, `-shm`, `-journal`, and master-journal sidecars
before and after dump import. With `--replace`, it MUST remove source sidecars
before moving the source to its corrupt backup. Master-journal matching MUST
treat the database basename literally. Before final output import and sidecar
cleanup, recovery MUST acquire an exclusive SQLite transaction on the source
and MUST close every recovery-opened SQLite connection before any sidecar or
database rename.
If an active connection prevents the lock, or sidecar cleanup fails, recovery
MUST fail without moving the source or installing the output.

#### Scenario: A stale source WAL cannot attach to the replacement

- **GIVEN** recovery is replacing a file-backed SQLite database
- **AND** a source WAL is created after the dump is read
- **WHEN** recovery moves the source aside and installs the output
- **THEN** source and output SQLite sidecars MUST be absent
- **AND** reopening the installed database MUST not apply stale WAL rows

#### Scenario: An active writer cannot cross the fenced preparation boundary

- **GIVEN** a source connection is open while recovery is replacing the database
- **WHEN** that connection attempts a write during final import and cleanup
- **THEN** the write MUST fail with the source's exclusive recovery lock held
- **AND** a fresh connection MUST be able to write to the installed database

#### Scenario: Recovery closes handles before Windows renames

- **GIVEN** recovery has prepared an output replacement
- **WHEN** it moves the source to its corrupt backup and the output into place
- **THEN** every recovery-opened SQLite connection MUST already be closed before each rename
- **AND** both file mutations MUST succeed on a platform with exclusive rename handles

#### Scenario: A busy source fails closed before replacement

- **GIVEN** another process already holds a conflicting SQLite write lock
- **WHEN** recovery cannot acquire its exclusive source lock
- **THEN** recovery MUST fail
- **AND** the source MUST remain at its original path
- **AND** no replacement MUST be installed

#### Scenario: Partial sidecar cleanup fails closed

- **GIVEN** one target sidecar cannot be removed while other sidecars can be removed
- **WHEN** recovery prepares a replacement
- **THEN** recovery MUST fail before moving the source or installing the output
- **AND** the source MUST remain at its original path

#### Scenario: Output installation failure restores the source

- **GIVEN** the source has moved to its corrupt backup
- **AND** moving the recovered output into the source path fails
- **WHEN** recovery handles the replacement error
- **THEN** recovery MUST restore the corrupt backup to the original source path
- **AND** recovery MUST report the installation failure

#### Scenario: Wildcard names do not broaden cleanup

- **GIVEN** the database basename contains a glob metacharacter
- **AND** an unrelated database has a matching-looking master journal
- **WHEN** recovery cleans the target sidecars
- **THEN** the target journal MUST be removed
- **AND** the unrelated journal MUST remain
