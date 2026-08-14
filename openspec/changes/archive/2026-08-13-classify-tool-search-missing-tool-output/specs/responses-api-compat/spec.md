## MODIFIED Requirements

### Requirement: Missing-tool-output classification covers all tool call variants
The service MUST classify an upstream `invalid_request_error` with `param=input` whose message starts with `No tool output found for function call call_`, `No tool output found for custom tool call call_`, `No tool output found for apply patch call call_`, or `No tool output found for tool search call call_` as a missing-tool-output continuity error, so the existing masking and retry recovery paths engage instead of forwarding the raw upstream 400 downstream. The hosted `No tool output found for web search call` wording MUST NOT be classified, because a `web_search_call` is executed upstream and carries no client-addressable tool output.

#### Scenario: custom tool call variant is masked on the HTTP bridge
- **WHEN** upstream emits `invalid_request_error` with `param=input` and message `No tool output found for custom tool call call_x`
- **AND** the pending bridge request carries `previous_response_id`
- **THEN** the service rewrites the error to a retryable `stream_incomplete` continuity failure
- **AND** the raw upstream message and call id are not exposed downstream

#### Scenario: tool search call variant is masked on the HTTP bridge
- **WHEN** upstream emits `invalid_request_error` with `param=input` and message `No tool output found for tool search call call_x`
- **AND** the pending bridge request carries `previous_response_id`
- **THEN** the service rewrites the error to a retryable `stream_incomplete` continuity failure
- **AND** the raw upstream message and call id are not exposed downstream

#### Scenario: hosted web search wording stays unclassified
- **WHEN** upstream emits `invalid_request_error` with `param=input` and a message starting `No tool output found for web search call`
- **THEN** the service does not treat it as a missing-tool-output continuity error

### Requirement: Previous-response replay trimming handles tool-search output pairs
When a Responses HTTP bridge or WebSocket continuation carries `previous_response_id` and replays already-stored response output items before a fresh `tool_search_output`, the service MUST trim the replayed `tool_search_call` prefix and preserve the `tool_search_output` plus the fresh turn. The service MUST NOT forward both the replayed `tool_search_call` and its `tool_search_output` on top of the `previous_response_id` anchor.

#### Scenario: HTTP bridge trims replayed tool-search call prefix
- **GIVEN** an HTTP bridge session has a completed previous response
- **WHEN** the next request carries `previous_response_id` and input `[tool_search_call, tool_search_output, user_message]`
- **THEN** the upstream request keeps the same `previous_response_id`
- **AND** its input is `[tool_search_output, user_message]`

#### Scenario: WebSocket bridge trims replayed tool-search call prefix
- **GIVEN** a WebSocket Responses session has a completed previous response
- **WHEN** the next request carries `previous_response_id` and input `[tool_search_call, tool_search_output, user_message]`
- **THEN** the upstream request keeps the same `previous_response_id`
- **AND** its input is `[tool_search_output, user_message]`
