---
id: document.debugger.comparison
kind: intent
statement: "WHEN multiple compatible DSC representations or mappings are compared, THE debugger SHALL use an explicit observable scope and equivalence policy, preserve disagreements and unknowns, and export reproducible minimal witnesses without asserting unproven semantic equivalence."
---

# Document debugging comparisons and counterexamples

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| scoped_comparison | invariant | `Every comparison declares inputs, endpoint types, versioned observable scope and comparator` | [[document.debugger.comparison]] |
| typed_outcome | invariant | `Outcomes distinguish equivalent, different, disputed, unsupported and unexamined` | [[document.debugger.comparison]] |
| composition_checks | invariant | `Declared identity and associative composition are checked on compatible typed mappings including their loss/error effects` | [[document.debugger.comparison]] |
| no_edition_guess | invariant | `Document titles and filenames alone never establish equivalent editions or semantic equality` | [[document.debugger.comparison]] |
| counterexample_replay | invariant | `An exported witness records rule, input hashes, exact scope, versions, expected/observed and replay limitations` | [[document.debugger.comparison]] |
| loss_visibility | invariant | `Loss, unresolved evidence and unexamined coverage cannot be converted into pass by normalization` | [[document.debugger.comparison]] |
| independent_agreement | invariant | `Two independently implemented readers agree on canonical fixture outputs for declared comparison policies` | [[document.debugger.comparison]] |

## Model

### States
- `inputs_received`
- `scope_checked`
- `compared`
- `exported`
- `unsupported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| check_scope | inputs_received | scope_checked | types, scopes, comparator and versions are compatible [[document.debugger.comparison.scoped_comparison]] |
| compare | scope_checked | compared | all required observations resolved or typed non-evaluable outcomes emitted [[document.debugger.comparison.typed_outcome]] [[document.debugger.comparison.loss_visibility]] |
| export | compared | exported | witness plus source/descriptor hashes and replay instructions recorded [[document.debugger.comparison.counterexample_replay]] |
| reject_scope | inputs_received | unsupported | incompatible endpoints or missing comparator classified [[document.debugger.comparison.no_edition_guess]] |
| reject_evaluation | scope_checked | unsupported | mapping or comparator unsupported with no equivalence claim [[document.debugger.comparison.composition_checks]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| scope_required | unit | [[document.debugger.comparison.scoped_comparison]] | `missing_comparator_or_scope()` | `comparison returns unsupported not equivalent` |
| typed_differences | unit | [[document.debugger.comparison.typed_outcome]] | `different_vs_unexamined_fixture()` | `outcomes do not collapse to same status` |
| compositional_examples | law | [[document.debugger.comparison.composition_checks]] | `identity_and_three_compatible_transformations()` | `**identity:** compose(identity,m) and compose(m,identity) preserve declared observables; **associativity:** three compatible mappings agree on observables and loss/error scope across bracketings` |
| edition_counterexample | unit | [[document.debugger.comparison.no_edition_guess]] | `same_title_different_edition_pair()` | `no automatic equivalence inferred` |
| replay_roundtrip | unit | [[document.debugger.comparison.counterexample_replay]] | `wrong_order_minimal_witness()` | `replayed diagnostic equals exported rule and witness when replayable` |
| no_loss_as_success | unit | [[document.debugger.comparison.loss_visibility]] | `drop_column_position_and_unknown_coverage()` | `preservation not certified and limitation remains visible` |
| dual_readers | unit | [[document.debugger.comparison.independent_agreement]] | `pinned_canonical_comparison_fixtures()` | `two independent outputs byte-identical after specified canonicalization` |

## ADDED Requirements

### Requirement: Scoped comparisons
The debugger SHALL compare representations only under compatible, declared observables and equivalence rules, preserving difference versus unknown.

#### Scenario: Text flattening loses transaction sign
- **GIVEN** two physical layouts with identical flattened text but different sign-bearing column positions
- **WHEN** text-only equivalence is requested for signed amounts
- **THEN** the result SHALL be unsupported or different, not equivalent, unless additional sign evidence is supplied.

### Requirement: Composition and diagram witnesses
The debugger SHALL test declared identity and associativity properties for compatible mappings and report minimal counterexamples or unsupported evaluators.

#### Scenario: Composition violates a preservation claim
- **GIVEN** composable transformations with a declared retained-feature scope
- **WHEN** the paths produce different scoped observables
- **THEN** the result SHALL identify the conflicting mapping path and observable, with applicable loss metadata.

### Requirement: Export a replayable counterexample
The debugger SHALL export enough pinned inputs, policy identifiers, witnesses and instructions to independently reproduce a diagnostic, or explicitly mark the result nonreplayable if source bytes are withheld.

#### Scenario: Confidential input redacted
- **GIVEN** a failing financial statement with private content
- **WHEN** the user exports a redacted counterexample without redistributable source bytes
- **THEN** the bundle SHALL omit the protected bytes and mark replayability limits instead of fabricating a reproducible source.

### Requirement: Independent-reader agreement
The debugger SHALL expose canonical comparison outputs suitable for independent conformance tests.

#### Scenario: Two readers
- **GIVEN** a frozen descriptor pair, declared policy and scope
- **WHEN** independent implementations compare them
- **THEN** normalized result codes and witness references SHALL agree.

## Requirements

### Requirement: Scoped comparisons
The debugger SHALL compare representations only under compatible, declared observables and equivalence rules, preserving difference versus unknown.

#### Scenario: Text flattening loses transaction sign
- **GIVEN** two physical layouts with identical flattened text but different sign-bearing column positions
- **WHEN** text-only equivalence is requested for signed amounts
- **THEN** the result SHALL be unsupported or different, not equivalent, unless additional sign evidence is supplied.

### Requirement: Composition and diagram witnesses
The debugger SHALL test declared identity and associativity properties for compatible mappings and report minimal counterexamples or unsupported evaluators.

#### Scenario: Composition violates a preservation claim
- **GIVEN** composable transformations with a declared retained-feature scope
- **WHEN** the paths produce different scoped observables
- **THEN** the result SHALL identify the conflicting mapping path and observable, with applicable loss metadata.

### Requirement: Export a replayable counterexample
The debugger SHALL export enough pinned inputs, policy identifiers, witnesses and instructions to independently reproduce a diagnostic, or explicitly mark the result nonreplayable if source bytes are withheld.

#### Scenario: Confidential input redacted
- **GIVEN** a failing financial statement with private content
- **WHEN** the user exports a redacted counterexample without redistributable source bytes
- **THEN** the bundle SHALL omit the protected bytes and mark replayability limits instead of fabricating a reproducible source.

### Requirement: Independent-reader agreement
The debugger SHALL expose canonical comparison outputs suitable for independent conformance tests.

#### Scenario: Two readers
- **GIVEN** a frozen descriptor pair, declared policy and scope
- **WHEN** independent implementations compare them
- **THEN** normalized result codes and witness references SHALL agree.
