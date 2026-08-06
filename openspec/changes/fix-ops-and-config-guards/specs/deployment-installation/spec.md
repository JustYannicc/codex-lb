## MODIFIED Requirements

### Requirement: Production Compose backend has drain-safe stop grace

The production Compose backend service MUST set `stop_grace_period` to a value greater than or equal to the application's complete shutdown drain and cleanup budget.

#### Scenario: Compose restart preserves backend draining

- **WHEN** the production Compose service receives a stop request
- **THEN** Docker allows at least the configured application drain budget before SIGKILL
