## 1. Workflow approval guard

- [x] 1.1 Approve only action-required workflow runs whose head SHA matches the selected pull request's current head.
- [x] 1.2 Skip workflow-run approval lookup and mutation for blocked, conflicting, or unknown merge states.
- [x] 1.3 Skip workflow-run approval lookup and mutation when the pull request changes `.github/**`.
- [x] 1.4 Skip workflow-run approval lookup and mutation when the pull request file listing reaches GitHub's 3,000-file cap.
- [x] 1.5 Filter action-required workflow runs to those associated with the selected pull request number.
- [x] 1.6 Preserve the existing label gate: workflow approval never grants `🤖 codex: ok` by itself.
- [x] 1.7 Unit coverage for allowed clean PR approval, blocked PR skip behavior, `.github/**` skip behavior, capped file-list skip behavior, and selected-PR run filtering.

## 2. Validation

- [x] 2.1 Run the sync-script unit coverage.
- [x] 2.2 Validate this OpenSpec change in strict mode.
