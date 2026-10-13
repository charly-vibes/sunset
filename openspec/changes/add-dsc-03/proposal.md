# Change: add-dsc-03 — DSC 0.3 design proposal

## Why

The DSC 0.2 baseline loses information the comparative document-model research
showed matters: multiple structural views, incompatible reading orders,
source-addressable text/layout, explicit normalization lineage, and honest
extraction coverage. The research bundle
(`spec/document-model-specodelic-v3/`, provenance in its README) proposes the
**DSC 0.3** contract to address exactly those failure modes — and is honest
that **nothing of 0.3 is implemented**.

## What Changes

- Add named structural `views` (physical/logical/carrier) with per-view
  containment trees; cross-view linkage only via `realizes`/registered alignment.
- Add typed, profile-defined `selectors` addressing source content.
- Add explicit `interpretations` (reading-order, segmentation) with evidence;
  competing hypotheses coexist, never merged.
- Add relation-level evidence and distinguishable text observations with
  transform lineage.
- Add per-adapter `coverage` accounting (preserved/transformed/approximated/
  omitted/unsupported/unexamined).
- Add the `document-ontology-boundaries` capability (no silent coercion,
  explicit projections, declared losses).
- Define the 0.2→0.3 migration obligations (reported, never guessed).

## Impact

- Affected specs: `document-core`, `document-structure`, `document-semantics`,
  `document-evidence`, `document-adapters`, `document-conformance`, and the
  new `document-ontology-boundaries`.
- `validator.py` is deliberately frozen at 0.2 and MUST reject 0.3 descriptors
  until upgraded (requirement carried in the document-core delta).
- Non-goals (0.3): globally stable ids; automated semantic truth assessment;
  universal carrier ontology; built-in EPUB navigation/HTML semantics;
  auto-merge of disagreements; automatic lossless PDF reconstruction.
