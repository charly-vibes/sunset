---
id: document.debugger.comparison.layer
kind: intent
statement: "WHEN multiple compatible DSC representations or mappings are compared, THE debugger SHALL use an explicit observable scope and equivalence policy, preserve disagreements and unknowns, and export reproducible minimal witnesses without asserting unproven semantic equivalence."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| scoped_comparison | invariant | `Every comparison declares inputs, endpoint types, versioned observable scope and comparator` | [[document.debugger.comparison.layer]] |
| typed_outcome | invariant | `Outcomes distinguish equivalent, different, disputed, unsupported and unexamined` | [[document.debugger.comparison.layer]] |
| composition_checks | invariant | `Declared identity and associative composition are checked on compatible typed mappings including their loss/error effects` | [[document.debugger.comparison.layer]] |
| no_edition_guess | invariant | `Document titles and filenames alone never establish equivalent editions or semantic equality` | [[document.debugger.comparison.layer]] |
| counterexample_replay | invariant | `An exported witness records rule, input hashes, exact scope, versions, expected/observed and replay limitations` | [[document.debugger.comparison.layer]] |
| loss_visibility | invariant | `Loss, unresolved evidence and unexamined coverage cannot be converted into pass by normalization` | [[document.debugger.comparison.layer]] |
| independent_agreement | invariant | `Two independently implemented readers agree on canonical fixture outputs for declared comparison policies` | [[document.debugger.comparison.layer]] |

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
| check_scope | inputs_received | scope_checked | types, scopes, comparator and versions are compatible [[document.debugger.comparison.layer.scoped_comparison]] |
| compare | scope_checked | compared | all required observations resolved or typed non-evaluable outcomes emitted [[document.debugger.comparison.layer.typed_outcome]] [[document.debugger.comparison.layer.loss_visibility]] |
| export | compared | exported | witness plus source/descriptor hashes and replay instructions recorded [[document.debugger.comparison.layer.counterexample_replay]] |
| reject_scope | inputs_received | unsupported | incompatible endpoints or missing comparator classified [[document.debugger.comparison.layer.no_edition_guess]] |
| reject_evaluation | scope_checked | unsupported | mapping or comparator unsupported with no equivalence claim [[document.debugger.comparison.layer.composition_checks]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| scope_required | unit | [[document.debugger.comparison.layer.scoped_comparison]] | `missing_comparator_or_scope()` | `comparison returns unsupported not equivalent` |
| typed_differences | unit | [[document.debugger.comparison.layer.typed_outcome]] | `different_vs_unexamined_fixture()` | `outcomes do not collapse to same status` |
| compositional_examples | law | [[document.debugger.comparison.layer.composition_checks]] | `identity_and_three_compatible_transformations()` | `**identity:** compose(identity,m) and compose(m,identity) preserve declared observables; **associativity:** three compatible mappings agree on observables and loss/error scope across bracketings` |
| edition_counterexample | unit | [[document.debugger.comparison.layer.no_edition_guess]] | `same_title_different_edition_pair()` | `no automatic equivalence inferred` |
| replay_roundtrip | unit | [[document.debugger.comparison.layer.counterexample_replay]] | `wrong_order_minimal_witness()` | `replayed diagnostic equals exported rule and witness when replayable` |
| no_loss_as_success | unit | [[document.debugger.comparison.layer.loss_visibility]] | `drop_column_position_and_unknown_coverage()` | `preservation not certified and limitation remains visible` |
| dual_readers | unit | [[document.debugger.comparison.layer.independent_agreement]] | `pinned_canonical_comparison_fixtures()` | `two independent outputs byte-identical after specified canonicalization` |
