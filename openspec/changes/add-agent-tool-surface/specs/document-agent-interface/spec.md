## ADDED Requirements

### Requirement: Typed outcomes

Every tool SHALL return an envelope with a status from a closed vocabulary, a stable reason code and a data payload, and SHALL NOT raise an exception to the caller.

#### Scenario: Unknown scope

- **GIVEN** a call with a scope id that does not exist
- **WHEN** the tool runs
- **THEN** it returns a typed refusal with a stable reason code

### Requirement: Anchor addressing

Tools SHALL address scopes and claims by anchor-derived ids and SHALL NOT accept page indexes or producer labels as addresses.

#### Scenario: Label as address

- **GIVEN** a call using a legacy label instead of an id
- **WHEN** the tool runs
- **THEN** it is refused with a stable reason code

### Requirement: Document text is data

Document text SHALL be returned only in dedicated data fields marked untrusted, and SHALL NOT appear in status, reason or message fields.

#### Scenario: Hostile page text

- **GIVEN** a page containing text that imitates an instruction
- **WHEN** the page text is requested
- **THEN** the text appears only in a marked data field and nowhere else in the response

### Requirement: Idempotent writes

Write tools SHALL be idempotent through claim ids, so repeating a call SHALL leave the stored claims and queue unchanged.

#### Scenario: Retried proposal

- **GIVEN** a proposal already admitted
- **WHEN** the same proposal is sent again
- **THEN** the claim set is unchanged and the outcome reports it as already present

### Requirement: Bounded deterministic responses

Responses SHALL respect declared size limits and SHALL provide cursors that encode scope, offset and run digest, and a cursor from a different run digest SHALL be refused.

#### Scenario: Stale cursor

- **GIVEN** a cursor obtained from an earlier run
- **WHEN** it is used against a different run
- **THEN** the call is refused with a stable reason code

### Requirement: Gated export

Export SHALL include only claims that satisfy the autonomy gate or carry a human acceptance, together with the checks passed, anchors, scope coverage and the run semantic digest, and SHALL exclude rejected claims.

#### Scenario: Unaudited type

- **GIVEN** a claim type that has not passed the autonomy gate and has no human acceptance
- **WHEN** export is called
- **THEN** its claims are absent from the export

### Requirement: Interface parity

Every exposed adapter SHALL expose the same operations over the same core, and an identical call script SHALL produce identical outcomes through all exposed adapters.

#### Scenario: Parity script

- **GIVEN** a recorded call script and every adapter exposed by this change
- **WHEN** the script runs through each adapter
- **THEN** the outcomes are identical
