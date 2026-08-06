## 1. Usage-limit backoff

- [x] 1.1 Track per-sender Codex usage-limit and normal-response timestamps from classified PR timelines (`CodexReviewUsageBackoff`).
- [x] 1.2 Skip `@codex review` posts while the sender's latest Codex response within the backoff window is a usage-limit reply; surface a write warning naming the evidence.
- [x] 1.3 Probe after posting when no quota evidence exists: wait, reread the PR timeline, and latch off remaining triggers on a usage-limit reply; stop probing after the first observed normal response.
- [x] 1.4 Report apply-loop status and errors per decision (`decision.repo`/`decision.number`), not the stale classification-loop variables.

## 2. Validation

- [x] 2.1 Unit coverage: latch on recent limit, unlatch on newer normal reply, per-sender independence, probe latch across PRs (asserting per-PR apply lines), probe suppression after a normal response.
- [x] 2.2 Run the sync-script unit suite.
- [x] 2.3 Validate with `openspec validate backoff-codex-review-usage-limits --strict`.
