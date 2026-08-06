# responses-api-compat Delta

## ADDED Requirements

### Requirement: Silent HTTP bridge sessions are quarantined from re-attach and reuse

When an HTTP bridge session proves silent/wedged, the proxy MUST quarantine its session key for a bounded window so later requests stop attaching to it. A session proves silent/wedged when either (a) a pending request being failed or retired carried a proxy-injected `previous_response_id`, had sent `response.create`, observed upstream response events, and never had `response.created` assigned, or (b) the session key hits two consecutive eventless `missing_response_created_timeout` retires. The quarantine MUST be evaluated only when a request is already being failed or its session retired — never against a live owned turn — so a stream whose `response.created` was observed (including deferred-reasoning streams with long event gaps) MUST NOT be quarantined, and mere event silence during an owned live turn MUST NOT trigger quarantine by itself.

While a session key is quarantined: an existing session under that key MUST NOT be selected for reuse (a new request detaches it and proceeds on a fresh session), and a fresh reattach whose incoming payload already looks like a full conversation resend MUST NOT receive a proxy-injected durable anchor — it proceeds on the existing unanchored fresh path. A payload that does not look like a full resend (a genuine delta-only continuation) MUST still receive the durable anchor, because it has no other way to convey prior conversation state.

Quarantine state MUST be bounded and self-recovering: it is in-memory and session-scoped, expires by TTL, is cleared when a response completes on the same session key, and MUST NOT write account health or alter account selection.

#### Scenario: Reattach streams events but response.created is never assigned (#1534)

- **GIVEN** a durable HTTP bridge session with a stored anchor whose fresh reattach injected a proxy-owned `previous_response_id`
- **AND** the reattached upstream stream delivers response events but `response.created` is never assigned
- **WHEN** the stream fails or the session is retired with that request still pending
- **THEN** the request fails terminally as before
- **AND** the session key is quarantined with reason `reattach_missing_response_created`

#### Scenario: Next request after the wedge completes on the fresh path

- **GIVEN** a session key quarantined after a reattach that streamed events without `response.created`
- **WHEN** a later request arrives for the same key with a full-conversation-resend payload and no client `previous_response_id`
- **THEN** the proxy does not inject the durable anchor for that request
- **AND** the request is sent upstream unanchored with the client's own full payload
- **AND** the request can complete normally instead of rebuilding the identical wedged reattach

#### Scenario: Quarantined session is excluded from reuse selection

- **GIVEN** a session marked quarantined that is still live or retained for admission handoff
- **WHEN** a new request looks up that session key
- **THEN** the session is not considered reusable
- **AND** the request proceeds on a fresh session instead

#### Scenario: Repeated eventless timeouts quarantine the key

- **GIVEN** a session key whose pending request already retired once with the eventless `missing_response_created_timeout`
- **WHEN** a subsequent attach on the same key retires with the same eventless timeout before any response completes on the key
- **THEN** the session key is quarantined with reason `repeated_eventless_timeout`
- **AND** the first timeout alone does not quarantine the key

#### Scenario: Deferred-reasoning live turn is never quarantined

- **GIVEN** an owned live turn whose `response.created` was observed and whose events flow with long gaps (deferred reasoning)
- **WHEN** its stream later fails or its session is retired
- **THEN** the session key is not quarantined
- **AND** later requests keep the existing reuse and anchor-injection behavior

#### Scenario: Delta-only payloads keep their anchor while quarantined

- **GIVEN** a quarantined session key
- **WHEN** a later request arrives whose payload does not look like a full conversation resend
- **THEN** the durable anchor is still injected for that request, preserving the client's only way to convey prior context

#### Scenario: Quarantine is bounded and self-clearing

- **GIVEN** a quarantined session key
- **WHEN** a response completes on that session key, or the quarantine TTL elapses
- **THEN** the quarantine (and its eventless strike counter) is cleared
- **AND** no durable row, janitor work, or account-health write was involved at any point
