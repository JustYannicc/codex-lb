MUST make routing, sticky affinity, quota thresholds, warm-up, and account
eligibility understandable from dashboard copy alone.

## ADDED Requirements

### Requirement: Sticky-threads copy distinguishes soft routing from hard continuation affinity

The routing settings SHALL describe `Sticky threads` as a soft preference and
SHALL state that disabling it does not disable hard Codex continuation
affinity for requests that carry continuation state.

#### Scenario: Sticky threads help copy

- **WHEN** the routing settings section renders
- **THEN** the sticky-threads description identifies the toggle as a soft preference
- **AND** an adjacent note states that hard Codex continuation affinity is not disabled by the toggle

### Requirement: Sticky thresholds are presented in percent used with a remaining equivalent

The sticky reallocation threshold controls SHALL name the quota window they
apply to, SHALL state that the value is percent used, and SHALL show the
equivalent percent remaining for a valid threshold value.

#### Scenario: Threshold unit hint

- **GIVEN** the sticky secondary threshold input holds the valid value `70`
- **WHEN** the routing settings section renders
- **THEN** a hint shows `70% used` as equivalent to `30% remaining`

#### Scenario: Quota window explainer

- **WHEN** the routing settings section renders
- **THEN** an explainer identifies primary quota as the 5-hour window and secondary quota as the longer weekly window (monthly on plans without a weekly window)
- **AND** it states that account pages show percent remaining while the thresholds are percent used

### Requirement: Prefer-earlier-reset and limit warm-up copy describe actual behavior

The routing settings SHALL describe `Prefer earlier reset` as preferring
otherwise-eligible accounts whose selected quota window resets sooner, and
SHALL describe limit warm-up as sending one small probe request that consumes
a small amount of quota after an opted-in account's exhausted window resets.

#### Scenario: Prefer earlier reset help copy

- **WHEN** the routing settings section renders
- **THEN** the prefer-earlier-reset description says selection prefers accounts whose selected quota window resets sooner
- **AND** it names the strategies the preference applies to (capacity weighted, usage weighted, and fill first)

#### Scenario: Limit warm-up help copy

- **WHEN** the routing settings section renders
- **THEN** the limit warm-up description says a probe is sent after an opted-in account's exhausted quota window resets
- **AND** it states that probes consume a small amount of quota

### Requirement: Active status is presented as displayed status, not per-request eligibility

The accounts list SHALL annotate the `Active` status badge with a hint that
the displayed status does not guarantee per-request eligibility.

#### Scenario: Active badge eligibility hint

- **GIVEN** an account whose status is `active`
- **WHEN** its accounts-list entry renders
- **THEN** the status badge carries a hint that individual requests can still skip the account
- **AND** non-active statuses do not carry that hint
