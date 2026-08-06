## Why

A clean upstream close can race the replacement HTTP bridge session with the
old session's durable lease release. The durable row may briefly be active but
ownerless; rejecting the replacement as `bridge_instance_mismatch` strands
otherwise recoverable reconnect and `previous_response_id` requests.

## What Changes

- Treat an ownerless durable bridge row as claimable and advance its owner epoch.
- Preserve fencing so a late close from the previous session cannot clear the
  replacement lease.
- Keep active leases held by another instance protected by the existing
  mismatch contract.

## Impact

This changes only durable HTTP bridge ownership recovery and restores the
existing reconnect behavior covered by integration tests.
