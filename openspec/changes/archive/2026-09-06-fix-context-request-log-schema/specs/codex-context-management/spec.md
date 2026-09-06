## ADDED Requirements

### Requirement: Context request logs remain readable in the dashboard
The dashboard request-log response schema SHALL accept `requestKind: "codex_context"` for successful and failed context operations without rejecting other rows or pagination metadata in the same response.

#### Scenario: Inference and context operations share a page
- **WHEN** a request-log response contains normal inference rows and successful or failed context rows
- **THEN** the dashboard accepts the complete page and preserves each row's request kind, status and pagination metadata
