# Change: add-dsc-03 — DSC 0.3 design proposal

## Why

DSC aims to exchange document observations without losing source location,
transformation history, competing interpretations or extraction omissions.
The first consumer is a reviewer reconciling historical-periodical extraction.
Its benefit over native extractor outputs remains a hypothesis pending the
specified source-traceability and review-effort demonstration.

The preserved research bundle supplies the original proposal. The active
capability deltas revise it to resolve the general review's seven findings;
[design.md](design.md) records decisions and compatibility implications.
Nothing of the 0.3 descriptor/adapter implementation is claimed complete.

## What Changes

- **BREAKING:** replace the 0.2 closed shape, region `view`, global containment
  and order constraints with versioned 0.3 rules and independent named views.
- Add named order/segmentation interpretations; contradictory hypotheses remain
  separate, with no inferred winner or geometric ordering.
- **BREAKING:** add five mandatory arrays: views, selectors, interpretations,
  coverage and profiles. This revises the earlier four-array research draft.
  Profiles are explicit local declarations pinned by version and artifact digest.
- **BREAKING:** allow non-NFC text values while preserving their exact code
  points and retaining canonical serialization stability; normalization is an
  explicit content transform.
- Bind selectors/geometry to profiles, evidence to content/anchors, transforms
  to input/output content, and annotations to views.
- Require independent source-feature inventories, scoped coverage and conservative
  loss aggregation; adapters cannot define completeness by supported features alone.
- Separate same-snapshot reader byte agreement from projected extractor comparison.
- Require typed malformed-input handling in the successor and document the frozen
  baseline's limitations without rewriting it.
- Add explicit ontology boundaries and migration reporting; retain original
  acceptance cases with the active deltas taking precedence where revised.

## Impact

Affected capabilities: document-core, document-structure, document-semantics,
document-evidence, document-adapters, document-conformance, and the new
document-ontology-boundaries. Changed baseline rules use MODIFIED requirements;
new independent obligations use ADDED. The proposal composition test exercises
this distinction without promoting the change in the working repository.

The research bundle and its 0.2 validator remain frozen permanently. A future
0.3 implementation lives outside that artifact. No 0.3 publication, adapter,
real-source demonstration or successful conformance run is implied by this fix.

Non-goals remain globally stable ids, automated semantic truth assessment,
universal carrier ontology, automatic dispute resolution and automatic lossless
PDF reconstruction. The first-consumer demo precedes broad ontology integration.
