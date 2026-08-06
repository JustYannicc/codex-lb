## ADDED Requirements

### Requirement: Codex review trigger usage-limit backoff

The Codex label synchronization script MUST NOT post a new `@codex review` comment while the comment sender's latest Codex response within the configured backoff window is a usage-limit reply. Usage-limit evidence MUST be attributed to the sender whose request comment preceded the reply, and a newer normal Codex response for that same sender MUST lift the backoff. When no quota evidence exists for the sender, the script MUST post the first `@codex review`, wait briefly, reread that pull request's timeline, and suppress the remaining review requests in the run if that probe observed a usage-limit reply; probing MUST stop once a normal Codex response has been observed. Apply-loop status lines and error reports MUST reference the pull request of the decision being applied.

#### Scenario: Recent usage-limit reply latches the backoff

- **GIVEN** the sender's `@codex review` comment was answered by a Codex usage-limit reply within the backoff window
- **AND** the sender has no newer normal Codex response
- **WHEN** the script would trigger a missing Codex review
- **THEN** it skips the `@codex review` post and surfaces a write warning naming the usage-limit evidence

#### Scenario: Newer normal response lifts the backoff

- **GIVEN** the sender received a Codex usage-limit reply within the backoff window
- **AND** the same sender has a newer normal Codex response
- **WHEN** the script would trigger a missing Codex review
- **THEN** it posts the `@codex review` comment

#### Scenario: Senders are attributed independently

- **GIVEN** the sender received a Codex usage-limit reply within the backoff window
- **AND** only a different account has a newer normal Codex response
- **WHEN** the script would trigger a missing Codex review
- **THEN** it still skips the `@codex review` post for the sender

#### Scenario: No-data probe latches off remaining triggers

- **GIVEN** no Codex quota evidence exists for the sender in the classified timelines
- **WHEN** the script posts the first `@codex review` of the run
- **THEN** it waits the configured probe interval, rereads that pull request's timeline, and skips the remaining review requests if the probe observed a usage-limit reply

#### Scenario: Probing stops after a normal response

- **GIVEN** a normal Codex response for the sender has already been observed
- **WHEN** the script posts further `@codex review` comments in the run
- **THEN** it does not wait or reread pull request timelines for those posts

#### Scenario: Apply status is attributed to the applied pull request

- **WHEN** the script applies decisions for multiple pull requests in one run
- **THEN** each status line and error report references the pull request of the decision being applied
