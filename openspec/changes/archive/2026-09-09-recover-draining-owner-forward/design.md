## Context

The existing owner client signals rejection on a non-200 HTTP response and
acknowledgement on 200. These callbacks already control settlement ownership.
See proposal.md for the two defects in PR2088.

## Decisions

Preserve callback-derived transport outcomes when wrapping proxy exceptions.
Never promote an error-code match into receiver rejection. Bootstrap recovery
checks the drain code together with pre-dispatch evidence before the ordinary
turn-state guard. Previous-response drain recovery receives the same explicit
evidence only at the owner-forward call site.

Release the initial request-state reservation through its existing lifecycle
before local session admission. This also drains deferred health writes after
settlement. Keep the existing replacement reservation and finalizer path.
Reusing the original reservation would require a broader ownership protocol
change across the origin and replacement service.

## Risks

A failed release stops local recovery. The request's existing outer cleanup
remains responsible for retrying settlement. Owner and file constraints remain
in the existing admission call and receive unchanged arguments.

## Delivery

This is a local integration commit with no schema change. Integration tests use
isolated temporary SQLite databases and a loopback owner receiver. Deployment
and hosted review remain with the parent integration task.
