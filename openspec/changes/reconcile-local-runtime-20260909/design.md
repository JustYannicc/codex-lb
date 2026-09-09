## Context

The accepted runtime combines September 5 main, twenty selected PR inputs, context and credit repairs, and a September 9 Desktop overlay. Current main includes new native code, dependencies, settings ownership and database migrations. A Python overlay cannot represent that update.

## Goals / Non-Goals

Build a current, reviewable aggregate with explicit source provenance and preserve accepted runtime contracts. This work does not merge upstream PRs, adopt unresolved routing policies, change account authority, or edit another task's worktree.

## Decisions

- Start a registered integration branch at immutable upstream main `efe0f581a18a36f4d491b92a36ef79b0c432d252`.
- Compose frozen current PR revisions and preserve overlapping ownership contracts; record exclusions and superseders in `aggregate-manifest.json`.
- Preserve historical migration revisions instead of rewriting their parents; join lineages when compatible and verify the deployed upgrade path.
- Use the accepted pooled implementation `3f8af6be0c09db264f6994dc29895a2a89442b48` as the client contract reference. Its older-runtime adaptation at `effc2a944313fbf3325330785ba3a3d3e95a1076` is preservation evidence.

## Risks / Trade-offs

Conflict-free Git composition does not prove runtime ownership, settings compatibility, or migration correctness. Multiple PRs touch shared proxy code and must be tested together. Unresolved feature policy remains held. Preserve the existing accepted container until candidate proof is complete.

## Migration Plan

Compare deployed and candidate revision graphs. Rehearse upgrade and restoration on isolated state, build the complete source image, bind review and test evidence to exact identities, then hand the candidate to the deployment owner for a pinned transactional cutover.

## Open Questions

Current PR owners are resolving active findings. Freeze their resulting heads before final validation. The deployment owner must reconcile effective settings where upstream retired environment controls.
