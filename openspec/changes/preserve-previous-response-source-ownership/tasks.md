## 1. Contract

- [x] 1.1 Sync the owner-evidence routing requirement into the main Responses compatibility spec.

## 2. Routing Implementation

- [x] 2.1 Remove response-ID-shape inference from the shared structural source-route exclusion policy.
- [x] 2.2 Make both HTTP Responses routes let recorded subscription ownership veto an otherwise valid model-source candidate.
- [x] 2.3 Apply the same owner-aware decision before direct WebSocket connect and reuse source guards.
- [x] 2.4 Resolve recorded subscription ownership before disabled-source denial, even when enabled-source lookup misses.
- [x] 2.5 Treat physically present blank direct-WebSocket turn-state headers as client input and fail closed on owner miss.
- [x] 2.6 Use TypedDicts for the authenticated forwarding-signature payload shape.
- [x] 2.7 Require API-key-scoped synthesized-marker provenance or an independent hard owner before compact owner-miss fallback.
- [x] 2.8 Apply the synthesized-marker provenance guard to compact requests without `previous_response_id`.

## 3. Regression Coverage

- [x] 3.1 Update unit coverage for structural source-route exclusions without response-ID syntax classification.
- [x] 3.2 Cover subscription-owned and canonical source-owned prior responses on both HTTP Responses routes.
- [x] 3.3 Add direct WebSocket regressions for subscription-owner routing and canonical source-owner HTTP fallback.
- [x] 3.4 Cover unregistered synthetic-shaped compact turn state with a missing previous-response owner.
- [x] 3.5 Cover unregistered synthetic-shaped compact turn state without `previous_response_id`.

## 4. Verification

- [x] 4.1 Run focused tests, Ruff, ty, and scoped/strict OpenSpec validation; inspect the final diff and worktree status.
- [x] 4.2 Preserve turn-state ownership before owner-miss fallback and fail closed when WebSocket candidate lookup is unavailable.
- [x] 4.3 Validate the no-previous-response compact provenance boundary and strict OpenSpec contract.
