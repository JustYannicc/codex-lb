## ADDED Requirements

### Requirement: Previous-response source routing follows proven ownership

When a Responses request carries `previous_response_id`, the proxy MUST resolve
recorded subscription-account ownership independently from model-source catalog
ownership. The proxy MUST NOT infer either outcome from the response identifier's
syntax. A recorded subscription owner MUST keep the request on subscription
routing. A missing subscription owner MUST first be evaluated against the
model-source catalog. If the source catalog confirms source ownership, the
configured model source remains authoritative even when exactly one subscription
account is eligible; the request MUST NOT use subscription candidate fallback.
For HTTP and compact subscription routing, eligible-account counting is
permitted only after the source catalog lookup succeeds without confirming
source ownership, applying API-key account-assignment scoping. Exactly one
eligible account MUST be allowed to proceed through normal subscription
selection; zero or multiple eligible accounts MUST fail closed with the sanitized
`previous_response_owner_unavailable` error. Account-pinned file requests remain
strict and do not use the sole-candidate fallback. Codex compaction remains
subscription-only; its dedicated compact HTTP selection uses the same
sole-candidate compatibility fallback. The direct Responses WebSocket transport
MUST retain its `model_source_requires_http_transport` fallback for confirmed
source ownership. An unavailable source-catalog lookup is distinct from an owner
miss: the direct WebSocket path MUST preserve its existing subscription fallback
instead of applying the successful-catalog precondition or converting the lookup
failure into `previous_response_owner_unavailable`.
A real client-supplied `x-codex-turn-state` is hard continuity evidence. When
that token cannot be resolved to an owner in the requesting API-key scope, the
proxy MUST fail closed and MUST NOT apply the sole-candidate fallback, even when
exactly one subscription account is eligible. Proxy-synthesized first-turn
placeholders (`turn_*` / `http_turn_*`) remain the only exception while they are
unregistered; a registered placeholder MUST resolve to its recorded owner. For
the same fail-closed decision, a physically present but blank
`x-codex-turn-state` header MUST be treated as client input rather than as an
omitted header and MUST NOT authorize synthesized provenance or sole-candidate
fallback. For the HTTP bridge owner-miss fallback, that exception MUST be
authorized by a server-generated marker carried in the authenticated internal
forward; a client-supplied value matching the `turn_*` / `http_turn_*` shape
MUST NOT qualify. On the direct Responses WebSocket path, the exception MUST
require an exact match with the synthesized marker generated for that handshake
or a server-side continuity record proving that the proxy previously issued the
marker; matching the synthesized-token shape alone MUST NOT qualify.

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

#### Scenario: Opaque source response ID remains source-routed over HTTP

- **GIVEN** a Responses-compatible source is configured for the requested model
- **AND** no subscription account is recorded as owner of `source-turn-opaque-42`
- **AND** the source catalog confirms that the requested model is source-owned
- **AND** `previous_response_id` is the opaque non-canonical value `source-turn-opaque-42`
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the request is forwarded to the configured model source
- **AND** routing is based on recorded ownership rather than identifier syntax

#### Scenario: Confirmed source ownership outranks a sole subscription candidate

- **GIVEN** a Responses-compatible source is configured for the requested model
- **AND** no subscription account is recorded as owner of `source-turn-sole-candidate`
- **AND** the source catalog confirms that the requested model is source-owned
- **AND** exactly one eligible subscription account remains after applying
  API-key account-assignment scoping
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the request is forwarded to the configured model source
- **AND** the sole subscription candidate is not selected

#### Scenario: Known subscription-model owner miss fails closed over HTTP

- **GIVEN** the requested model is known to subscription routing
- **AND** the source catalog lookup succeeds without confirming source ownership
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
- **AND** the source catalog lookup succeeds without confirming source ownership
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** exactly one eligible subscription account remains after applying
  API-key account-assignment scoping
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the proxy proceeds through normal subscription account selection
- **AND** the request is forwarded to that sole eligible subscription account
- **AND** the `previous_response_id` is preserved in the upstream request

#### Scenario: Unresolved client turn-state blocks the HTTP sole-candidate fallback

- **GIVEN** the requested model is known to subscription routing
- **AND** the source catalog lookup succeeds without confirming source ownership
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** the client supplies an `x-codex-turn-state` with no owner in the
  requesting API-key scope
- **AND** exactly one eligible subscription account remains
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the proxy returns HTTP status `502`
- **AND** the sanitized error code is `previous_response_owner_unavailable`
- **AND** no subscription account is selected and no upstream request is dispatched

#### Scenario: Blank client turn-state blocks the HTTP sole-candidate fallback

- **GIVEN** the requested model is known to subscription routing
- **AND** the source catalog lookup succeeds without confirming source ownership
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** the client sends a physically present but blank `x-codex-turn-state`
  header
- **AND** exactly one eligible subscription account remains
- **WHEN** the client calls `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the proxy returns HTTP status `502`
- **AND** the sanitized error code is `previous_response_owner_unavailable`
- **AND** no subscription account is selected and no upstream request is dispatched

#### Scenario: Generated-looking WebSocket turn state requires exact provenance

- **GIVEN** a direct Responses WebSocket handshake generated a synthesized turn-state marker
- **AND** the client supplies a different `x-codex-turn-state` that matches the synthesized-token shape
- **AND** that client token has no owner in the requesting API-key scope
- **AND** exactly one eligible subscription account remains
- **WHEN** the client submits a compact continuation with a missing previous-response owner
- **THEN** the proxy fails closed with `turn_state_owner_unavailable`
- **AND** no subscription account is selected and no upstream request is dispatched
- **BUT WHEN** the turn state exactly matches the marker generated for that handshake
- **OR** server-side continuity state proves that the proxy issued the marker on an earlier handshake
- **THEN** the unregistered first-turn placeholder may use the sole-candidate compatibility fallback

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

#### Scenario: Opaque source response ID falls back to HTTP on direct WebSocket

- **GIVEN** a source is configured for the requested model
- **AND** the source catalog confirms that the requested model is source-owned
- **AND** no subscription account is recorded as owner of `source-turn-opaque-ws`
- **AND** `previous_response_id` is the opaque non-canonical value `source-turn-opaque-ws`
- **WHEN** a direct Responses WebSocket client submits the follow-up
- **THEN** the proxy emits `model_source_requires_http_transport`
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
- **AND** the source catalog lookup succeeds without confirming source ownership
- **AND** no subscription account is recorded as owner of `previous_response_id`
- **AND** the continuation is not already attached to its required open owner socket
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
