## ADDED Requirements

### Requirement: Local owner forwarding composes marker and input-shape authentication

A local integration carrying both synthesized-marker ownership and input-shape classification SHALL preserve the pre-classifier body-bound v2 signature fields for compatible predecessor owners. It SHALL authenticate raw input-shape version and target process epoch using an additional domain-separated proof, and MUST NOT enable current classification from an unauthenticated version header. An epoch-bound request MUST reject a missing or invalid input-shape proof. The receiver SHALL continue accepting the earlier classifier-aware v2 signature during transition.

#### Scenario: Marker and file owner reach a compatible predecessor
- **WHEN** a forward carries a synthesized marker and file-owner proof without an epoch-bound classifier requirement
- **THEN** the v2 signature retains the predecessor-compatible field set
- **AND** the new receiver separately authenticates the synthesized marker

#### Scenario: Input-shape proof is stripped from an epoch-bound request
- **WHEN** an epoch-bound forward has no valid additional or earlier classifier-aware proof
- **THEN** the receiver rejects the request before dispatch

#### Scenario: An unsigned version accompanies a legacy proof
- **WHEN** only the legacy v2 proof validates and an input-shape version header is untrusted
- **THEN** the receiver retains legacy classification
