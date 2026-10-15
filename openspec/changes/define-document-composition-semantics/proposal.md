# Change: Define document composition and interpretation semantics

## TL;DR
Extend Sunset's *document description*, not its extraction implementation. Formalize the laws for assembling parts, multiple structural hierarchies, carrier-relative geometry, and scoped semantic interpretation. All laws shall have small positive and negative witnesses and remain inspectable through Sunset Lens.

## Motivation
The existing `restore-document-substrate` proposal specifies typed instances, relations, and transformations but does not fully define document assembly, cross-view hierarchy behavior, geometry, or semantic context. Without these, interoperable descriptions of complex magazines, native PDF and reflowable EPUB remain underdetermined.

## Scope
Add four behavioral capabilities: `document-assembly`, `document-views`, `document-space`, `document-context`. Their specs are proposed additively in dual Specodelic/OpenSpec form. Add a small executable *illustrative* finite model with fixtures; it does not modify the DSC 0.3 wire contract.

## Non-goals
No category-theory runtime, universal language-understanding engine, automatic OCR, PDF/EPUB parser, canonical global reading order, new core primitive, inferred semantic truth, or mandatory geometry for reflowable content.

## Dependencies
- Proposed `restore-document-substrate` change: `document-categorical-model`, `document-purpose`.
- Existing Sunset DSC 0.3 carrier adapters, typed references, structure views, evidence and selectors; resolve exact naming with pinned HEAD before integration.
- `add-document-structural-debugger` may consume witnesses but is not needed to implement validation.

## Compatibility
Prefer additive, versioned extension vocabulary and laws over replacing deployed contracts. Reject an unknown extension as unsupported under declared policy; no silent reinterpretation. No changes to archival history or frozen validator.

## Acceptance
All four capabilities have at least one positive and one negative executable example; model laws are reproducible under deterministic canonical equality; native PDF, EPUB, Ahira scan, hybrid page, and financial record fixtures exercise the same core; no ungrounded fact is promoted from observation to truth. Runtime parity with DSC 0.3 remains UNKNOWN until integration.

## Known unknowns
Pinned Sunset HEAD commit UNKNOWN. Whether current DSC 0.3 schema already exposes all required extension fields UNKNOWN. Executable `spk lint` and OpenSpec integration require available binaries and repo checkout. Do not call these passed without actually running them.

## Integration record (grounded 2026-10-15)

- **Checkout:** sunset `518a71a4abb7caa5e253cc1d5711b7cfce61fbe7`. Deployed
  capability IDs verified (`document-core`, `document-structure`,
  `document-adapters`, `document-semantics`, `document-evidence`,
  `document-conformance`, `document-ontology-boundaries`); the proposed four
  capabilities are new and additive. Dependency proposal
  `restore-document-substrate` is integrated in the same changeset.
- **Validations actually run** (spk 0.10.0):
  `openspec validate define-document-composition-semantics --strict` → valid;
  `spk lint openspec/changes/define-document-composition-semantics` → 0 issues;
  `just spec-check` → all gates green (strict 7/7, tracer 154 passed,
  frozen 0.2 validator PASS 11 fixtures).
- **Integration normalizations applied** (integrated files diverge from the
  as-received zip): four intent statements reshaped to EARS-legal forms
  (Event-Driven/Ubiquitous); ids rekeyed to dotted law (`document.assembly`,
  `document.views`, `document.space`, `document.context`); `## Requirements`
  mirrors added via `spk migrate`; guard citations added for state/transition
  reachability; one missing deriving property per capability added
  (`deterministic_replay`, `no_spatial_reading_order`, `links_not_containment`);
  law-case labels (`**identity:**`/`**associativity:**`) added to law
  predicates.
- **Not done:** executable fixtures, law witnesses, real PDF/EPUB runs,
  second-reader comparison and Lens exposure remain open (see `tasks.md`).
  The mathematical laws remain design requirements until externally executed.

## Rule-of-5 review record (2026-10-15, TypeSafe-verified)

A universal rule-of-5 pass over the integrated set (substrate + composition +
debugger) found and fixed four verified trace/scope defects in this bundle
(Jev 1.13.0: verified 0.87–0.99, 0% measured false-positive rate):

- `document.assembly` Properties `derives_from` column was systematically
  off-by-one; all four cells corrected, plus a merge-path witness
  (`shared_id_merges`) for `boundaries_preserved`.
- `document.space` rows 41–43 and `document.context` rows 42–43 mis-traces
  corrected; `deterministic_replay` (integration-time coverage stopgap)
  consolidated away in favour of corrected `same_pinned_input`, with
  `no_union_on_assembly` and `roundtrip_transform` added for honest coverage.
- `assembly_associative` constraint gained the design's domain qualifier
  ("whose combined constraints do not depend on assembly grouping").
- Cross-file typed guard citations added (assembly→`schema_instance`,
  views→`relational_spans`, space→`conditional_equivalence`,
  context→`non_invention`); `document.debugger.comparison`
  `compositional_examples` normalized to `kind=law` with machine-findable
  law-case labels; `reject_evaluation` guard citation narrowed.
