## ADDED Requirements

### Requirement: Local integration upgrades preserve accepted persistent state

A local integration upgrade SHALL recognize the deployed migration revision and preserve account credentials, API keys, usage history, settings, and context ownership through the upgrade. It MUST retain accepted client endpoints and MUST NOT replace the database or stamp past missing migrations.

#### Scenario: Upgrade an accepted aggregate database
- **WHEN** the new local integration starts with a database at the previously accepted aggregate revision
- **THEN** its migration graph reaches one current head without unknown revision errors
- **AND** persisted account, settings, usage and context records remain readable

#### Scenario: Preserve accepted pooled Desktop usage
- **WHEN** the upgraded integration replaces a runtime with an embedded Desktop relay
- **THEN** the existing localhost relay endpoint remains available with its established Host and route validation
- **AND** pooled quota projection retains the ordinary signed-in account identity and account routing

#### Scenario: Candidate cannot pass migration rehearsal
- **WHEN** a disposable copy of the deployed schema cannot migrate and serve accepted client endpoints
- **THEN** the candidate is not eligible to replace the accepted live runtime
