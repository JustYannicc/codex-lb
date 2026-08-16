# query-caching Delta

## MODIFIED Requirements

### Requirement: Projection history reads are bounded per account
The dashboard projections history fetch MUST NOT widen every account's
lookback to the widest account window. On PostgreSQL the bulk usage-history
read MUST bound rows per account by that account's own window cutoff, and
MUST additionally bound each account's slice to a newest-first per-account
row cap supplied by the projections caller. The cap MUST be sized to cover
every projection consumer's lookback (the recent-burn window and the
maximum pace-smoothing window) at supported sample cadences, so capping
changes no consumer-visible value. Capped slices MUST keep the newest
in-cutoff rows and MUST remain ordered oldest-first. For accounts whose
in-cutoff rows do not exceed the cap, the returned histories MUST equal the
previous shared-floor fetch after the existing per-account trimming; for
accounts over the cap, the returned history MUST be exactly the newest
cap-many rows of that slice.

#### Scenario: One weekly account does not widen the fetch for short-window accounts
- **GIVEN** one account with a 7-day window and several accounts with 5-hour windows
- **WHEN** the projections history fetch runs on PostgreSQL
- **THEN** rows for the 5-hour accounts MUST be bounded by their own cutoff in SQL
- **AND** each account's resulting history slice MUST equal the slice the shared-floor fetch produced after per-account trimming

#### Scenario: A dense account returns only its newest rows
- **GIVEN** an account whose in-cutoff usage-history rows exceed the per-account row cap
- **WHEN** the projections history fetch runs on PostgreSQL
- **THEN** the account's slice MUST be exactly the newest cap-many in-cutoff rows, ordered oldest-first
- **AND** accounts whose in-cutoff rows do not exceed the cap MUST return their full trimmed slice unchanged

#### Scenario: Capped probes stay index-only
- **GIVEN** usage history rows for multiple accounts and a populated visibility map
- **WHEN** the capped per-account probe shape is EXPLAINed on PostgreSQL with sequential and bitmap scans disabled
- **THEN** the plan MUST serve each probe as an Index Only Scan over the covering indexes with no sequential scan of `usage_history`

#### Scenario: SQLite snapshot cache keeps the shared floor
- **GIVEN** the SQLite backend serves the projections history fetch through its snapshot cache
- **WHEN** per-account cutoffs and a per-account row cap are supplied
- **THEN** the SQLite read MAY keep the shared floor and MAY ignore the row cap
- **AND** per-account trimming in the caller MUST still bound each account's slice
