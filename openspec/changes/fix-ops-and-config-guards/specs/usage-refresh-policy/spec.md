## MODIFIED Requirements

### Requirement: Refresh exchange timeouts and claim TTL are bounded

`token_refresh_timeout_seconds` and the OAuth exchange timeout MUST be strictly positive and no greater than 300 seconds. The refresh-claim TTL floor MUST include the proxy admission wait, the fixed 30-second database exchange/persistence budget, and twice the token-refresh exchange timeout.

#### Scenario: Zero refresh timeout is rejected

- **WHEN** settings are loaded with `token_refresh_timeout_seconds=0`
- **THEN** settings validation fails

#### Scenario: Claim TTL covers database work

- **WHEN** settings are loaded with a claim TTL below admission wait + 30 seconds + twice the refresh timeout
- **THEN** settings validation fails
