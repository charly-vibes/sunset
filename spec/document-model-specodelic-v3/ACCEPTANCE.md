# DSC 0.3 falsifiable acceptance matrix (NOT executed)

Tests below are release gates, not results. A validator or adapter run is required before any row may be marked PASS. Reference inputs must include a source digest and independent manually reviewed expected observations. A correct result MAY preserve uncertainty.

| ID | Source case | Expected observable assertion | Failure criterion |
|---|---|---|---|
| D01 | two-column PDF | competing/incomparable reading sequence preserved as separate interpretations | edges silently merged or reading order inferred from x/y |
| D02 | two article continuations | one logical unit maps to multiple physical fragments | forced single placement |
| D03 | two articles share one page | physical and logical trees separately valid | duplicate ownership or cross-view contains |
| D04 | native text + OCR layer | separate observation content IDs and evidence | silent text overwrite |
| D05 | verse, ligatures and hyphenation | original text with separate normalization transform, stable offset unit | unreported character modifications |
| D06 | EPUB footnote/navigation | spine, hyperlink/navigation semantics not conflated with reading order | invented universal precedes |
| D07 | reflowable EPUB | no invented fixed page positions | geometry fabricated |
| D08 | contradicting readers | both attributed hypotheses retained and independently acyclic | global order cycle or silent winner |
| D09 | rotated/cropped PDF | frame transform checked against reference highlight within declared pixel tolerance | wrong coordinate frame without error |
| D10 | canonical roundtrip | v0.3 parsed canonical bytes stable under second serialization | byte mismatch |
| D11 | unsupported vector object | explicit omitted/unsupported coverage entry | complete/preserved reported |
| D12 | pinned extraction replay | identical input/config/dependencies yield explained equality or divergence report | unexplained change marked reproducible |
| D13 | legacy v0.2 conversion | ambiguity is reported; unobserved source capabilities remain unexamined | evidence or coverage fabricated |
| D14 | malformed selector/frame | stable invalid-selector or invalid_geometry_frame outcome | accepted as verified reference |
| D15 | relation-level evidence | wrong/dangling evidence rejected, absent evidence not treated as supported | dangling reference accepted |

## Required evaluation protocol

1. Independently annotate the carrier before evaluating extracted output; retain disagreements.
2. Run schema validation, source coverage checks and interpretive assessment independently; never collapse them into one PASS.
3. Track observed false positives, false negatives and unresolved cases per test; record tool version, source checksum and output digest.
4. Do not require byte-for-byte equivalence between **different** extractors unless a common projection and equivalence oracle are declared. Each extractor must produce deterministic canonical bytes only under a fixed source/config/environment.
5. Publish failing inputs and minimal counterexamples; add validator regression fixtures for each implemented rule.

## Acceptance gate

Release 0.3 conformance is **INCOMPLETE** until (a) the new validator validates the contract and negative fixtures, (b) real PDF and EPUB corpus runs exist, and (c) at least two readers undergo a declared common-projection comparison. No blanket equality expectation applies to competing semantic interpretations.

## Ontology-boundary acceptance obligations (NOT executed)

See [ONTOLOGY-BOUNDARIES.md](ONTOLOGY-BOUNDARIES.md), cases **O-A01–O-A08**. These assess non-coercion, conflicting claims, identity, RDF/OWL projection loss, conditional roundtrips, unknown carrier features, temporal media and pinned reproducibility. They are *design-only* until independent fixtures and a projection evaluator exist. No ontology interoperability PASS is asserted.
