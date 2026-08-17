## MODIFIED Requirements

### Requirement: Codex compaction triggers are bridged into compact output

The proxy SHALL remove a single terminal top-level `{"type":"compaction_trigger"}` item from `POST /backend-api/codex/responses` before compact-input preparation, the internal compact request MUST contain exactly one terminal `compaction_trigger` item on the compact wire, and the proxy MUST reject duplicate or non-terminal top-level `compaction_trigger` placement locally with HTTP 400 `invalid_request_error` before upstream compact handling.

#### Scenario: terminal trigger becomes one compact-wire trigger

- **WHEN** a `POST /backend-api/codex/responses` request ends with exactly one
  top-level `compaction_trigger`
- **THEN** the proxy strips that trigger before compact-input preparation
- **AND** the internal compact request contains exactly one terminal
  `compaction_trigger` item on its `input` array

#### Scenario: malformed trigger placement is rejected locally

- **WHEN** a `POST /backend-api/codex/responses` or
  `POST /backend-api/codex/responses/compact` request contains duplicate or
  non-terminal top-level `compaction_trigger` items
- **THEN** the proxy returns HTTP 400 with `invalid_request_error`
- **AND** it does not attempt upstream compact handling

#### Scenario: Codex compact transport uses the Responses stream

- **WHEN** a valid terminal compaction trigger is submitted through a Codex
  compact flow
- **THEN** the proxy sends the compact request to
  `POST /backend-api/codex/responses` with `stream=true` and `store=false`
- **AND** it accepts the upstream SSE response and reconstructs one normalized
  compact response item from the terminal response lifecycle
- **AND** it does not require the legacy `/backend-api/codex/responses/compact`
  upstream route to be available

#### Scenario: Standalone Codex compact remains a compatibility endpoint

- **WHEN** a client calls `POST /backend-api/codex/responses/compact`
- **THEN** codex-lb preserves the endpoint and its subscription-backed compact
  routing contract
- **AND** malformed duplicate or non-terminal top-level triggers are rejected
  locally before any upstream compact attempt

#### Scenario: OpenAI-compatible compact normalizes duplicate triggers

- **WHEN** a client calls `POST /v1/responses/compact` with duplicate
  top-level `compaction_trigger` items
- **THEN** codex-lb preserves the existing compatibility behavior and returns
  HTTP 200 when the compact operation succeeds
- **AND** the forwarded compact input contains one terminal trigger
