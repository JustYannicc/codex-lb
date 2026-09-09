## Purpose

Let Codex Desktop display genuine pooled quota while retaining its original ChatGPT identity and account-owned state.

## ADDED Requirements

### Requirement: Desktop quota requires the original ChatGPT caller

`GET /api/codex/desktop/usage` and its trailing-slash alias MUST require a valid ChatGPT bearer and an imported, eligible `chatgpt-account-id`. The endpoint MUST reject API-key-only callers and capability-restricted requests before pool projection. Existing `/api/codex/usage` and inference behavior MUST remain unchanged.

#### Scenario: Authorized original caller
- **WHEN** an imported eligible caller supplies its valid ChatGPT bearer and account header
- **THEN** the endpoint validates that caller using the existing upstream identity policy and returns the Desktop quota projection

#### Scenario: Invalid or incompatible caller
- **WHEN** the bearer is missing or invalid, the account is unknown or inactive, or only an LB API key is supplied
- **THEN** the endpoint denies access without returning pool data

### Requirement: Pool availability requires fresh evidence

The Desktop projection MUST use the existing capacity-weighted pool calculation and earliest reported reset for each window. It MUST exclude paused, deactivated and reauthentication-required accounts, retain fresh exhausted accounts in capacity totals, and declare availability only if at least one eligible account has capacity in every known applicable window. It MUST require finite percentages, valid window timing and observations within the existing usage freshness horizon. It MUST NOT infer a successful reset from elapsed time alone, invent missing samples, or silently omit uncertain capacity from the aggregate. Missing, stale, elapsed or malformed applicable evidence MUST return HTTP 503 with error code `pooled_usage_unavailable`. The projection MUST refresh through existing usage-refresh ownership rules and MUST NOT execute concurrent statements on one database session.

#### Scenario: Primary exhausted with another pool account available
- **WHEN** fresh pool evidence includes an exhausted primary caller and an eligible account with available quota
- **THEN** the native main quota reports the capacity-weighted percentages with `allowed=true` and `limit_reached=false`

#### Scenario: Entire known pool exhausted
- **WHEN** fresh evidence shows every eligible account has an exhausted applicable window
- **THEN** the projection reports `allowed=false` and `limit_reached=true` without inventing reserve capacity

#### Scenario: Refresh fails after a window expires
- **WHEN** a refresh fails and the remaining evidence is stale, expired, missing or malformed
- **THEN** the endpoint returns `pooled_usage_unavailable` and does not report the elapsed window as zero used

#### Scenario: No eligible accounts
- **WHEN** the pool contains no eligible accounts
- **THEN** the endpoint returns `pooled_usage_unavailable`

#### Scenario: Weekly primary competes with a secondary placeholder
- **WHEN** an account reports weekly quota in its primary slot and a competing secondary row
- **THEN** the projection applies the established weekly-primary tiebreak from the usage refresh policy
- **AND** the selected effective row must pass strict freshness and timing checks
- **AND** a selected no-data placeholder returns `pooled_usage_unavailable` rather than zero used

### Requirement: Account-owned metadata survives quota composition

The Desktop response MUST retain the original upstream caller envelope, including identity, plan, credits, spend controls, billing, reset credits and unknown account fields. It MUST replace only the canonical quota and additional quota for which equivalent fresh pooled evidence exists. Model-specific quota matching MUST match both normalized limit name and metered feature. Additional percentages MUST use equal-plan contributors with equal window durations, or a capacity-independent equal percentage across plans; otherwise the projection MUST return `pooled_usage_unavailable`. Unmatched same-named buckets MUST NOT be duplicated with an available bucket; unmatched original limits and reserve-model metadata MUST remain conservative. If the pooled main quota is available, the response MUST remove a known superseded `rate_limit_reached` marker and quota-only exhausted/reserve banners. It MUST preserve unknown restriction markers and account-owned spending restrictions. The response MUST NOT substitute another account's plan, credits or identity.

#### Scenario: Account plan and balances differ from the pool
- **WHEN** a Plus caller uses a pool that also contains Pro accounts
- **THEN** the response retains the caller's plan, identifiers, credit balance and reset credits while returning pooled quota windows

#### Scenario: Luna reserve is superseded by genuine pool quota
- **WHEN** the original response contains known quota-exhaustion state and the main pool quota is available
- **THEN** the response removes only that superseded quota restriction and retains account-owned restrictions and reserve metadata

#### Scenario: Additional model quota remains exhausted
- **WHEN** fresh equivalent pooled additional quota is exhausted or no equivalent pool evidence exists
- **THEN** the response does not claim that model is available merely because main pooled quota is available

#### Scenario: Main and model capacity are on different accounts
- **WHEN** one account has main quota but its model quota is exhausted and another has model quota but its main quota is exhausted
- **THEN** the model-specific pooled limit reports unavailable

### Requirement: Optional Desktop relay preserves caller traffic

`codex-lb desktop-relay` MUST run separately from the normal server and bind only loopback on port 8000. `GET /backend-api/wham/usage` and its trailing-slash alias MUST route to the configured local LB's strict Desktop quota endpoint. Other `/backend-api/` HTTP and WebSocket requests MUST use the fixed `https://chatgpt.com` destination with the original method, path, query, body, Authorization, account identity, cookies and end-to-end headers. The relay MUST remove hop-by-hop headers, preserve streaming and duplicate response headers, close owned upstream resources on disconnect or cancellation, validate upstream TLS, and neither retry state-changing requests nor follow redirects automatically. It MUST reject nonloopback LB destinations, unexpected request authorities and paths outside the backend prefix. It MUST NOT log credentials, query strings or payloads, store caller cookies between requests, or allow arbitrary upstream destinations.

#### Scenario: Usage routing
- **WHEN** Desktop requests either supported usage path
- **THEN** the relay forwards the original caller headers to the strict LB endpoint and returns its quota or error response

#### Scenario: Original identity passthrough
- **WHEN** Desktop requests a settings or reset-credit endpoint
- **THEN** the relay forwards the request to ChatGPT with the original caller identity and unmodified body, and preserves the response status, cookies and integrity headers

#### Scenario: Configured outbound proxy
- **WHEN** standard outbound proxy environment variables configure ChatGPT HTTP or WebSocket egress
- **THEN** the relay honors the existing HTTP, WebSocket and SOCKS proxy selection policy, including the explicit WebSocket direct-connect override
- **AND** local LB usage requests remain direct loopback traffic

#### Scenario: Unsafe destination or request
- **WHEN** a nonloopback LB URL, unexpected Host, or path outside `/backend-api/` is supplied
- **THEN** the relay rejects it without forwarding credentials

#### Scenario: Failure and cancellation
- **WHEN** an upstream times out, a stream fails, or the downstream disconnects
- **THEN** the relay reports failure without fabricating quota and releases its owned connection and tasks

### Requirement: Desktop activation remains explicit and reversible

The documented setup MUST retain ChatGPT login, `requires_openai_auth=true`, and existing inference routing. It MUST configure the Desktop launch environment with `CODEX_API_BASE_URL=http://localhost:8000/backend-api` and leave Rust account-base controls unchanged. Setup MUST NOT modify the installed app, bypass auth or TLS checks, or silently change the user's live launch environment. Documentation MUST state tested versions, broad-routing compatibility limits, start/restart order, persistence, recovery and rollback. Real-app success MUST be recorded separately from synthetic tests and MUST include the original displayed identity, genuine pooled usage observed through the candidate route, and a completed request using the intended model through LB.

#### Scenario: Revert optional routing
- **WHEN** the user restores the previous Desktop launch environment and fully restarts Desktop
- **THEN** backend requests resume the original destination and the separate relay can be stopped without changing ChatGPT login or inference configuration

#### Scenario: Synthetic proof only
- **WHEN** deterministic tests pass but the real Desktop trial has not completed
- **THEN** documentation and delivery status identify the real-app acceptance as pending
