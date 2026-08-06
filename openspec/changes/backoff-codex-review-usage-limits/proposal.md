## Why

The Codex label sync posts `@codex review` for every merge-ready PR missing a current-head review. When the Codex account behind the sender has exhausted its usage limits, Codex replies "You have reached your Codex usage limits" — and the next sync run re-fires `@codex review` anyway, burning the shared quota further and spamming PR timelines. Observed on 6+ PRs during the week of 2026-08-03 (including #1599). Takeover of #1560 (Komzpa), whose author is unresponsive since 2026-07-31.

## What Changes

- The sync script attributes Codex usage-limit replies to the comment sender that triggered them and skips further `@codex review` posts for that sender while a usage-limit reply is the sender's latest Codex response within a backoff window (default 24h, `--codex-usage-limit-backoff-hours`).
- A newer normal Codex response for the same sender unlatches the backoff; other senders' limits and responses are independent.
- When no quota evidence exists, the script posts the first `@codex review`, waits briefly (`--codex-review-response-wait-seconds`, default 10s), rereads that PR's timeline, and suppresses the remaining review requests if the probe hit the usage limit. Probing stops after the first normal Codex response is observed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `github-automation`: label sync gains a usage-limit backoff for `@codex review` triggers.

## Impact

- Code: `.github/scripts/sync_codex_ok_labels.py`
- Tests: `tests/unit/test_sync_codex_ok_labels.py`
- Specs: `openspec/specs/github-automation/spec.md`
