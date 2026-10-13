# DSC 0.3 proposed contract — normative DESIGN, not implemented

**Status:** proposed successor to [v0.2](CONTRACT-0.2.md). `validator.py` is deliberately frozen at 0.2 and MUST NOT be described as a 0.3 validator. This document defines a concrete additive target; no migration or adapter implementation is claimed.

## 0. Base and compatibility

The v0.3 descriptor has all v0.2 mandatory top-level keys, with `version` set to `"0.3"`, and exactly four additional mandatory arrays: `views`, `selectors`, `interpretations`, `coverage`. The existing v0.2 entities retain their shapes except for the changes below. No silent v0.2->v0.3 rewrite; conversion emits a report of assumptions and unrepresentable information. Unknown properties are invalid. JSON scalar restrictions, NFC precondition, duplicate-key rejection and canonicalization algorithm remain those of v0.2. IDs are unique over all instance collections including the new arrays, except view names and coverage entries which are not instance identifiers. No nulls or floats.

```json
{"version":"0.3","id":"issue-1","source":{"format":"pdf","sha256":"<64 lowercase hex>","locator":"local:issue-1"},"regions":[],"contents":[],"relations":[],"annotations":[],"evidence":[],"vocabularies":[],"views":[],"selectors":[],"interpretations":[],"coverage":[]}
```

The above illustrates *shape*, not a valid document (it has no root). See `examples/v03-*.json` for design fixtures. Until a 0.3 validator exists, the examples are NOT certified.

## 1. Named structural views

`views[]`: exact fields `{id,kind,root}`, with `id` ASCII snapshot-unique, `kind` one of `physical|logical|carrier`, `root` a region ID. At least one logical view is required. `regions[]` change from `view` to `view_id` (references `views.id`), retain `id`, `kind` and optional `geometry`. A region belongs to exactly one view. Within each view, `contains` must have exactly one root (`view.root`), every other region exactly one parent, and no cycles. `contains` cannot cross views. To connect a physical region to a logical one, use `realizes`; it may be many-to-many. A logical view may coexist with another logical view. **Cross-view containment is invalid.** Inter-view equivalence is not inferred. A `carrier` view may preserve native EPUB structures without implying page geometry.

`precedes` MUST connect nodes in the same view and the same interpretation context (see §3), be acyclic within that context, and does not assert total order. No geometric sorting is implicit. A consumer requiring total order MUST declare a separate deterministic linearization policy and report incomparable elements. Navigation hyperlinks and EPUB spine ordering MUST NOT be encoded as if they were the same universal kind of `precedes`; such links belong in registered carrier-specific annotations/profiles until a tested common relation exists.

## 2. Source selectors and coordinate frames

`selectors[]`: exact fields `{id,kind,source_sha256,target,locator}` where `kind` is `pdf-area|pdf-object|pdf-text-range|epub-resource|epub-fragment|text-range|external`, `source_sha256` matches the source digest for internal selectors, `target` is a region or content ID, and `locator` is a nonempty string encoded according to a **registered selector profile**. Unsupported selector profile => unsupported/invalid-selector outcome, never a guessed interpretation. Selector syntax, dereference tests, units, axes, rotation, crop and optional affine transformations are profile-defined, not inferred from locator names.

`geometry`, when present, has the v0.2 shape, but the `space` identifier MUST resolve to a versioned coordinate-frame definition in a registered profile: axis directions, origin, unit/scale, target page/resource, rotation/crop mapping; non-axis-aligned geometry is approximated only if the adapter declares that loss. Missing frame definition => invalid_geometry_frame. Zero extents are valid as in v0.2. Selectors may address subranges or disjoint fragments through multiple instances; no intrinsic one-to-one assumption.

## 3. Explicit order and segmentation interpretations

`interpretations[]`: exact fields `{id,kind,view_id,origin,status,evidence}`, where `kind` is `reading-order|segmentation`, `origin` and `status` reuse v0.2 annotation vocabularies, and `evidence` is an array of evidence IDs. `supported` needs at least one evidence; `asserted_without_evidence` none. `relations[]` add optional `interpretation_id` only for `precedes`, required for all v0.3 `precedes` edges. It must refer to a `reading-order` interpretation whose `view_id` matches both endpoints. Duplicate edge uniqueness is `(kind,from,to,interpretation_id)` where applicable. Acyclicity checks apply to each interpretation separately. Competing or mutually inconsistent interpretations MAY coexist; they MUST NOT be merged into a single inferred order. Segmentation differences are represented using distinct named structural views rather than contradictory `contains` edges inside one tree; segmentation interpretation attaches to the corresponding view. Interpretation statuses report attribution/support, not objective correctness.

## 4. Text fidelity and content alignment

`contents[]` retain v0.2 `{id,kind,value}`. Text observations (native, OCR, manual, normalized, corrected) MUST be separate content objects whenever the content strings differ, with evidence and lineage linking transformations, not silently overwritten values. Text-range selectors MUST declare in their profile whether offsets index UTF-8 bytes, Unicode scalar values, or grapheme clusters, whether end is inclusive/exclusive, and the normalization version; offsets are measured **on the exact target content snapshot**. Hyphenation, ligature expansion, Unicode normalization, and bidirectional ordering are explicit transforms when applied. A source transcription cannot be claimed lossless unless a source-specific roundtrip verifier passes.

## 5. Relation-level provenance

`relations[]` also add optional `evidence` as an array of evidence IDs for `contains`, `precedes`, `realizes`, `has-content`; missing evidence means *unverified assertion*, not supported. Relationship provenance is not a substitute for its underlying source selector. `derived-from` continues to link evidence instances and cannot itself carry evidence. For `realizes`, fine-grained aligned fragments use selectors on its endpoint regions/contents plus a registered alignment annotation. No universal alignment semantics are asserted without a registered profile.

## 6. Adapter capability and information-loss accounting

`coverage[]`: exact fields `{feature,status,reason,adapter_id,adapter_version,config_sha256}`; feature is a registered capability name (e.g. `pdf:glyphs`, `epub:spine`); status is `preserved|transformed|approximated|omitted|unsupported|unexamined`; reason a nonempty explanation for all statuses except `preserved` (empty string permitted there); identity/version nonempty; configuration fingerprint is 64 lowercase hex or the literal `unavailable` (the latter means replay UNVERIFIABLE). At least one coverage entry is required for each feature the selected adapter declares in its manifest; manifests are versioned external artifacts. A descriptor may be structurally valid despite omitted features. Reports MUST distinguish `schema_valid`, `source_coverage`, and `interpretation_assessment` independently. Coverage assertions require end-to-end source fixtures to verify and MUST NOT be inferred from v0.2 fixture validation.

## 7. Constraints and migration

Adapters MUST never silently identify their output as complete. A 0.2->0.3 migration must (a) put legacy regions into declared physical/logical views, (b) preserve source digest and old IDs when unambiguous, (c) mark synthesized order interpretation as `asserted_without_evidence`, (d) split legacy physical/logical containment into valid per-view trees by explicit documented transformation or reject/report ambiguities and cross-view `contains` that cannot be converted without guessing, (e) report unknown selector resolution and coordinate-frame definitions, (f) produce `coverage` entries with `unexamined` rather than fabricate extraction capabilities. The migration is a requirement, **not implemented**.

**Non-goals for 0.3:** globally stable IDs; automated semantic truth assessment; universal carrier ontology; built-in EPUB navigation/HTML semantics; auto-merge of disagreements; automatic lossless PDF reconstruction. Profiles must be independently versioned and invalid if undeclared.

## Ontology boundary policy (proposal)

The wire contract does **not** implement general-purpose ontology semantics. See [ONTOLOGY-BOUNDARIES.md](ONTOLOGY-BOUNDARIES.md) and the proposed ontology-boundaries capability ([openspec change add-dsc-03](../../openspec/changes/add-dsc-03/specs/document-ontology-boundaries/spec.md)) for the proposed non-coercion, extension, projection and information-loss obligations. These do not introduce unrecognized fields into 0.3 descriptors: implementations must not claim compliance until a compatible conformance envelope or externally validated report is specified and tested.
