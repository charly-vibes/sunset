# Document assembly

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## ADDED Requirements
### Requirement: Typed partial assembly
The system SHALL compose compatible parts while preserving typed identity and the existing relations.

#### Scenario: Continuation across magazine pages
- **GIVEN** two regions on separate magazine pages and a continuation relation
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** assembly retains both regions and their continuation without assuming a single page or a total reading order.

### Requirement: Algebraic assembly laws
The system SHALL meet identity and associativity under canonical equivalence for jointly compatible parts.

#### Scenario: Bracketing and identity equivalence
- **GIVEN** three jointly compatible parts
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** both bracketings and the empty assembly produce canonically equivalent results.

### Requirement: Reject incompatible parts
The system SHALL refuse conflicting identities or structural constraints with a finite witness.

#### Scenario: Conflicting origins under one region ID
- **GIVEN** conflicting intrinsic origins under the same region ID
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** assembly refuses the composition with a finite witness instead of silently renaming the source.

### Requirement: Commutative canonical join under the identity profile
Under the identity profile proposed by add-anchor-derived-identity, assembly SHALL be commutative in canonical bytes for jointly compatible parts: merging is by anchor-derived identity, identical observations at one anchor unite, and canonical bytes of compose(A,B) SHALL equal canonical bytes of compose(B,A).

#### Scenario: Operand order irrelevance
- **GIVEN** two jointly compatible identity-profile parts A and B
- **WHEN** compose(A,B) and compose(B,A) are canonicalized
- **THEN** the bytes are identical

### Requirement: Idempotent assembly with absorbing refusal
Under the identity profile, re-assembling a part with itself SHALL be the identity on its canonical bytes, and a refusal operand SHALL propagate: compose(refusal, X) and compose(X, refusal) SHALL both be refusals retaining the original witness.

#### Scenario: Self-assembly is identity
- **GIVEN** an identity-profile part A
- **WHEN** compose(A,A) is canonicalized
- **THEN** the bytes equal the canonical bytes of A

#### Scenario: Refusal absorbs
- **GIVEN** a refusal with witness w and any compatible part B
- **WHEN** they are composed in either order
- **THEN** the result is a refusal whose witness is w
