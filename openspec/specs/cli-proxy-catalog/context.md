# Configure a separately operated CLIProxyAPI source

CLIProxyAPI owns external provider login and translation. CodexLB remains the client endpoint and keeps its native subscription accounts. The [catalog requirements](spec.md) govern discovery, caching and unavailable identities.

## Register the inference endpoint

Create a source through the authenticated dashboard API, using the CPA inference prefix, normally ending in `/v1`. The key is a CPA inference key, not a management key. For example, this POST body for `/api/model-sources/` enables discovery without a manual model list:

```json
{
  "name": "CLIProxyAPI",
  "baseUrl": "http://cpa:8317/v1",
  "apiKey": "your_cpa_inference_key",
  "supportsResponses": true,
  "catalogMode": "cli_proxy_api"
}
```

The source defaults to manual mode unless you select `cli_proxy_api`. This is a per-source topology setting. No global environment setting or frontend change is required. Keep operating and updating CPA separately.

## Catalog refresh and missing models

Public and Codex catalog reads acquire CPA's rich `/models?client_version=0.144.0` response at most once per source per minute. All acquisitions share a five-second budget, with four concurrent requests and a 2 MiB response limit. Each request owns its database sessions and cancels unfinished acquisitions before returning stored data.

A successful response updates existing model rows in place. Omitted models leave new selections but retain their identity as disabled source models. They return automatically if CPA lists them again. This treats suspension and removal conservatively without deleting conversation history. Fetch failures retain the last successful snapshot.

Requests for an omitted model return an explicit source-disabled error. Requests to an unavailable CPA service return upstream errors. Neither condition silently substitutes another model. Native identities retain the existing default subscription precedence; explicit API-key source assignment retains its existing routing policy.

Manual model-list replacement is rejected while discovery owns the source. Switching `catalogMode` back to `manual` retains existing rows and stops acquisition. Source configuration edits invalidate in-flight refreshes.

## Metadata and compatibility limits

Discovery requires a positive context limit and rejects a complete snapshot if any entry violates its typed bounds. It never fills missing discovered context with the manual-source 128k default. Unknown upstream fields, including internal request overrides, are not copied into the client catalog.

CPA's rich catalog can inherit GPT template values. A structurally valid context, reasoning or modality claim does not prove the actual provider supports it. Verify the exact CPA build and authorized model before relying on those capabilities.

CPA mode preserves Responses tool declarations and replayed namespaces so CPA can translate or reject them. A disposable test of CPA `7fac6b15bcfe5ea55c18c9eaec8e5b7e6457d974` found generic text/function/custom-tool translation and full-history input working. It also found deferred definitions missing from the provider request and no history restoration for `previous_response_id` alone. These are compatibility gaps, not a reduced supported workflow.

External compact forwarding remains a separate CodexLB gap on the inspected base. Existing continuation ownership work in [PR #1905](https://github.com/Soju06/codex-lb/pull/1905) overlaps its settlement rules. This discovery change does not claim full Codex workflow compatibility or live provider acceptance.
