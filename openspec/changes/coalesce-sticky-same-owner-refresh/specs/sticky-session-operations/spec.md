## ADDED Requirements

### Requirement: Same-owner sticky refresh writes are coalesced

When selection retains the existing pinned owner of a TTL-based sticky mapping, the
mapping write exists only to advance the mapping's freshness timestamp. The system
MUST skip that write when the same request's owner lookup already observed the row
with a freshness timestamp younger than a bounded skip window, so concurrent requests
of one hot session do not serialize on the same row's lock.

The skip window MUST NOT exceed 1% of the mapping's configured TTL and MUST NOT
exceed 15 seconds, so a mapping's effective expiry — on both the read-path TTL check
and the background cleanup loop — moves at most that window earlier than today's
write-per-request behavior.

The skip decision MUST be derived from row state observed in the current request's
database lookup, not from cross-request in-process state, so any number of workers or
replicas remain correct.

A skip MUST apply only to a pure freshness rewrite. The following writes MUST remain
immediate and unconditional: rebinding the mapping to a different account, deleting
the mapping, restoring a provisional owner after failed admission, initializing a
seed mapping, and any upsert against a row carrying an abandonment marker (whose
write also clears the marker columns). A raw legacy owner that shadows the namespaced
row MUST NOT inherit the namespaced row's freshness observation.

#### Scenario: Hot same-owner retention skips the redundant refresh write

- **GIVEN** a `prompt_cache` mapping pinned to an eligible account
- **AND** the request's owner lookup observed the row fresher than the skip window
  with no abandonment marker
- **WHEN** selection retains the pinned account
- **THEN** the request routes to the pinned account
- **AND** no sticky-session write is issued for the retention

#### Scenario: Retention outside the skip window refreshes write-through

- **GIVEN** a `prompt_cache` mapping pinned to an eligible account
- **AND** the row's freshness timestamp is older than the skip window but inside the TTL
- **WHEN** selection retains the pinned account
- **THEN** the mapping's freshness timestamp is advanced by a write

#### Scenario: Rebind is never coalesced

- **GIVEN** a soft mapping whose row was observed fresher than the skip window
- **WHEN** selection rebinds the mapping to a different account
- **THEN** the rebind is persisted immediately

#### Scenario: A skipped refresh does not clobber a concurrent rebind

- **GIVEN** a request that observed a fresh same-owner row and skipped its refresh write
- **AND** a concurrent request rebinds the same mapping to another account
- **WHEN** both requests complete
- **THEN** the mapping's owner is the rebind target
