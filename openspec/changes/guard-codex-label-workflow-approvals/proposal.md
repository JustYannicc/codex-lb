## Why

Fork pull requests can leave GitHub Actions runs in `action_required` until a
write-capable maintainer token approves them. The Codex label synchronizer now
helps unblock those runs, but the approval path needs an explicit safety
contract so blocked or conflicting pull requests are not mutated as a side
effect of ordinary label classification.

## What Changes

- The label synchronizer may approve `action_required` pull-request workflow
  runs for the selected pull request's current head SHA.
- Approval is skipped for known blocked, conflicting, or unknown merge states.
- Approval is skipped when the pull request changes any path under `.github/`,
  preserving maintainer review for workflow, script, and action-pin changes.
- Approval is skipped when GitHub's pull-request file listing reaches its
  3,000-file cap, because absence of `.github/` can no longer be proven.
- Approval run IDs are accepted only when the workflow run is associated with
  the selected pull request number, so another PR sharing the same head SHA
  cannot be approved through the selected PR's safety checks.
- Approval does not imply `🤖 codex: ok`; the ok label still requires green
  current-head checks, clean current-head Codex review evidence, and no active
  current-head Codex findings.

## Impact

- Code: `.github/scripts/sync_codex_ok_labels.py`
- Tests: `tests/unit/test_sync_codex_ok_labels.py`
- Specs: `openspec/specs/github-automation/spec.md`
