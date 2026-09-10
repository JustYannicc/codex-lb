## Why

A WebSocket terminal finalizer drops model and service-tier scope when it records the selected pending request's health penalty. This violates the accepted rejected-scope requirement in #2327 and prevents a matching probe from recovering such a hold.

## What Changes

- Preserve the scope of the pending request selected for the finalizer's health penalty.
- Extend public WebSocket EOF and pending-request finalization regressions without changing settlement ordering.

## Capabilities

### New Capabilities

### Modified Capabilities

- `account-routing`: cover selected request scope during shared WebSocket finalization.

## Impact

One finalizer call, regression tests and the existing routing spec. No changes to penalty selection, ownership, reservation settlement or operator probe admission.
