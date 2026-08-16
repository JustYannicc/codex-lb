## ADDED Requirements

### Requirement: Compact requests recover from quota-caused previous-response owner loss

When a compact request is pinned to a previous-response owner account, that pin is the only
continuity pin (no client-supplied turn-state owner and no input-file owner), and account
selection cannot return the pinned owner, the proxy MUST attempt account-neutral fresh-replay
recovery before surfacing the failure, provided every activation gate below holds. Outside the
gates the proxy MUST keep today's fail-closed failure for that request, MUST NOT send any part
of the payload to another account, and MUST record the fail-closed outcome on the continuity
fail-closed observability counter for the compact surface.

Recovery MUST activate only for quota-caused owner loss. At selection time, before the owner
was ever used for the request, the owner's persisted account status MUST be rate-limited or
quota-exhausted; an owner unselectable for any other reason (re-authentication required,
deactivated, paused, local capacity caps on an active account, or a failed status lookup)
stays owner-bound. Mid-request, only a pre-visible quota or rate-limit failure of the pinned
owner that permits failover makes recovery eligible; post-selection authentication, refresh,
transport, timeout, and transient exclusions of the pinned owner keep their existing
owner-bound handling.

Recovery MUST NOT activate when the request carries a session identity (a turn-state or
session header) that can bind live or durable HTTP-bridge continuity, or when the resolved
affinity is session ownership (a Codex-session affinity key, a raw legacy session row, or a
conversation handle requiring an unambiguous owner): this recovery deliberately carries no
continuity-rebind machinery, so anything that would need rebinding stays owner-bound.
Prompt-cache and sticky-thread locality keys are advisory cache locality that ordinary sticky
selection already falls back from and do not block recovery.

Local verification MUST run against the exact upstream-bound compact payload without
`previous_response_id`, after every wire transformation the compact serializer applies. It
MUST require that serialized `input` to be a list of more than one item that is item-for-item
identical to the validated request `input`, so that no request whose wire history is dropped
or trimmed — including single-item collapse and oversized-input trim markers — is ever
replayed on another account, which could not resolve the omitted owner-resident context. It
MUST validate that same serialized payload against the shared account-neutral fresh-replay
rules: self-contained tool call/output pairing, no server-assigned item ids, no encrypted or
compaction state, no nonblank conversation or prompt handles, no account-scoped
file/container/vector handles, no hosted/MCP call state, and only recognized account-neutral
fields and shapes. Because a self-contained payload may still be a delta that relies on the
owner to hold the earlier conversation, the serialized `input` MUST additionally parse as a
transcript whose final segment retains completed assistant output followed only by fresh
client input, using the shared retained-prior-output rule anchored at the last assistant
message. Histories those gates cannot prove — including delta-shaped inputs without retained
assistant output and transcripts without fresh follow-up input — stay owner-bound.

For an eligible recovery, the proxy MUST remove `previous_response_id` from the upstream
compact payload, strip downstream session/turn affinity aliases from the upstream-bound
headers, exclude the unavailable owner account from the remaining attempts, and reselect among
the remaining eligible accounts with fallback enabled.

#### Scenario: Quota-excluded owner at selection time fails over with a verified full resend

- **GIVEN** account A owns the previous response referenced by a compact request and account B is eligible
- **AND** account A's persisted status is rate-limited or quota-exhausted
- **AND** the compact payload carries an account-neutral full-resend `input` that retains prior assistant output ahead of the new client input
- **AND** the request carries no session identity and no session-ownership affinity
- **WHEN** pinned account selection cannot return account A
- **THEN** the proxy sends the compact upstream exactly once on account B without `previous_response_id`
- **AND** the compact response is returned successfully

#### Scenario: Owner exhausts quota during the compact request

- **GIVEN** the pinned previous-response owner is selected for a compact request
- **AND** the upstream compact fails with a pre-visible quota or rate-limit error that permits failover
- **WHEN** reselection cannot return the now-excluded owner
- **THEN** the proxy applies the same account-neutral fresh-replay recovery on another eligible account
- **AND** the owner's quota failure is not surfaced to the client when the recovery succeeds

#### Scenario: Post-selection authentication failure on the pinned owner stays owner-bound

- **GIVEN** the pinned previous-response owner is selected for a compact request with an account-neutral full-resend `input`
- **AND** the upstream compact fails with `401` again after the forced token refresh, which excludes the owner from the remaining attempts
- **WHEN** reselection cannot return the now-excluded owner
- **THEN** the proxy surfaces the owner's authentication failure
- **AND** account-neutral fresh-replay recovery does not activate and no part of the payload is sent to another account

#### Scenario: Non-quota owner loss at selection time stays owner-bound

- **GIVEN** a previous-response-pinned compact request whose owner account is paused, deactivated, or requires re-authentication
- **WHEN** pinned account selection cannot return the owner
- **THEN** the request fails with the existing selection error
- **AND** account-neutral fresh-replay recovery does not activate
- **AND** the continuity fail-closed counter records the compact-surface outcome

#### Scenario: Non-neutral compact payload stays fail-closed

- **GIVEN** a pinned compact request whose `input` retains encrypted compaction state, server-assigned item ids, or account-scoped file handles
- **WHEN** the quota-excluded pinned owner cannot be selected
- **THEN** the request fails with the existing selection or upstream error
- **AND** no part of the payload is sent to another account
- **AND** the continuity fail-closed counter records the compact-surface outcome

#### Scenario: Delta-shaped history without retained output stays fail-closed

- **GIVEN** a pinned compact request whose multi-item `input` carries no retained assistant output ahead of fresh client input
- **WHEN** the quota-excluded pinned owner cannot be selected
- **THEN** the request fails with the existing selection or upstream error
- **AND** the proxy keeps the anchor and sends no part of the payload to another account

#### Scenario: History the wire serializer shortens stays fail-closed

- **GIVEN** a pinned compact request whose `input` loses history when serialized for upstream, either collapsing to a single item or being trimmed to a head, trim marker, and tail
- **WHEN** the quota-excluded pinned owner cannot be selected
- **THEN** the request fails with the existing selection or upstream error
- **AND** the proxy does not replay the shortened history on another account

#### Scenario: Session-identified compact stays owner-bound

- **GIVEN** a pinned compact request that carries a session or turn-state identity able to bind live or durable HTTP-bridge continuity
- **WHEN** the quota-excluded pinned owner cannot be selected
- **THEN** the request fails with the existing selection error
- **AND** account-neutral fresh-replay recovery does not activate

#### Scenario: Turn-state-pinned and file-pinned compacts remain owner-bound

- **GIVEN** a compact request pinned by a client-supplied turn-state owner or an input-file owner
- **WHEN** that owner account cannot be selected
- **THEN** the request fails closed with the existing continuity or selection error
- **AND** account-neutral fresh-replay recovery does not activate

#### Scenario: Unresolvable previous-response owner remains fail-closed

- **GIVEN** a compact request whose `previous_response_id` owner cannot be resolved from any record
- **AND** more than one account is eligible
- **WHEN** the request is evaluated before account selection
- **THEN** the request fails with `previous_response_owner_unavailable`
- **AND** the proxy does not treat the missing owner as a selector result or replay on another account
