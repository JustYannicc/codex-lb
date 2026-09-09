## Why

A draining owner rejects HTTP bridge requests before accepting them upstream.
PR2088 permits bootstrap recovery, but its error-code inference can erase
ambiguous dispatch evidence. Its recovery path also leaves the rejected
API-key reservation active when a replacement request acquires a new one.

## What Changes

- Preserve the forwarding client's transport outcome.
- Require pre-dispatch evidence for drain recovery on all bootstrap paths.
- Release rejected reservations before replacement admission and reservation.
- Preserve existing account ownership and previous-response constraints.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sticky-session-operations`: safe draining-owner recovery and reservation settlement.

## Impact

Local HTTP bridge routing and tests only. No schema or configuration change.
