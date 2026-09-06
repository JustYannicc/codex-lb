# Accept context operations in dashboard request logs

## Why
Context operations emit `requestKind: "codex_context"`, which the dashboard rejects. A single such row prevents the entire request-log page from loading with `Response schema mismatch`.

## What Changes
- Accept the existing context request kind in the dashboard response schema.
- Cover mixed inference and context pages, including failed context operations.

## Impact
Dashboard response validation only. No proxy, database, configuration or routing changes.
