## ADDED Requirements

### Requirement: Dashboard-user and retry-claim migration branches converge without history changes

The graph MUST join `20260910_170000_merge_guest_retry_claim_heads` and `20260909_020000_reproject_compat_admin_credentials` through a new schema-neutral merge revision. All published migration identifiers, parent edges and bodies MUST remain unchanged. The public default upgrade MUST converge from an empty database or either populated parent to exactly one head matching ORM metadata.

#### Scenario: Upgrade either populated parent

- **GIVEN** a populated parent with retry-failure evidence, guest-session generation and nondefault spool retention, plus live receipts or custom roles, scoped grants and user/session rows where those schemas exist
- **WHEN** `codex-lb-db upgrade head` is run
- **THEN** all preexisting row fields MUST retain their values except transformations explicitly required by the incoming parent migrations
- **AND** incoming role seeding and credential projection MUST retain their documented semantics
- **AND** the graph MUST have one current head with passing policy and drift checks

#### Scenario: Downgrade only the join

- **GIVEN** both parent schemas with populated receipt, role/grant and user/session data
- **WHEN** only the join is downgraded to either named immediate parent
- **THEN** both parent stamps MUST remain and the full schema and all rows MUST be unchanged
- **AND** re-upgrade MUST restore one current head with the same schema and rows
