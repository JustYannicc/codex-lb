## ADDED Requirements

### Requirement: Scheduled retry cleanup preserves changes after selection

Scheduled retry-circuit cleanup MUST delete only the observation timestamp, admission generation and consecutive-failure count selected for that key. A changed value MUST prevent deletion even when the row still satisfies retention eligibility. When any selected row fails its conditional deletion, the cleanup pass MUST stop after completing that selected batch and MUST NOT select the changed row again in the same pass. Existing retention grace, tombstone retention and live-continuity protection MUST remain in force.

#### Scenario: Replay claims after stale selection
- **GIVEN** cleanup selected an eligible stale retry-circuit row
- **WHEN** a replay claims a newer admission generation before deletion without advancing the observation timestamp
- **THEN** cleanup MUST preserve the claimed row and MUST NOT recapture it in that pass

#### Scenario: Lagging-clock failure follows stale selection
- **GIVEN** cleanup selected an eligible stale retry-circuit row or abandoned-anchor tombstone
- **WHEN** a failure increases the consecutive-failure count while its observation timestamp remains unchanged
- **THEN** cleanup MUST preserve the updated row and MUST NOT recapture it in that pass

#### Scenario: Observation advances within the retention window
- **GIVEN** cleanup selected an eligible stale retry-circuit row
- **WHEN** its observation timestamp changes but remains old enough for retention cleanup
- **THEN** cleanup MUST preserve the updated observation in that pass

#### Scenario: Mixed batch with unchanged stale rows
- **GIVEN** cleanup selected both an unchanged eligible row and a row subsequently changed by a replay or failure
- **WHEN** cleanup deletes that selected batch
- **THEN** it MUST delete and count the unchanged row, preserve the changed row, and stop that pass

#### Scenario: Unchanged rows retain existing cleanup eligibility
- **WHEN** selected rows do not change
- **THEN** cleanup MUST preserve the existing retention grace and tombstone/live-continuity protections and MUST continue deleting eligible rows across batches
