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
