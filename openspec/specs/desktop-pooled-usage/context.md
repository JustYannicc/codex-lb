# Desktop pooled usage context

[Contract](spec.md). [Setup and rollback](../../../docs/desktop-pooled-usage.md).

## Purpose

The intended outcome is to keep the original ChatGPT account and connected capabilities while inference uses codex-lb's imported account pool. Desktop's own usage poll follows a different base URL from inference. The optional relay joins those paths for usage and forwards the caller's credentials on other backend requests. The real trial below did not establish preservation of the full Desktop account behavior.

## Routing decisions

The separate `desktop-relay` command binds loopback port 8000, matching the unchanged auth allowlist observed in Desktop `26.903.61454`. `CODEX_API_BASE_URL` changes Electron-owned backend routing. The inference provider base and Rust account base remain independent. Changing the Rust account base can alter hosted MCP authentication before a request reaches any relay.

The relay uses the existing aiohttp dependency, fixed ChatGPT origin, verified TLS and a loopback LB origin. It retains no shared cookies, follows no redirects and logs no payloads or credentials. It forwards HTTP and WebSocket traffic with explicit connection ownership. The normal LB listener and setup defaults are unchanged.

The separate strict endpoint avoids changing the older `/api/codex/usage` contract. The upstream usage parser retains a private original JSON envelope without changing its existing serialized model. Quota composition uses that envelope to retain unknown account-owned fields instead of reconstructing them from a lossy parser.

## Quota meaning

Main window percentages reuse LB's existing plan-capacity weights. A Plus account at 100% weekly usage and a Pro account at 20% produce 30% used after truncation, using capacities 7,560 and 50,400. Those weights are LB estimates, not a measured token or currency entitlement.

Additional limits use the arithmetic mean for equal-plan contributors with equal window durations. Across different plans, only an equal percentage on every contributor is independent of unknown capacity weights. Other mixed-plan results and differing durations are unavailable. There is no model-specific capacity table from which to derive different weights. A model is available only when the same eligible account has both main and model quota. The original caller's reserve bucket remains account-owned.

Freshness uses the shared horizon, currently 180 seconds. The projection refreshes without holding its initial database session, then reads sequentially. It does not infer resets from elapsed time or quietly discard missing accounts. Weekly primary/secondary selection reuses the [existing tiebreak](../usage-refresh-policy/spec.md), followed by strict validation of the selected effective row. Thus a real weekly-primary sample can beat a no-data secondary placeholder without treating the placeholder as unused quota.

## Limits and recovery

Some historical missing-window cases remain conservatively unavailable. Original account credits, billing and spending restrictions can still block Desktop despite available main pool quota. Unknown restriction markers remain intact. The native UI has no per-account breakdown.

The Desktop override also affects signed remote-control challenges, cookie registration and some dictation routing. Exact-message passthrough does not establish that client-side origin or cookie-domain checks will accept the result. No signed challenges, application files or auth guards are rewritten. The corrected candidate removes an explicit chatgpt.com Domain attribute from non-usage Set-Cookie fields so they remain usable through localhost; cookie values and other attributes remain unchanged.

Real acceptance is separate from synthetic proof. Record the retained displayed identity, a genuine native pooled-usage observation and an actual request with the intended model. Until that trial completes, this is a locally tested candidate. Rollback restores the prior Desktop environment and restarts the app; the separate relay can then be stopped.

## Observed Desktop trial

The 2026-09-09 trial used candidate `1aa75e14f2cdcc6f5223a64b68c573f7b207a630` against base `c0beaaadd96a89f0240582b5449bf4dd50647c7d`, Desktop `26.903.61454` and bundled CLI `0.153.4`. A private candidate database and separate relay left the existing inference service intact. Initial temporary jobs stopped when Desktop quit, causing connection-refused failures. Explicit GUI-domain LaunchAgents restored the listeners and survived the later app restart.

A genuine Desktop request to the strict pooled endpoint returned 200. The user confirmed that the name and usage control returned, but account settings still failed with `DeviceCheck registration failed (403)`, and several account routes received upstream HTML challenges. Restoring the original Desktop launch environment restored the user's purple accent and normal behavior. The trial services and copied credentials were then removed. These observations disprove treating byte-preserving HTTP forwarding as sufficient account-feature acceptance; they do not identify every cause of the upstream challenges.

The exact displayed pooled percentage and a successful intended-model request were not verified. The zero remaining and Luna-only restriction reported after rollback were from the original exhausted account, not an observed zero-valued pooled response.

Installed-source inspection separates three paths: inference follows the model provider URL, Rust account quota follows `chatgpt_base_url`, and Desktop's native quota and reserve restriction follow its direct `/wham/usage` query. The inspected reserve gate requires a matching identity and plan, a `luna_reserve` banner, main `allowed=false`, and an allowed `gpt-reserve` bucket. The existing composition targets that gate when pool evidence establishes main availability. A visible usage control alone does not prove the picker used the intended quota or that an intended-model request succeeded.

No narrow Desktop quota URL override was found. DeviceCheck registration and its cookie lookup also use the broad Desktop base, so redirecting non-usage calls to the official origin is not an established fix. A future trial must first establish normal account/settings behavior and then compare the actual quota and model selection. No application patch, trust change, signed-challenge rewrite or authentication bypass is part of this candidate.

The next candidate corrects the proven cookie-domain mismatch. Both a Chromium cookie-store check and the exact installed CookieManager running in an isolated Electron 42.3.0 process reject the original foreign-domain cookie and accept the host-only cookie while retaining Secure and HttpOnly. This synthetic evidence does not establish that real DeviceCheck registration will accept the forwarded request; the next authorized trial records status and cookie-presence metadata separately from quota and model acceptance.
