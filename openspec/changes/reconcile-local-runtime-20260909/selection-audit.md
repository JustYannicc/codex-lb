# Frozen source selection evidence

The source manifest overrides these initial triage reports where later repairs or upstream merges changed the decision. In particular, #2265 entered upstream main; #2070 and #2088 use repaired sources; #1954 preserves historical deployed migration ancestry. This is source selection evidence, not deployment acceptance.

# New runtime fixes: source selection audit

Pinned upstream `efe0f581a18a36f4d491b92a36ef79b0c432d252`, verified against live `git ls-remote upstream refs/heads/main` during this audit. Exact current-head GitHub API evidence and real diffs are preserved in `new-fixes-evidence/<PR>.json` and `.diff`. No application imports, tests, Docker, repository changes or public comments were performed. This selects inputs for integration; it does not certify the composed image or upstream merge gates. No candidate in this set is an entire already-upstream duplicate.

Preserve accepted pooled #2286 `3f8af6be0c09db264f6994dc29895a2a89442b48`, existing selected external/authored concerns, and existing ownership-policy holds. A missing upstream PR CI run is missing evidence, not a reason to abandon a useful fix forever. The integration owner can repair bounded defects and prove the resulting local candidate without waiting for public PR changes.

## Exact decisions

| PR / immutable head | Classification | Independent benefit and current-base evidence | Required work / overlap |
|---|---|---|---|
| [#2260](https://github.com/Soju06/codex-lb/pull/2260) `8244933c0c1d8d45aaceb0564776c2c603a9d3f1` | include independently | Sanitizes fixed and Connection-nominated hop headers before native identity detection. Prevents rebuilt chunked compact requests carrying invalid upstream framing; regenerates LB credentials/JSON negotiation. Main proxy.py:943 still detects native from unfiltered input and lacks Connection-token sanitation. | CodeRabbit/security/label success only, no hosted runtime-suite proof. Diff includes real compact route regression and header tests plus OpenSpec. Compose shared header path with #1905/#2093/#2102; these selected diffs do not implement Connection-token sanitation. |
| [#2255](https://github.com/Soju06/codex-lb/pull/2255) `80a3c737521c0312ae98d4e09e8b58a0adf0d093` | include independently | Makes new WebSocket admission during drain return retryable HTTP 503 + Retry-After instead of pre-handshake close surfaced as 403. Main inflight.py:63 still sends websocket.close. Relevant to actual runtime restarts. | CodeRabbit/security/label success only. Existing route-drain and admission tests updated. No OpenSpec change despite observable wire contract change: add explicit drain HTTP denial requirement to integration change. Preserve #2283 shutdown test completion-order fix; these changes are complementary. |
| [#2248](https://github.com/Soju06/codex-lb/pull/2248) `1cf22a8790e036382714edd63edbef50cbac6dee` | include independently | Retires a proxy-injected WebSocket continuity anchor already denied upstream, including prefix/tool metadata, using existing API-key-scoped stale cache. Main websocket/helpers.py:699 does not consult it. Prevents retry loops while sending original full client input. | CodeRabbit/security/label success only. Preparation-level regression present, external WebSocket deny-then-retry regression still needed. Add OpenSpec delta for changed continuation contract. Explicit client anchors remain untouched. Compose #1952/#2102 helper/mixin edits and #2277 input preservation; no duplicate stale-cache retirement in inspected selected diffs. |
| [#2193](https://github.com/Soju06/codex-lb/pull/2193) `cae31f0a928200b637425e72941b6a9110731948` | include independently | Skips Connection.info reads on invalidated/closed SQLite connections in watchdog callbacks, allowing rollback before reconnect. Main session.py:252 and ending callbacks read info directly. Useful on cancellation/shutdown with SQLite. | No active review blockers; successful concrete runtime suites and CI Required in snapshot. Regression invalidates a real disposable SQLite connection then rolls back/reuses it. Preserve unrelated deployed teardown repairs. README/contributor metadata is incidental, not required runtime behavior. |
| [#2119](https://github.com/Soju06/codex-lb/pull/2119) `c5fe2d5792f4f3038269d90f20cb110066a2411a` | include independently | Requires spendable positive balance or unlimited credits before treating purchased credits as capacity; a bare credits_has flag must not clear quota exhaustion. Main quota.py and account mapper still accept the bare flag. | Current-head CI Required green, no active inline blockers. Preserve foreground advisory long-window behavior. Compose #2048 quota recovery and #2070 usage refresh plus accepted #2286 pooled capacity. Verify exhausted, zero, absent, positive and unlimited credits in aggregate. |
| [#2110](https://github.com/Soju06/codex-lb/pull/2110) `880861fcf2dd555636111cdcfd5efe6b81fc8ad6` | include independently | Caches system-trust SSLContext for direct Python WSS instead of rebuilding the trust store for each connection. Startup creates and shutdown clears it. Main has no cache. | Current-head reported checks success/skipped, no active inline blockers. Python WSS only; native egress is unchanged. Complements #2075 receive/close provenance. Trust store/environment changes apply on close/reinit; preserve certifi handling on the separate aiohttp path. |
| [#2234](https://github.com/Soju06/codex-lb/pull/2234) `c01c2be95003f4d079d3e3323e7f91e330df3f53` | blocked-review, routine local doc repair can unblock | Preserves a soft TTL prompt-cache owner when only this request excludes/caps it, while serving an alternate request. Main sticky_selection.py:578 preservation is limited to bare sessions. Includes actual HTTP retry tests and cap/status/scope cases. | Current-head runtime CI green. One active CodeRabbit thread correctly flags design.md fixed 1800-second TTL wording although TTL is configurable. Fix to configured affinity TTL; this is documentation, not an unresolved product policy. Candidate is useful and should enter local repair queue, not permanent exclusion. Preserve security-work rebinding, paused/deactivated/out-of-scope rebinding and hard-owner fences. |
| [#2133](https://github.com/Soju06/codex-lb/pull/2133) `e7eeb855c931773a10dc74976ce10e1c08d0bb85` | blocked-review | Separates heartbeat scheduling/pool from maintenance so slow work does not make healthy replicas look dead. Missing upstream. | Green CI does not resolve live findings: fixed 2s cleanup + 3s stale marking ignore lifespan absolute shutdown deadline; bridge-disabled readiness contract remains vague; real lifespan/DB heartbeat regression under blocked maintenance absent. See child report. Lifecycle contract requires repair before inclusion. |
| [#2132](https://github.com/Soju06/codex-lb/pull/2132) `47e255b052a08aa1aa3bd268363f8986998c34d4` | blocked-review, independent local concern | Adds recovery from rejected authentication using credential CAS, reason-aware routing, safe replay projection and rotation repair. Missing upstream. | Green CI/no active GitHub threads, but _recover_rejected_auth defers account_auth_invalidated health until keyed replacement settlement and excludes only request-local ID; immediate shared routing exclusion is not established. Prove/fix concurrent selection exclusion while preserving reservation-before-health ordering. Consolidate with #2117; their reason predicates differ. |
| [#2117](https://github.com/Soju06/codex-lb/pull/2117) `1dad6743801263fd351c247cc848e8bdef800752` | blocked-review / missing aggregate verification | Adds token_revoked/token_invalidated retirement, immediate token_revoked routing mark, correct no-replacement auth envelope, and AuthManager routing publication. Missing upstream. | Three active threads have fixed replies and visible corresponding fixes. Only label/CodeRabbit/security runs in current-head snapshot, no runtime suites. Missing CI alone is not a product defect: local composed verification can qualify it. Compose with #2132 and #2120 rather than importing overlapping auth policies unchanged. |
| [#2131](https://github.com/Soju06/codex-lb/pull/2131) `ad3674b0a2551da3f3581863f4ca4cc76575346c` | blocked-review / failing checks | Treats narrowly identified misalignment_policy_violation request rejections as health-neutral while preserving the client failure. No safety bypass and absent upstream. | Exact-head Ruff/unit/CI Required fail. Status-propagation review fix is visible, so do not repeat it as still broken. Diagnose failures and verify neutral health plus preserved error before local inclusion. |
| [#2121](https://github.com/Soju06/codex-lb/pull/2121) `f5e044d8c186428ae0816247e5b0f06e56e7441a` | blocked-review | Permits fresh user follow-up after an exactly completed durable tool manifest, allowing existing safe full-resend recovery from unavailable owner. Main helper still rejects the trailing user suffix. | Active current-head review flags suffix shape checks omitting strict item neutrality/unknown-field validation. Diff really removes trailing input before local self-contained proof, but callers also classify complete projected payload, so review concern is not proven exploit. Need explicit malformed-ID/metadata/unknown-field regression and disposition. Exact-head CI Required fails, one runtime aggregate failure accompanies cancelled jobs. Preserve #2086/#1952/#2102 tool/history restrictions. |
| [#2120](https://github.com/Soju06/codex-lb/pull/2120) `e4718ddefcce93197ecfb67ae8c9f6c72dac0d32` | blocked-review / failing gate | Lets ordinary preflight keep explicitly unexpired access token after refresh-credential-only failure; forced/rejected-access path remains excluded. Absent upstream. | Runtime slices green but CI Required failure and contributor check cancellation, plus active ordinary-vs-forced normative wording mismatch. Routine spec/gate repair could unblock; do not conflate this with runtime test failure. Consolidate reason fences with #2132/#2117. |
| [#2111](https://github.com/Soju06/codex-lb/pull/2111) `84cce0395f18941ce9272a8cea3e984a61752385` | blocked-review / failing checks | Publishes real queued/in-progress/created response owners before downstream delivery, closing immediate continuation race while detached request log is pending. Upstream lacks publisher. | Exact-head lint/unit/CI Required fail despite historical body claims. No active nonoutdated inline threads. SSE provenance/parser touches HTTP and WebSocket; synthetic IDs must remain excluded. Incidental exhausted-recovery artifacts require current-base scope review. Repair failures before inclusion. |
| [#2001](https://github.com/Soju06/codex-lb/pull/2001) `e2bed8be5140564501f5b5233af2af738fd4ea46` | blocked-review / failing checks | Avoids creating transient payload owners for previsible HTTP 429 or first-event retryable quota/rate-limit rejection; main retry.py still registers them. Keeps existing hard owners and already-visible output pinned. | Current-head failed/cancelled CI, no active inline blockers. Narrow candidate preferable to broad #2069 owner-moving overlap once fixed/proven. Do not combine both unchanged; #2069 remains held. Product-path compacted-input regressions exist. |
| [#1900](https://github.com/Soju06/codex-lb/pull/1900) `acea4c9af872aa319d8466ec05dbba7fa430ef90` | out of scope as a whole / unresolved recovery policy | Novel transcript materialization is real, but entire branch adds durable transcript/snapshot/alias/rebind migrations, lifecycle fencing and ten settings with optional unsafe recovery semantics. | CONFLICTING and CI/CodeRabbit incomplete at snapshot. Defaults-off gives no immediate recovery benefit; enabling partial/new-response modes changes duplicate-work semantics. Strong overlap with selected #1903/#1905/#2083/#2084/#2086/#2088/#1952/#2102. Do not include bundle or enable policy. No constituent approved; extract/review persistence/materialization separately if required. |

## Evidence details

- #2260: base `bb7b33a9294d3b73a33dd4c2067286a01235e4cc`, exact head `8244933c0c1d8d45aaceb0564776c2c603a9d3f1`, mergeability `MERGEABLE`, checks {'SUCCESS': 3}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2255: base `0da41b64e802331faae01077c89e8c8580b4bce0`, exact head `80a3c737521c0312ae98d4e09e8b58a0adf0d093`, mergeability `MERGEABLE`, checks {'SUCCESS': 3}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2248: base `f3f306fa88815756157e373bf745773f62314d78`, exact head `1cf22a8790e036382714edd63edbef50cbac6dee`, mergeability `MERGEABLE`, checks {'SUCCESS': 3}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2193: base `e987c56c85a3dc516e6a543ff13a9513ca41aafb`, exact head `cae31f0a928200b637425e72941b6a9110731948`, mergeability `MERGEABLE`, checks {'CANCELLED': 1, 'SUCCESS': 26, 'SKIPPED': 8}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2119: base `d3f63331d6ba5e233001fb38c9a059e5a9b681cb`, exact head `c5fe2d5792f4f3038269d90f20cb110066a2411a`, mergeability `UNKNOWN`, checks {'SUCCESS': 26, 'SKIPPED': 8}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2110: base `bb7b33a9294d3b73a33dd4c2067286a01235e4cc`, exact head `880861fcf2dd555636111cdcfd5efe6b81fc8ad6`, mergeability `UNKNOWN`, checks {'SUCCESS': 26, 'SKIPPED': 7}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2234: base `bb7b33a9294d3b73a33dd4c2067286a01235e4cc`, exact head `c01c2be95003f4d079d3e3323e7f91e330df3f53`, mergeability `MERGEABLE`, checks {'SUCCESS': 31, 'SKIPPED': 8}; 1 active nonoutdated inline threads. Review pagination hasNextPage=False.
  - [openspec/changes/preserve-soft-sticky-owner-on-request-local-unavailability/design.md:3](https://github.com/Soju06/codex-lb/pull/2234#discussion_r3968806663)
- #2133: base `c085177110b4b80d5aba7cdef50093efd5565b4f`, exact head `e7eeb855c931773a10dc74976ce10e1c08d0bb85`, mergeability `UNKNOWN`, checks {'CANCELLED': 38, 'SUCCESS': 31, 'SKIPPED': 16, 'FAILURE': 4}; 3 active nonoutdated inline threads. Review pagination hasNextPage=False.
  - [app/main.py:290](https://github.com/Soju06/codex-lb/pull/2133#discussion_r3957957818)
  - [openspec/changes/isolate-ring-heartbeat-from-maintenance/specs/bridge-ring-membership/spec.md:48](https://github.com/Soju06/codex-lb/pull/2133#discussion_r3957957823)
  - [tests/unit/test_ring_lifecycle.py:64](https://github.com/Soju06/codex-lb/pull/2133#discussion_r3962513284)
- #2132: base `3e78b0b646eca38e277a89d706f7dc9f1e94a5aa`, exact head `47e255b052a08aa1aa3bd268363f8986998c34d4`, mergeability `UNKNOWN`, checks {'SUCCESS': 25, 'SKIPPED': 8}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2117: base `35ccf8e9369b10e5819229ac674a3e1c5f6569ae`, exact head `1dad6743801263fd351c247cc848e8bdef800752`, mergeability `UNKNOWN`, checks {'SUCCESS': 3}; 3 active nonoutdated inline threads. Review pagination hasNextPage=False.
  - [app/modules/proxy/_service/streaming/retry.py:2754](https://github.com/Soju06/codex-lb/pull/2117#discussion_r3962429160)
  - [app/modules/proxy/_service/streaming/retry.py:2764](https://github.com/Soju06/codex-lb/pull/2117#discussion_r3962429168)
  - [app/core/balancer/logic.py:63](https://github.com/Soju06/codex-lb/pull/2117#discussion_r3962429176)
- #2131: base `35ccf8e9369b10e5819229ac674a3e1c5f6569ae`, exact head `ad3674b0a2551da3f3581863f4ca4cc76575346c`, mergeability `UNKNOWN`, checks {'SUCCESS': 22, 'SKIPPED': 8, 'FAILURE': 3}; 1 active nonoutdated inline threads. Review pagination hasNextPage=False.
  - [app/modules/proxy/_service/streaming/helpers.py:1018](https://github.com/Soju06/codex-lb/pull/2131#discussion_r3962413018)
- #2121: base `5ad638b6a4c9c094bcc8866b1d7487173fe3b54e`, exact head `f5e044d8c186428ae0816247e5b0f06e56e7441a`, mergeability `UNKNOWN`, checks {'CANCELLED': 23, 'SUCCESS': 23, 'FAILURE': 4, 'SKIPPED': 8}; 1 active nonoutdated inline threads. Review pagination hasNextPage=False.
  - [app/modules/proxy/replay_safety.py:434](https://github.com/Soju06/codex-lb/pull/2121#discussion_r3944991000)
- #2120: base `5ad638b6a4c9c094bcc8866b1d7487173fe3b54e`, exact head `e4718ddefcce93197ecfb67ae8c9f6c72dac0d32`, mergeability `UNKNOWN`, checks {'CANCELLED': 23, 'SUCCESS': 23, 'FAILURE': 4, 'SKIPPED': 8}; 1 active nonoutdated inline threads. Review pagination hasNextPage=False.
  - [openspec/specs/usage-refresh-policy/spec.md:1693](https://github.com/Soju06/codex-lb/pull/2120#discussion_r3944848310)
- #2111: base `bb7b33a9294d3b73a33dd4c2067286a01235e4cc`, exact head `84cce0395f18941ce9272a8cea3e984a61752385`, mergeability `UNKNOWN`, checks {'SUCCESS': 23, 'SKIPPED': 7, 'FAILURE': 3}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #2001: base `713fa5648d23a47087381204b6fb841bd36cbe88`, exact head `e2bed8be5140564501f5b5233af2af738fd4ea46`, mergeability `UNKNOWN`, checks {'CANCELLED': 23, 'SUCCESS': 17, 'SKIPPED': 8, 'FAILURE': 10}; 0 active nonoutdated inline threads. Review pagination hasNextPage=False.
- #1900: base `1205237328b5c15a4d5bf8e7f5e4d5503a1e8734`, exact head `acea4c9af872aa319d8466ec05dbba7fa430ef90`, mergeability `CONFLICTING`, checks {'SUCCESS': 30, 'SKIPPED': 2, None: 2, 'PENDING': 1}; 0 active nonoutdated inline threads. Review pagination hasNextPage=True.

The parallel bounded reports `new-fixes-auth-health.md` and `new-fixes-owner-replay.md` contain additional exact CI links and #1900 constituent analysis. Selection audit follows AGENTS.md, PRINCIPLES.md, CONTRIBUTING.md and project code conventions. Main retains the failing code for the six recommended concerns; selected external diff comparisons identify shared paths rather than assuming disjoint PRs.

## Integration order

Start with #2193, #2260, #2255, #2110, #2119 and #2248. Add missing specs/product-path tests as part of the reviewed integration change. Repair #2234 documentation and include its bounded preservation fix once composed selection tests pass. Other blocked items remain useful repair candidates with their exact evidence above; do not silently treat them as rejected product choices. Keep #1900 whole-branch policy expansion out. Final acceptance requires exact aggregate revision tests, migration/build proof and live identity/pooled quota/Astra checks by the owning agent.


# Remaining open PR runtime relevance audit

Pinned source target: `efe0f581a18a36f4d491b92a36ef79b0c432d252`. Snapshot checked 2026-09-09, including a second current-head/CI read after the separate pooled-runtime cutover. This report selects source concerns, not merge or deployment approval. It does not replace the newly accepted pooled runtime as deployment authority.

Direct include recommendations: **#2236, #2113, #2206**. Useful but need named repairs or composition proof: **#2246, #2235, #2244, #2112, #2059, #2060, #2069**. Other concerns below are excluded or deferred for concrete scope/compatibility reasons. A failed upstream PR may supply a justified local fix only after its failure is understood and the exact aggregate passes the required checks. No PR here is approved for blind cherry-pick.

## Inspected runtime and dashboard candidates

- **#2236 `bed74e5b493f1b0408ed827852a2f8ee9aa4a77d`: Include after current-main composition.** Bounded 16-entry, 60-second dashboard trailing-demand cache. Both current-main callers use the same moving seven-day window. The cache changes only weekly pace display freshness, returns copies, and does not govern pooled usage, authentication or routing. Current-head CI succeeds; no active threads. DIRTY means port the small repository change and retain current import changes.

- **#2113 `6bdde31e7dcf838e8567acaa71ec2f77a5152198`: Include after current-main composition.** Skips JSON serialization when HTTP is already chosen and neither native transport nor payload tracing needs encoded bytes. Native and raw-trace consumers retain serialization, including fallback after WebSocket rejection. Current main still performs both encodes. Current-head CI Required succeeds; release-guard checks were cancelled; no active threads. DIRTY against main requires source composition and HTTP/native/fallback byte-equivalence checks.

- **#2263 `8d6f44f188d76bf2182c51ee041b13168e707626`: Defer transport migration.** Native direct usage GET is a coherent, well-tested migration, with explicit-client and resolved-route precedence, direct-egress gate before helper discovery, bounded retries, and Python fallback only before first dispatch. All current-head checks succeed and no active threads. It changes the fetch dependency used by pooled freshness but supplies no measured operating benefit for this accepted runtime. Do not enlarge the transport transition only because a refactor exists. If root opts in, reconcile removed settings.usage_fetch_timeout_seconds with current USAGE_FETCH_TIMEOUT_SECONDS and prove pooled freshness, retry/body/cancellation and helper failure behavior with the built helper before cutover.

- **#2246 `88920fd0c0e79d85e1b1735488efe1fc02dcd8b8`: Useful, repair before include.** Three live-row partial facet indexes complement selected2253, reducing scans through soft-deleted cohorts. Adds migration 20260909_080000 after 20260909_070000, which needs current-main graph reconciliation. Current-head checks succeed, DIRTY. Active CodeRabbit finding is supported: same-named valid wrong-column/nonpartial indexes are accepted by IF NOT EXISTS and manual drift checks validate names only. Fresh local SQLite may not hit that case, but do not silently call the general migration verified. Validate definitions or record and prove the exact local index preconditions, plus migration/downgrade and2253 composition.

- **#2235 `11ab09ba3572fb496f5270467a503f8b6bd5af8d`: Useful, repair verification before include.** Rewrites conversation watermark joins as scalar subqueries and clamps the raw complement to constant requested_at ranges. Single-statement snapshot semantics, missing watermark fallback and folded/raw union are retained. Removes an unused labeled helper; no app callers remain on current main. CI succeeds, CLEAN, two active test findings: required requested_at index absent from create_all test schema, and plan assertions assume no PostgreSQL parallel scan. Inspecting the test confirms no local index creation or max_parallel_workers_per_gather setting. Reconcile these assertions with test setup before treating PostgreSQL plan proof as sufficient. SQLite semantic regression and current-base query-plan proof remain required.

- **#2244 `666d48578a2066b72c4e79c9a75bd454a165bed9`: Useful, repair contract coverage before include.** Adds bounded terminal-delivery log/metric and disconnect stamps. It leaves bytes and usage settlement untouched, distinguishing a parsed terminal from a completed ASGI send. CI succeeds, CLEAN. Active CodeRabbit coverage finding is real: source-routed SourceStreamingResponse bypasses DeliveryTracedStreamingResponse. Either cover source streams while preserving their finalizer or narrow the observability contract explicitly. Also compose protocol stamps with current main and2260 and test active/queued httptools cycles. No reason to reorder settlement.

- **#2112 `34729b0b1b8a0adecf855d856d0a89ac31f961b8`: Useful, repair gate before include.** Records first upstream activity/response-created latency separately from TTFT; marks locally generated events and IDs so they are excluded correctly. Diff carries2111 owner publication and related spec/test history, so integrate timing atop the independently selected2111 once. No active review threads. Current-head CI fails: streaming/mixin.py is1111 lines versus architecture limit 1100; unit gate repeats that same architecture assertion. Logs saved in other-prs/2112-job-*.txt. This is a concrete candidate failure, not a flaky runner. Extract a coherent responsibility or use current-main composition to bring it below the existing boundary; no gate inflation.

- **#2059 `b896b7febd5ff7e5fc04de2a3f74b1ae70b5a156`: Useful, repair before include.** Viewport-bounded create/edit model-source dialogs fix inaccessible controls and keep title/footer visible. CI succeeds, CLEAN. Three active findings, with source confirmation: moving ModelSourceFormFields loses prior space-y-4 grouping in both scrollers; browser regression only exercises Create, not distinct Edit hierarchy. Restore field spacing and cover edit/save/Escape at compact and desktop sizes before selecting. Preserve current styling rather than redesign.

- **#2060 `0d34254503ecdad3e6d65bda178d5845d66b26dd`: Useful, repair before include.** Exposes the already-supported reactivate endpoint for deactivated accounts while preserving reauth_required restrictions. Does not autonomously reactivate any account. Current-main list column remains 6.5rem, while added fourth action needs 7.75rem; card action row also lacks wrapping. Current-head active findings flag both responsive regressions and missing screenshots. Latest CI Required now fails with frontend test and Docker jobs cancelled. Add list/card coverage and screenshots, correct layout, then reverify current candidate.

- **#2098 `571b6afede4a43625b9c2bdab221927f80e1031b`: Exclude deployment-default change.** Diff removes1455 callback port from both default compose files and adds an optional OAuth override. The accepted local runtime already owns an explicit compose/port contract and rollback. No runtime code fix is supplied. Preserve the actual accepted port bindings; do not import a default-compose policy change into this refresh.

- **#2205 `89c77ac32c353e4cf2d4784edb4767e7eebf1479`: Defer warm-up policy expansion.** One initial Free monthly warm-up after opt-in is reasonable but sends a new warm-up for accounts that current runtime leaves idle. No evidence this operator needs that behavior. Current-head source includes both account and legacy per-window advisory locks, so active review comment has an explicit fixed reply and is no longer a source defect. CI succeeds. Defer based on operating scope, not that resolved-in-code finding.

- **#2122 `925d683a815cee734146dfa6d7ae2f7d959c2d9e`: Defer warm-up threshold contract transition.** Restores visible minimum usage gate and zero default but adds active/legacy columns, triggers, migration and changes which confirmed resets trigger billable warm-up. Current-head CI succeeds and no active threads. Existing local threshold provenance must decide migration semantics; no authorization to silently reinterpret warm-up settings during pooled runtime refresh.

- **#2206 `a1da9f27e5658587cbf2503acbaac40944cefe21`: Include bounded dependency fix.** Lock-only httpx2/httpcore2 2.10.0 to 2.12.0 adds bounded incremental decompression and response cleanup on decoder failure; current main still pins 2.10.0. This is a memory/cleanup fix, not a major test-tool upgrade. No active threads; CI Required succeeds though release guards are cancelled and CodeQL is neutral. Resolve only these dependency entries against current lock, preserving current codex-lb version rather than old beta.6 normalization. Verify Python 3.13 dependency/transport compatibility in isolated build.

- **#2069 `085640b2a9624702d6e996742bd206da5c9b0d72`: Useful, verify composition before include.** Repairs existing pre-visible raw-stream quota recovery for unanchored full resends whose response bookkeeping creates soft ownership. Projection retains completed assistant output and requires account-neutral replay; hard owners, files, conversation/previous-response anchors, single-account routing and post-visible cases remain excluded. Also recognizes exact host heartbeat envelopes. No active threads. Current-head CI Required fails solely observed test_otel lifespan SQLite database-is-locked error; logs saved as other-prs/2069-failure.txt. Requires isolated rerun plus composition with2001/2048/2086/2121 and settlement ordering proof; this is not broad new2207 automatic failover policy.

- **#2095 `94fc99b6937b6d23a03cf2d91344cbff5ca133a8`: Exclude duplicate pricing.** Selected2085 already contains Astra rates and wildcard aliases from2095 plus batch rates and gpt-6 alias. Verified selected2085 source. Importing2095 adds no independent runtime benefit; its active pricing/backfill/test findings do not justify a duplicate carrier.

## Other feature, policy and maintenance PRs

- **#2281 `cb563a9da4d15f0ee51fa1d1ae4e9c1f7a6b899c`**: feat(settings): pause background schedulers from the dashboard. Exclude: moves scheduler policy into DB/UI with migration; no required scheduler pause outcome.

- **#2275 `47d771b73d771f6b5bb95ccf99adde4d9c1cd598`**: feat(settings): conversation archive toggle in the dashboard. Exclude: new recording-control UI/schema, not required for normal relay or pooled quota.

- **#2265 `9833c23cfe7affbcd87e99f2e457d4c610412814`**: feat(settings): per-model context window overrides in the dashboard. Exclude: advertised-context override management and new table/cache; no requested context override.

- **#2258 `4cd9c6cfae958b3e5b095fe332553533928eb386`**: feat(load-balancer): discount relatively slow accounts (first-token latency + per-model output throughput) in weighted selection. Exclude: deliberately changes account weighting by latency/throughput, an unrequested routing-policy choice.

- **#2257 `55568acf8b36bd05ca5d0818a3face90f9af5d08`**: feat(proxy): subscription-exhaustion overflow to a designated model source — decision, wiring, WebSocket evidence routing (ship-dark) (#2123 WP-C2+D). Exclude: subscription overflow to paid model sources and durable pinning is separate policy/cost feature.

- **#2251 `9b16e3377e728ce50669162fa180c4cef61e8e49`**: feat(frontend): fold the auth cards into one Access card that grows with the team. Exclude: RBAC Access UI stacked on 2237; unnecessary account-management rollout.

- **#2249 `82f3c52a409d2ebfa408961fad8f6f302ad84e51`**: chore: release v1.25.0-beta.7. Exclude: beta release version metadata only; does not add runtime fixes.

- **#2237 `bf015bfca68e290d331ede00122059fec6e2fe17`**: feat(frontend): tier the login form and header by account facts, add the invite route. Exclude: RBAC login/invite UI depends on 2226.

- **#2226 `3429e1ab222c56aac0e3a93e68808a9c579ea19c`**: feat(users): add account management, invite links and the roles read API. Exclude: user/invite management depends on 2225, adds schema and authority lifecycle.

- **#2225 `79ab0dca12b9fd39d1950e2b0eda9d0bea52092a`**: feat(audit): record the acting account, target and severity on audit rows. Exclude: audit attribution depends on 2223 user-session rollout.

- **#2223 `9ceb523fa35c0cc8be3c519c6cdf220e3afbfcce`**: feat(auth): make dashboard users the source of truth for login and sessions. Exclude: changes authentication authority and session cookie format, depends on 2218.

- **#2218 `989ed604cfdb00480dda15a817740bc11cbc2cba`**: feat(auth): add dashboard user tables and migrate the shared admin into a user. Exclude: per-user schema/legacy credential mirroring depends on 2217.

- **#2217 `f9705f46f66946018e6ae55c145daff6988b71bd`**: feat(auth): add dashboard role rows with code-defined preset grants. Exclude: unused role-registry schema depends on 2204.

- **#2207 `ab6eb78b368ceec3d9e02383a05829ef0fba07cb`**: feat(proxy): add automatic quota failover. Defer: useful quota-failover feature but adds enabled-by-default setting/schema, 5-second delay and three-attempt policy across raw HTTP/bridge/WS. Requires explicit root choice against preserving existing routing; not a prerequisite for pooled quota/history. Diff and review threads inspected (no active unresolved).

- **#2204 `93516e0a23ac181d70ec08d91123dddd63cc4894`**: feat(auth): reject cross-site dashboard mutations and start the client least-privilege. Exclude stack: CSRF/least-privilege hardening is potentially useful generally, but stacked on 2203/2201/2196 authorization-policy changes; no standalone runtime requirement established.

- **#2203 `bcff468afc1c1e3d04e82f67b329ee04fcbbae04`**: feat(dashboard): hide restricted surfaces from read-only guests. Exclude: guest UI aligns with changed 2201 permission policy.

- **#2201 `b2d241c89aa76fe663d1f6841b6b90a533be62b1`**: feat(auth): restrict guest-visible sensitive surfaces and make guest sessions revocable. Exclude: restricts guest surfaces, redacts identity, changes guest sessions; depends on 2196.

- **#2196 `25e6f337025f7b45e40b130e9629915bfe04a3cb`**: feat(auth)!: add resource-scoped dashboard permission vocabulary. Exclude: breaking permission vocabulary/re-gating foundation for RBAC, not needed for runtime refresh.

- **#2172 `9f7122bf39f8ba82e6e1a7772a8b07c4423988f7`**: docs(companions): add Codex LB for Omarchy. Exclude: Linux companion docs only.

- **#2159 `64604a4162c9a52c2dbc6cbff19713b23dab33af`**: chore(deps): bump vitest from 4.1.11 to 5.0.0 in /frontend. Exclude: Vitest major toolchain bump, no production runtime effect.

- **#2158 `3153e26e08b027c49eea402caba372e94c484032`**: chore(deps): bump @vitest/coverage-v8 from 4.1.11 to 5.0.0 in /frontend. Exclude: Vitest coverage major toolchain bump, no production runtime effect.

- **#2147 `f485b6258db99a144a1af5ced732f4a15e8f0850`**: feat(accounts): add per-account usage caps. Exclude: optional account quota caps, new admission policy/schema; not pooled usage reporting.

- **#2146 `384f45d84a37bab5a72aeb57f17ec378076fd0dd`**: feat(dashboard): add request heatmap on dashboard. Exclude: optional dashboard request heatmap and daily endpoint, unrelated display feature.

- **#2118 `16dcf53039b85acac3e03ff4efb04a3c78b5a878`**: feat(ui): add Japanese dashboard localization. Exclude: Japanese localization, not required by runtime goal.

- **#2116 `8e1db6e0332f32fc5eed0e46c14b026a042a1f93`**: docs: add codex-lb-status community companion. Exclude: Ubuntu companion docs only.

- **#2115 `dcc44154154750e96dd9a3e38afe9078d45e230a`**: feat(proxy): support Astra steering with transport-owned dispatch. Defer/block candidate: Astra steering directly relevant to desktop use, but actual current-head unresolved P2 says queued steers can bypass newly applicable API-key limits. Diff confirms _extend_websocket_api_key_usage returns success with no reservation. Earlier stale-ack P1 has explicit current-head fix reply. Broad 414KB diff changes transport interception/reservation lifecycle; requires fix and regression verification before inclusion.

- **#2101 `bc9dfedf2d202bff5307e2ac77497e14af20d1c1`**: fix(proxy): preserve native history and notes ownership. Exclude: native history/notes hard account-owner affinity is alternative to accepted pooled-history2102; cannot combine blindly. Actual diff adds history_session selection and owner-required native control routing.

- **#2099 `050992d34e506fcf1855150cc6a727ac8e44d38e`**: feat(proxy): preserve async tool results across continuations. Defer: async-tool continuity is protocol-forward per body (sampled Codex clients do not emit async:true); no demonstrated runtime need. Diff changes pending-call state on bridge/WS and replay safety. No active unresolved threads.

- **#2097 `2ad7ff16e5722ca03449d350bd7d33b2278ebc91`**: feat(proxy): enforce Astra configuration-update policy. Candidate requiring root scope decision: supports Astra configuration_update API-key policy and Ultra serialization; actual diff adds strict update/logprob/compaction validation and continuation mutation. No active unresolved threads, but this is a protocol/policy change with rejected-request behavior, not a prerequisite for pooled reporting. Requires native Astra need and compatibility tests. This is a deferral rather than a request for another user permission gate; root can establish operating need from the already-authorized runtime task.

- **#2065 `f7dcbad530b5dfe07c3a5c3a9b4173b18e453094`**: Feature/multi file account import. Exclude broad branch: title/body mismatched multi-file import + standalone search, but file list includes deployment skill, auth/key dashboard/native egress/routing changes. Use focused search fixes already on main/independent PRs, never this aggregate branch.

- **#1938 `5934d0bf67ca32e6fc1a0d826210b1686f6e2a1b`**: feat(accounts): add encrypted portable account bundles. Exclude: encrypted account bundle import/export with migrations and broader resilience/account changes; no requested credential migration.

- **#1932 `05b94da013fc55f3284a9a92309ce898742cd29d`**: feat(db): add safe SQLite compaction. Exclude: stopped-instance SQLite compaction CLI; no observed compaction requirement for refreshing runtime.

- **#1922 `18929128bf0c2c4bff6e8d6a305a95389303e6f1`**: chore(main): release 1.25.0. Exclude: release-please version/changelog metadata, not runtime feature source.

- **#1621 `5d8eff51ad072192640328f9cead8ffefb8a5e71`**: test(spec): model ownership and timeout invariants with TLC controls. Exclude: self-contained formal-spec/TLC tests, no production changes.

- **#1528 `21fc1fdd046cdf936f176e55a6a0cda83310cc70`**: feat(accounts): add per-account usage limits. Exclude: optional per-account usage-limit admission policy; broad routing/schema changes and depends on2193. Not pooled quota reporting; select2193 independently if needed.

## Audit boundary and evidence

50 of the 90 open PRs are covered here. The other 40 belong to authored/existing-pin and new-fix owners. PR2249 and1922 advanced during audit; the source snapshots above carry their fresh heads. Exact metadata/diffs/current-head review threads live in `other-prs/`, `feature-details.json`, and `feature-*-reviews.json`. PR bodies were only used to establish purpose; plausible inclusions were checked against actual source diffs and current main.

No application import, test, Docker command, deployment change, public comment or repository code edit was made. Source review used plain filesystem/git reads and GitHub APIs. Full runtime acceptance, disposable-database migration proof, and preservation of the latest pooled-usage receipt belong to root/container_inventory.


# Feature PR relevance audit

Read-only live GitHub body/file scope audit on 2026-09-09. Exact PR heads below. This is relevance triage, not merge or deployment approval. Full metadata: feature-details.json. Candidate diffs and review-thread snapshots: feature-N.diff and feature-N-reviews.json. No repository changes or tests performed.

- **#2281 cb563a9da4d15f0ee51fa1d1ae4e9c1f7a6b899c** — feat(settings): pause background schedulers from the dashboard. Exclude: moves scheduler policy into DB/UI with migration; no required scheduler pause outcome.

- **#2275 47d771b73d771f6b5bb95ccf99adde4d9c1cd598** — feat(settings): conversation archive toggle in the dashboard. Exclude: new recording-control UI/schema, not required for normal relay or pooled quota.

- **#2265 9833c23cfe7affbcd87e99f2e457d4c610412814** — feat(settings): per-model context window overrides in the dashboard. Exclude: advertised-context override management and new table/cache; no requested context override.

- **#2258 4cd9c6cfae958b3e5b095fe332553533928eb386** — feat(load-balancer): discount relatively slow accounts (first-token latency + per-model output throughput) in weighted selection. Exclude: deliberately changes account weighting by latency/throughput, an unrequested routing-policy choice.

- **#2257 55568acf8b36bd05ca5d0818a3face90f9af5d08** — feat(proxy): subscription-exhaustion overflow to a designated model source — decision, wiring, WebSocket evidence routing (ship-dark) (#2123 WP-C2+D). Exclude: subscription overflow to paid model sources and durable pinning is separate policy/cost feature.

- **#2251 9b16e3377e728ce50669162fa180c4cef61e8e49** — feat(frontend): fold the auth cards into one Access card that grows with the team. Exclude: RBAC Access UI stacked on 2237; unnecessary account-management rollout.

- **#2249 82f3c52a409d2ebfa408961fad8f6f302ad84e51** — chore: release v1.25.0-beta.7. Exclude: beta release version metadata only; does not add runtime fixes.

- **#2237 bf015bfca68e290d331ede00122059fec6e2fe17** — feat(frontend): tier the login form and header by account facts, add the invite route. Exclude: RBAC login/invite UI depends on 2226.

- **#2226 3429e1ab222c56aac0e3a93e68808a9c579ea19c** — feat(users): add account management, invite links and the roles read API. Exclude: user/invite management depends on 2225, adds schema and authority lifecycle.

- **#2225 79ab0dca12b9fd39d1950e2b0eda9d0bea52092a** — feat(audit): record the acting account, target and severity on audit rows. Exclude: audit attribution depends on 2223 user-session rollout.

- **#2223 9ceb523fa35c0cc8be3c519c6cdf220e3afbfcce** — feat(auth): make dashboard users the source of truth for login and sessions. Exclude: changes authentication authority and session cookie format, depends on 2218.

- **#2218 989ed604cfdb00480dda15a817740bc11cbc2cba** — feat(auth): add dashboard user tables and migrate the shared admin into a user. Exclude: per-user schema/legacy credential mirroring depends on 2217.

- **#2217 f9705f46f66946018e6ae55c145daff6988b71bd** — feat(auth): add dashboard role rows with code-defined preset grants. Exclude: unused role-registry schema depends on 2204.

- **#2207 ab6eb78b368ceec3d9e02383a05829ef0fba07cb** — feat(proxy): add automatic quota failover. Defer: useful quota-failover feature but adds enabled-by-default setting/schema, 5-second delay and three-attempt policy across raw HTTP/bridge/WS. Requires explicit root choice against preserving existing routing; not a prerequisite for pooled quota/history. Diff and review threads inspected (no active unresolved).

- **#2206 a1da9f27e5658587cbf2503acbaac40944cefe21** — chore(deps): bump httpx2 from 2.10.0 to 2.12.0. Candidate for root attention: lock-only httpx2/httpcore2 2.10 to 2.12 fixes bounded compressed-response memory and stream cleanup. Actual diff also normalizes package version 1.25.0-beta.6 to 1.25.0b6. No active unresolved threads. Verify current main lock/app native-egress usage and focused dependency compatibility before inclusion.

- **#2204 93516e0a23ac181d70ec08d91123dddd63cc4894** — feat(auth): reject cross-site dashboard mutations and start the client least-privilege. Exclude stack: CSRF/least-privilege hardening is potentially useful generally, but stacked on 2203/2201/2196 authorization-policy changes; no standalone runtime requirement established.

- **#2203 bcff468afc1c1e3d04e82f67b329ee04fcbbae04** — feat(dashboard): hide restricted surfaces from read-only guests. Exclude: guest UI aligns with changed 2201 permission policy.

- **#2201 b2d241c89aa76fe663d1f6841b6b90a533be62b1** — feat(auth): restrict guest-visible sensitive surfaces and make guest sessions revocable. Exclude: restricts guest surfaces, redacts identity, changes guest sessions; depends on 2196.

- **#2196 25e6f337025f7b45e40b130e9629915bfe04a3cb** — feat(auth)!: add resource-scoped dashboard permission vocabulary. Exclude: breaking permission vocabulary/re-gating foundation for RBAC, not needed for runtime refresh.

- **#2172 9f7122bf39f8ba82e6e1a7772a8b07c4423988f7** — docs(companions): add Codex LB for Omarchy. Exclude: Linux companion docs only.

- **#2159 64604a4162c9a52c2dbc6cbff19713b23dab33af** — chore(deps): bump vitest from 4.1.11 to 5.0.0 in /frontend. Exclude: Vitest major toolchain bump, no production runtime effect.

- **#2158 3153e26e08b027c49eea402caba372e94c484032** — chore(deps): bump @vitest/coverage-v8 from 4.1.11 to 5.0.0 in /frontend. Exclude: Vitest coverage major toolchain bump, no production runtime effect.

- **#2147 f485b6258db99a144a1af5ced732f4a15e8f0850** — feat(accounts): add per-account usage caps. Exclude: optional account quota caps, new admission policy/schema; not pooled usage reporting.

- **#2146 384f45d84a37bab5a72aeb57f17ec378076fd0dd** — feat(dashboard): add request heatmap on dashboard. Exclude: optional dashboard request heatmap and daily endpoint, unrelated display feature.

- **#2118 16dcf53039b85acac3e03ff4efb04a3c78b5a878** — feat(ui): add Japanese dashboard localization. Exclude: Japanese localization, not required by runtime goal.

- **#2116 8e1db6e0332f32fc5eed0e46c14b026a042a1f93** — docs: add codex-lb-status community companion. Exclude: Ubuntu companion docs only.

- **#2115 dcc44154154750e96dd9a3e38afe9078d45e230a** — feat(proxy): support Astra steering with transport-owned dispatch. Defer/block candidate: Astra steering directly relevant to desktop use, but actual current-head unresolved P2 says queued steers can bypass newly applicable API-key limits. Diff confirms _extend_websocket_api_key_usage returns success with no reservation. Earlier stale-ack P1 has explicit current-head fix reply. Broad 414KB diff changes transport interception/reservation lifecycle; requires fix and regression verification before inclusion.

- **#2101 bc9dfedf2d202bff5307e2ac77497e14af20d1c1** — fix(proxy): preserve native history and notes ownership. Exclude: native history/notes hard account-owner affinity is alternative to accepted pooled-history2102; cannot combine blindly. Actual diff adds history_session selection and owner-required native control routing.

- **#2099 050992d34e506fcf1855150cc6a727ac8e44d38e** — feat(proxy): preserve async tool results across continuations. Defer: async-tool continuity is protocol-forward per body (sampled Codex clients do not emit async:true); no demonstrated runtime need. Diff changes pending-call state on bridge/WS and replay safety. No active unresolved threads.

- **#2097 2ad7ff16e5722ca03449d350bd7d33b2278ebc91** — feat(proxy): enforce Astra configuration-update policy. Candidate requiring root scope decision: supports Astra configuration_update API-key policy and Ultra serialization; actual diff adds strict update/logprob/compaction validation and continuation mutation. No active unresolved threads, but this is a protocol/policy change with rejected-request behavior, not a prerequisite for pooled reporting. Requires native Astra need and compatibility tests.

- **#2095 94fc99b6937b6d23a03cf2d91344cbff5ca133a8** — feat(cost): add GPT-6 Astra pricing. Defer/block: Astra pricing fixes zero future costs but changes spend-cap accounting; five current active findings include missing API-key-path coverage and historical aggregate backfill. Diff is pricing-only runtime change, tests helper-only; not ready for claim of corrected existing reports.

- **#2069 085640b2a9624702d6e996742bd206da5c9b0d72** — fix(proxy): recover unanchored quota replay. Candidate: actual diff repairs raw-stream pre-visible quota failover when full-resend bookkeeping causes soft owner lock; excludes anchors/conversations/files/hard owners/single-account and verifies neutral replay with retained output. Also recognizes exact host automation heartbeat payload. No active unresolved threads. Requires root checking overlap with selected retry/bridge PRs and integration regression before inclusion.

- **#2065 f7dcbad530b5dfe07c3a5c3a9b4173b18e453094** — Feature/multi file account import. Exclude broad branch: title/body mismatched multi-file import + standalone search, but file list includes deployment skill, auth/key dashboard/native egress/routing changes. Use focused search fixes already on main/independent PRs, never this aggregate branch.

- **#1938 5934d0bf67ca32e6fc1a0d826210b1686f6e2a1b** — feat(accounts): add encrypted portable account bundles. Exclude: encrypted account bundle import/export with migrations and broader resilience/account changes; no requested credential migration.

- **#1932 05b94da013fc55f3284a9a92309ce898742cd29d** — feat(db): add safe SQLite compaction. Exclude: stopped-instance SQLite compaction CLI; no observed compaction requirement for refreshing runtime.

- **#1922 18929128bf0c2c4bff6e8d6a305a95389303e6f1** — chore(main): release 1.25.0. Exclude: release-please version/changelog metadata, not runtime feature source.

- **#1621 5d8eff51ad072192640328f9cead8ffefb8a5e71** — test(spec): model ownership and timeout invariants with TLC controls. Exclude: self-contained formal-spec/TLC tests, no production changes.

- **#1528 21fc1fdd046cdf936f176e55a6a0cda83310cc70** — feat(accounts): add per-account usage limits. Exclude: optional per-account usage-limit admission policy; broad routing/schema changes and depends on2193. Not pooled quota reporting; select2193 independently if needed.
