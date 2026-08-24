# Normalize expired durable retry cooldowns

## Summary

An expired durable retry-circuit cooldown must reload as an open circuit with
no cooldown, not as a newly ended cooldown that consumes a half-open probe.

## What Changes

- Map an elapsed or absent durable cooldown to the zero in-memory deadline.
- Preserve future cooldown deadlines and all existing threshold, persistence,
  ownership, and backoff behavior.

## Impact

This is an internal retry-circuit admission fix. It adds no setting, schema,
wire-format, or operator action.
