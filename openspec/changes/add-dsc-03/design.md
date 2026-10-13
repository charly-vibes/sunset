# DSC 0.3 review resolutions

This is the rationale for the revised 0.3 proposal, not implementation status.
Normative requirements live in this change's capability deltas. The research
bundle remains immutable provenance; its CONTRACT.md and ACCEPTANCE.md describe
an earlier draft. Where they differ, these active deltas take precedence.

## Decisions and trade-offs

| Review gap | Decision | Cost or limit |
|---|---|---|
| Additive deltas preserve incompatible 0.2 rules | Replace changed requirements using MODIFIED, exercise actual OpenSpec composition in a temporary workspace | Baseline remains 0.2 until a future release; purpose text must be refreshed on promotion |
| Unbound profile interpretation | Add a fifth array, profiles; bind selectors and geometry to versioned, digest-pinned local artifacts | Breaking revision of the unpublished draft; concrete carrier profiles still need implementation |
| NFC discards original text | Exempt text content values from NFC; retain all other scalar restrictions | Canonical bytes distinguish canonically equivalent strings; text comparison must declare normalization |
| Coarse or self-selected coverage | Use independent minimum inventories, source scopes, one disposition per scope and conservative aggregation | Partial preservation is summarized conservatively; exact fractions are not claimed |
| Evidence DAG does not identify transformed content | Bind evidence to produced content and transforms to inputs/outputs; require matching evidence lineage | Additional consistency checks; multi-stage adapters must retain intermediate observations |
| Reader/extractor agreement conflated | Byte equality for readers of one snapshot; pinned projection/oracle for different extraction outputs | Comparison requires source anchors or a reviewed mapping; no universal equivalence algorithm |
| Malformed endpoint crashes frozen validator | Record baseline limitation and require total typed handling in the successor | The frozen research executable is not repaired or advertised as hardened |

## Initial consumer and value hypothesis

The initial consumer is a reviewer reconciling extraction of historical
periodicals: finding disputed text on a page, preserving alternative reading
orders across columns and continuations, and identifying unexamined material.
DSC's proposed benefit is retaining those distinctions across tool boundaries.
It does not claim better OCR or a new universal ontology.

The first-consumer demonstration in document-conformance defines measurable
functional gates and compares review effort and overhead with native extractor
outputs. Until measured, lower review cost is a hypothesis. Existing tools and
standards already provide structure, provenance and selectors; differentiation
must be demonstrated by the combined workflow rather than feature names alone.
Research precedents remain in the preserved evidence-to-decision ledger.

## Scope and implementation sequence

Resolve and test the wire contract first, then implement pinned profile loading,
coverage enumeration and lineage, then the real-source review demonstration.
Full conformance still requires the wider PDF/EPUB corpus and independent readers.
Ontology projections remain part of the proposal but follow this demonstration.
The existing implementation issue is sunset-r68; review corrections are sunset-6pi.

Future implementation tasks pair a failing witness with the minimal behavior
that makes it pass. Behavior-preserving refactoring is tracked separately and,
when commits are authorized, committed separately. No refactor is needed for
these specification corrections.

## Compatibility and migration

The new profile array, selector/geometry bindings, scoped coverage, evidence
bindings and annotation view_id are explicit revisions of the unpublished draft.
A descriptor written to the preserved draft is not silently accepted under this
revision. A future migration must preserve original source digests and ids where
unambiguous, create per-view trees and unsupported order assertions, and report
missing bindings rather than invent them. Unknown frames/profiles and source
inventories remain unverified. Empty coverage without an adapter run means
unexamined, not complete. Existing NFC-only 0.2 text cannot recover original
pre-normalization code points; that loss must be reported.

## Verification boundary

The composition test checks OpenSpec replacement semantics, not descriptor
behavior. Strict OpenSpec validation checks specification structure. The eleven
frozen fixtures exercise only the 0.2 validator. New positive/negative scenarios
are implementation obligations, not executed 0.3 results. No 0.3 implementation,
real-source experiment or ontology interoperability result is claimed here.
