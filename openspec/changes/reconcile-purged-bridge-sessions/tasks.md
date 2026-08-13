## 1. Invalidation plumbing

- [x] 1.1 Add `NAMESPACE_HTTP_BRIDGE_PURGE` to `app/core/cache/invalidation.py` (+ log label)
- [x] 1.2 Cleanup scheduler bumps the namespace after `purge_abandoned_before` deletes > 0 rows

## 2. Owner-replica reconcile

- [x] 2.1 `reconcile_purged_http_bridge_sessions()` on the HTTP bridge mixin: snapshot quiescent candidates under the bridge lock, bulk-look up their durable rows, re-validate under the lock, detach + close (with `release_durable_session=False`) sessions whose rows are gone
- [x] 2.2 Register the reconcile as the `http_bridge_purge` invalidation callback in the lifespan (late-bound via `app.state.proxy_service`)

## 3. Tests

- [x] 3.1 Reconcile closes a quiescent session whose durable row is gone and releases its account lease; keeps a session whose row exists; skips sessions with pending work
- [x] 3.2 Cleanup scheduler requests the `http_bridge_purge` bump exactly when the abandoned purge deleted rows
- [x] 3.3 Namespace log-label coverage test stays green (`test_namespace_log_labels_cover_all_namespaces`)
