# live-usage-ingestion Delta

## ADDED Requirements

### Requirement: Live usage account attribution requires explicit identity proof

Live usage ingestion MUST attribute a snapshot to a persisted account row only
when the supplied internal account ID exactly matches that row, or when the
snapshot also supplies a ChatGPT account identity that resolves to exactly one
persisted account row. A workspace-local suffix, shard suffix, or other string
shape on an unknown internal account ID MUST NOT by itself justify stripping or
rewriting the ID.

When neither identity path resolves to exactly one persisted account row, the
snapshot MUST be dropped without failing the proxied request. After a raw
snapshot identity resolves to a persisted account row, duplicate coalescing
MUST use that resolved account ID so repeated live snapshots do not bypass the
per-account write interval.

#### Scenario: Hub-published snapshot resolves through ChatGPT identity

- **GIVEN** a proxy path publishes a live usage snapshot with a workspace-suffixed internal ID
- **AND** it also supplies a ChatGPT account identity that maps to exactly one persisted account
- **WHEN** the live usage ingestor persists the snapshot
- **THEN** the usage rows are written for the uniquely mapped persisted account

#### Scenario: Unproven suffix is dropped

- **GIVEN** a proxy path publishes a live usage snapshot with an internal ID that does not exactly match a persisted account row
- **AND** no unique ChatGPT account identity is supplied for that snapshot
- **WHEN** the live usage ingestor processes it
- **THEN** no usage rows are written for a guessed prefix account
- **AND** the proxied request is not failed

#### Scenario: Normalized aliases are coalesced

- **GIVEN** a raw snapshot identity has resolved to a persisted account row
- **WHEN** the same raw identity publishes an unchanged snapshot inside the write coalescing interval
- **THEN** the duplicate snapshot is skipped using the resolved account ID
