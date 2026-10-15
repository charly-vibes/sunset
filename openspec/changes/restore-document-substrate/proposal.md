# Change: Restore the general document-description purpose and categorical foundation

## Why

Sunset's original Document Structural Core (DSC) goal is a small deterministic, carrier-independent structural description that independently developed systems can exchange and validate. Its current top-level framing instead privileges reconciliation of competing extraction observations from historical periodicals. That is an excellent *consumer*, not a sufficient definition of the *substrate*. As a result, repository acceptance evidence may pass while the foundational interoperability objective remains untested.

The deployed 0.3 machinery already contains useful distinctions: views, source evidence, selectors, coverage, profiles and loss reporting. This change retains those contracts while restoring the generality criterion and explaining the categorical model as **laws over existing representations**, not an additional object hierarchy or mandatory runtime.

## What Changes

1. Add `document-purpose`: normatively state that DSC is a deterministic, extensible document-structure interchange substrate, with extraction review as one consumer. Separate source observation, logical structure and semantic interpretation; support native PDF, EPUB, scanned PDF and structured carriers.
2. Add `document-categorical-model`: define a small typed schema, instance interpretation, composition, identity laws, relational structure, evidence spans, observational preservation and honest partiality. Specify where categorical claims are formal obligations versus explanatory analogies.
3. Keep deployed DSC capabilities unchanged initially. Require a mapping from categorical obligations to existing `document-core`, `document-structure`, `document-adapters`, `document-semantics`, `document-evidence`, `document-conformance` (and deployed extra 0.3 capabilities) before editing wire formats. Exact deployed IDs must be verified in the checkout.
4. Add neutral, independent-consumer conformance gates: native PDF, EPUB, scanned periodical, and a non-periodical domain; include cross-format comparisons where content truly corresponds, negative examples and loss manifests.
5. Update README, docs status, and ACCEPTANCE narrative to distinguish product purpose, current implementation, and narrower first-consumer evidence without revising historical archived decisions.

## Non-goals

- Replacing 0.3 or renaming its fields; promising lossless conversion or a universal ontology.
- Building a CLI, OCR engine, PDF/EPUB parser, inference engine or general categorical programming framework.
- Assuming PDF and EPUB representations are naturally isomorphic, or that evidence implies truth.
- Reopening archived 0.3 proposals; this is a new additive change.

## Impact

- **Specification:** two added capabilities; normative purpose and laws; additive acceptance requirements.
- **Documentation:** a purpose statement and a purpose-vs-consumer decision record.
- **Conformance:** new fixture families and counterexamples; scoped reports distinguishing descriptor validity, adapter fidelity, and interoperable descriptions.
- **Compatibility:** no wire change proposed. If an acceptance test proves existing DSC insufficient, record the minimal counterexample and open a separate backward-compatible delta before changing the core.

## Decision to validate

A first-consumer extraction-review benchmark cannot, by itself, establish that independent systems can deterministically describe documents. Both kinds of gate must exist; neither supersedes the other.

## Source/version integrity

Authored 2026-10-15 by OpenAI GPT-6. Remote repository read on 2026-10-15; exact commit hash UNKNOWN (network environment cannot clone). Current status reports 0.3 implemented and seven deployed capabilities; README is stale. Specodelic format guided by provided `specodelic-main(3).zip`, plus current public Specodelic documentation. This bundle has not been validated against a live Sunset checkout or `spk lint`.

## Integration record (grounded 2026-10-15)

The open integrity questions above are now resolved against a pinned checkout.

- **Checkout:** sunset `518a71a4abb7caa5e253cc1d5711b7cfce61fbe7` (after the
  `add-dsc-03` deployment). Deployed capability IDs verified as exactly the set
  referenced above: `document-core`, `document-structure`, `document-adapters`,
  `document-semantics`, `document-evidence`, `document-conformance`,
  `document-ontology-boundaries`.
- **Validations actually run** (spk 0.10.0):
  - `openspec validate restore-document-substrate --strict` → valid.
  - `spk lint openspec/changes/restore-document-substrate` → 0 issues.
  - `just spec-check` → openspec strict 7/7, tracer suite 154 passed,
    frozen 0.2 validator `PASS 11 descriptor fixtures`.
- **Integration normalizations applied** (integrated files diverge from the
  as-received zip, whose MANIFEST sha256 values describe the originals):
  two ADDED Requirements ("Honest acceptance boundary", "No unjustified
  categorical equivalence") gained the scenarios OpenSpec strict requires;
  ids rekeyed to the Specodelic dotted naming law (`document.purpose`,
  `document.categorical.model`); `## Requirements` capability mirrors added
  via `spk migrate`; transition guards cite own-file constraints so every
  state/transition reaches the intent row; coverage and law-case gaps closed.
- **Not done:** implementation tasks in `tasks.md` remain open; the conformance
  fixtures, mapping table and second-reader work are unexecuted.
