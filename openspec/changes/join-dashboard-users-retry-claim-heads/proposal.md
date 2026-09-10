## Why

Main9cfce7f21bbad6595acf688be2864f3e466ee5c0 extends guest-session history through dashboard roles, users and compat-admin credential projection. Combined with the published retry-claim merge, the public default upgrade has two heads.

## What Changes

Append a schema-neutral join between the published guest/retry merge and the latest dashboard-user migration. Preserve every published migration identifier, edge and body, including the incoming role/user/session behavior.

## Impact

Databases at either populated parent converge on one head while retaining role rows, grants, users, guest generations and receipt/spool state. No authorization, receipt lifetime, settlement or mixed-version policy is selected here.
