# Compose reset pooling with dashboard users

## Why

Main 9cfce7f21 adds roles, users and credential reprojection above guest generation. Composing the published reset/guest merge produces two Alembic heads. Public upgrade-head fails before any upgrade can complete.

## What Changes

Append a no-op merge with the published reset/guest merge and credential-reprojection head as parents. Preserve every published migration. Verify populated upgrades from each parent and merge-only downgrade/re-upgrade without changing authorization or reset policy.

## Impact

Existing grants, identities, user and guest generations, credentials, reset bindings and retention values must survive. Main's credential backfill and reprojection still run when needed. Main's user-backed login and CSRF behavior remain authoritative.
