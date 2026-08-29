## ADDED Requirements

### Requirement: Previous-response source routing follows proven ownership

When a Responses request carries `previous_response_id`, the proxy MUST resolve
recorded subscription-account ownership independently from model-source catalog
ownership. The proxy MUST NOT infer either outcome from the response identifier's
syntax. A recorded subscription owner MUST keep the request on subscription
routing. A missing subscription owner MUST NOT fail the request by itself: when
subscription routing remains eligible, the proxy MUST count eligible subscription
accounts after applying API-key account-assignment scoping. Exactly one eligible
account MUST be allowed to proceed through normal subscription selection; zero or
multiple eligible accounts MUST fail closed with the sanitized
`previous_response_owner_unavailable` error. Account-pinned file requests remain
strict and do not use the sole-candidate fallback. Codex compaction remains
subscription-only; its dedicated compact HTTP selection uses the same
sole-candidate compatibility fallback. If the source catalog confirms source
ownership and no subscription owner is recorded, the configured model source remains
authoritative for HTTP; the direct Responses WebSocket transport MUST retain its
`model_source_requires_http_transport` fallback. An unavailable source-catalog
lookup is distinct from an owner miss: the direct WebSocket path MUST preserve
its existing subscription fallback instead of converting the lookup failure into
`previous_response_owner_unavailable`.

#### Scenario: Recorded subscription owner overrides an HTTP model source

- **GIVEN** a Responses-compatible source is configured for the requested model
- **AND** request logs record a subscription account as the owner of `previous_response_id`
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the request is not forwarded to the model source
- **AND** subscription routing preserves the recorded account owner

#### Scenario: Canonical source response ID remains source-routed over HTTP

- **GIVEN** a Responses-compatible source is configured for the requested model
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** the source catalog confirms that the requested model is source-owned
- **AND** `previous_response_id` uses a canonical OpenAI-compatible `resp_` hexadecimal shape
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the request is forwarded to the configured model source

#### Scenario: Known subscription-model owner miss fails closed over HTTP

- **GIVEN** the requested model is known to subscription routing
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** zero or multiple eligible subscription accounts remain after applying
  API-key account-assignment scoping
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the proxy returns HTTP status `502`
- **AND** the sanitized error code is `previous_response_owner_unavailable`
- **AND** the sanitized error message is `Previous response owner account is unavailable; retry later.`
- **AND** no subscription account is selected and no upstream request is dispatched

#### Scenario: Sole eligible subscription account preserves an HTTP continuation

- **GIVEN** the requested model is known to subscription routing
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** exactly one eligible subscription account remains after applying
  API-key account-assignment scoping
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the proxy proceeds through normal subscription account selection
- **AND** the request is forwarded to that sole eligible subscription account
- **AND** the `previous_response_id` is preserved in the upstream request

#### Scenario: Turn-state ownership bypasses owner-miss candidate fallback

- **GIVEN** no subscription account is recorded as owner of `previous_response_id`
- **AND** a turn-state header identifies a subscription account owner
- **WHEN** the client submits an HTTP Responses or compact continuation
- **THEN** the proxy reconciles the turn-state owner through normal owner resolution
- **AND** the proxy does not apply the zero-or-multiple-candidate owner-miss failure

#### Scenario: Direct WebSocket preserves a recorded subscription owner

- **GIVEN** a source is also configured for the requested model
- **AND** request logs record a subscription account as the owner of `previous_response_id`
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the request remains on the owner-bound subscription WebSocket path
- **AND** the proxy does not emit `model_source_requires_http_transport`

#### Scenario: Direct WebSocket source continuation falls back to HTTP

- **GIVEN** a source is configured for the requested model
- **AND** the source catalog confirms that the requested model is source-owned
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** `previous_response_id` uses a canonical OpenAI-compatible `resp_` hexadecimal shape
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the proxy emits `model_source_requires_http_transport`
- **AND** the service-level error uses HTTP status `503`
- **AND** the request is not sent to a subscription upstream

#### Scenario: Known subscription-model owner miss fails closed on direct WebSocket

- **GIVEN** the requested model is known to subscription routing
- **AND** the source catalog lookup succeeds without confirming source ownership
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** zero or multiple eligible subscription accounts remain after applying
  API-key account-assignment scoping
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the proxy emits a terminal error with HTTP status `502`
- **AND** the sanitized error code is `previous_response_owner_unavailable`
- **AND** the sanitized error message is `Previous response owner account is unavailable; retry later.`
- **AND** no subscription account is selected and no upstream request is dispatched

#### Scenario: Direct WebSocket candidate lookup failure fails closed

- **GIVEN** the requested model is known to subscription routing
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** loading eligible subscription candidates fails
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the proxy emits the sanitized `previous_response_owner_unavailable` terminal error
- **AND** the lookup failure is not exposed to the client

#### Scenario: Sole eligible subscription account preserves a WebSocket continuation

- **GIVEN** the requested model is known to subscription routing
- **AND** the source catalog lookup succeeds without confirming source ownership
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** exactly one eligible subscription account remains after applying
  API-key account-assignment scoping
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the proxy proceeds through normal subscription account selection
- **AND** the request is forwarded to that sole eligible subscription account
- **AND** the `previous_response_id` is preserved in the upstream request

#### Scenario: Unavailable source-catalog lookup preserves subscription fallback

- **GIVEN** no subscription account is recorded as owner of `previous_response_id`
- **AND** the source-catalog lookup for the requested model is unavailable
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the proxy preserves the existing subscription account-selection path
- **AND** the request is forwarded to the selected subscription upstream
- **AND** the proxy does not emit `previous_response_owner_unavailable`
