# Dashboard users and retry-claim composition

Actual target9cfce7f21bbad6595acf688be2864f3e466ee5c0 is later than the initially reported roles-only target08f9634e. Its published chain is guest_session_generation → add_dashboard_roles → add_dashboard_users → reproject_compat_admin_credentials. The other head is published20260910_170000_merge_guest_retry_claim_heads.

A populated retry-parent database retains its live receipt, nondefault spool value and guest generation while receiving the incoming role/user schema and its documented backfills. A populated users-parent database retains custom roles, scoped grants, users and session generations while receiving nullable receipt fields. Downgrading only the join restores both parent stamps without dropping either branch or changing any rows.

Previous repair/review/hosted records stay immutable. This change introduces no sibling PR dependency, modifies no existing revision, and does not select auth or receipt policy.
