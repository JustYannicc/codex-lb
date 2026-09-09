# Desktop pooled usage context

[Contract](spec.md). [Setup and rollback](../../../docs/desktop-pooled-usage.md).

## Purpose

Users can keep their original ChatGPT account and connected capabilities while inference uses codex-lb's imported account pool. Desktop's own usage poll follows a different base URL from inference. The optional relay joins those paths only for usage and preserves the caller on other backend requests.

## Routing decisions

The separate `desktop-relay` command binds loopback port 8000, matching the unchanged auth allowlist observed in Desktop `26.903.61454`. `CODEX_API_BASE_URL` changes Electron-owned backend routing. The inference provider base and Rust account base remain independent. Changing the Rust account base can alter hosted MCP authentication before a request reaches any relay.

The relay uses the existing aiohttp dependency, fixed ChatGPT origin, verified TLS and a loopback LB origin. It retains no shared cookies, follows no redirects and logs no payloads or credentials. It forwards HTTP and WebSocket traffic with explicit connection ownership. The normal LB listener and setup defaults are unchanged.

The separate strict endpoint avoids changing the older `/api/codex/usage` contract. The upstream usage parser retains a private original JSON envelope without changing its existing serialized model. Quota composition uses that envelope to retain unknown account-owned fields instead of reconstructing them from a lossy parser.

## Quota meaning

Main window percentages reuse LB's existing plan-capacity weights. A Plus account at 100% weekly usage and a Pro account at 20% produce 30% used after truncation, using capacities 7,560 and 50,400. Those weights are LB estimates, not a measured token or currency entitlement.

Additional limits use the existing arithmetic mean of observed contributors. There is no model-specific capacity table from which to derive different weights. A model is available only when the same eligible account has both main and model quota. The original caller's reserve bucket remains account-owned.

Freshness uses the shared horizon, currently 180 seconds. The projection refreshes without holding its initial database session, then reads sequentially. It does not infer resets from elapsed time or quietly discard missing accounts. Weekly primary/secondary selection reuses the [existing tiebreak](../usage-refresh-policy/spec.md), followed by strict validation of the selected effective row. Thus a real weekly-primary sample can beat a no-data secondary placeholder without treating the placeholder as unused quota.

## Limits and recovery

Some historical missing-window cases remain conservatively unavailable. Original account credits, billing and spending restrictions can still block Desktop despite available main pool quota. Unknown restriction markers remain intact. The native UI has no per-account breakdown.

The Desktop override also affects signed remote-control challenges, cookie registration and some dictation routing. Exact-message passthrough does not establish that client-side origin or cookie-domain checks will accept the result. No signed challenges, cookie domains, application files or auth guards are rewritten.

Real acceptance is separate from synthetic proof. Record the retained displayed identity, a genuine native pooled-usage observation and an actual request with the intended model. Until that trial completes, this is a locally tested candidate. Rollback restores the prior Desktop environment and restarts the app; the separate relay can then be stopped.
