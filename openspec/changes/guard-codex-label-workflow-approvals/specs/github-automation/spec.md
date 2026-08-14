## ADDED Requirements

### Requirement: Codex review label sync workflow approvals

The Codex label synchronization script MUST restrict GitHub Actions
pull-request workflow-run approval to the selected pull request's current head
SHA and to pull requests where GitHub reports a known non-conflicting merge
state. The script MUST skip workflow-run approval lookup and mutation for pull
requests whose merge state is `BLOCKED`, `DIRTY`, `CONFLICTING`, or `UNKNOWN`,
and it MUST skip workflow-run approval lookup and mutation when the pull
request changes any path under `.github/`, or when the changed-file listing
cannot prove `.github/` is absent because it reaches GitHub's 3,000-file pull
request file-list cap. The script MUST approve only workflow runs associated
with the selected pull request number. Workflow-run approval MUST NOT by itself
grant `🤖 codex: ok`; the ok label remains gated by current-head CI,
current-head Codex review evidence, and active current-head Codex findings.

#### Scenario: Clean pull request has action-required runs

- **GIVEN** a selected pull request has current head SHA `abc`
- **AND** GitHub reports the pull request merge state as `CLEAN`
- **AND** GitHub reports pull-request workflow runs for head SHA `abc` as `action_required`
- **AND** those workflow runs are associated with the selected pull request number
- **WHEN** the label synchronizer evaluates the pull request
- **THEN** it records those workflow run IDs for approval
- **AND** it does not grant `🤖 codex: ok` unless the normal Codex review and check gates are also satisfied

#### Scenario: Shared head SHA belongs to another pull request

- **GIVEN** a selected pull request has current head SHA `abc`
- **AND** GitHub reports the pull request merge state as `CLEAN`
- **AND** GitHub reports an `action_required` workflow run for head SHA `abc`
- **AND** that workflow run is associated only with a different pull request number
- **WHEN** the label synchronizer evaluates the selected pull request
- **THEN** it does not record that workflow run ID for approval

#### Scenario: Blocked pull request has action-required runs

- **GIVEN** a selected pull request has current head SHA `abc`
- **AND** GitHub reports the pull request merge state as `BLOCKED`
- **WHEN** the label synchronizer evaluates the pull request
- **THEN** it does not query action-required workflow runs for approval
- **AND** it does not approve any workflow runs for that pull request

#### Scenario: Pull request changes GitHub automation

- **GIVEN** a selected pull request has current head SHA `abc`
- **AND** GitHub reports the pull request merge state as `CLEAN`
- **AND** the pull request changes `.github/workflows/ci.yml`
- **WHEN** the label synchronizer evaluates the pull request
- **THEN** it does not query action-required workflow runs for approval
- **AND** it does not approve any workflow runs for that pull request

#### Scenario: Pull request file listing reaches GitHub cap

- **GIVEN** a selected pull request has current head SHA `abc`
- **AND** GitHub reports the pull request merge state as `CLEAN`
- **AND** the pull request file listing reaches GitHub's 3,000-file cap
- **WHEN** the label synchronizer evaluates the pull request
- **THEN** it does not query action-required workflow runs for approval
- **AND** it does not approve any workflow runs for that pull request

#### Scenario: Conflicting pull request has action-required runs

- **GIVEN** a selected pull request has current head SHA `abc`
- **AND** GitHub reports the pull request merge state as `CONFLICTING`
- **WHEN** the label synchronizer evaluates the pull request
- **THEN** it does not query action-required workflow runs for approval
- **AND** it does not approve any workflow runs for that pull request
