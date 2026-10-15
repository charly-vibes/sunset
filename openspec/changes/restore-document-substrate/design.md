# Design: purpose before application; categorical laws without a category-theory runtime

## 1. Minimal interpretation

Use the existing six conceptual roles (Document, Region, Content, Relation, Annotation, Evidence) as a *presentation of typed relational schema* rather than requiring exactly six new wire types. The concrete 0.3 schema may reify these differently, including views and selectors. Provide an explicit mapping in implementation; never assert a bijection without proof.

In a small category K, objects are declared types and arrows are well-typed functional references. Many-to-many relationships (membership, source support, alternatives) are modeled as relation objects with `source`/`target` arrows, i.e. spans. An instance I: K -> Set assigns finite instance collections and reference functions. Some relation vocabulary is profile-relative, not globally meaningful.

A transformation between document descriptions is a versioned, typed mapping that states preconditions, outputs, loss scope and preserved observables. Composition is allowed only when source/target schemas and scopes match and the result propagates provenance and loss. Identity and associative laws apply to *declared transformations on their applicable domains*; no inverse is presumed.

## 2. Three logically distinct layers

1. Observations: carrier-specific source facts (native PDF text/position, EPUB package/spine/XHTML, image pixels/OCR candidates, structured records).
2. Structure: grouping, containment, views, relations, and partial reading orders.
3. Interpretation: namespaced roles, semantics and domain claims. Annotation != verified truth.

All three may exist together, be partial, or disagree; they are not necessarily a sequential pipeline. Evidence applies to each layer.

## 3. Carrier-specific fidelity

PDF: preserve declared page and coordinate basis, observed text runs/images/vector or attachment inventory as capabilities permit; report unsupported/unexamined features.
EPUB: preserve package/spine, navigation, XHTML hierarchy, links and relevant reflowable structure; do not invent fixed page coordinates.
Scanned PDF: source page image and its coordinates remain primary; OCR text is a derived observation with confidence/uncertainty and engine provenance.
Hybrid: multiple observations of the same region coexist; no silent forced winner. Neither PDF nor EPUB requires OCR.

## 4. Laws and falsifiable counterexamples

- Type/ref integrity: every typed edge has in-scope endpoints; invalid endpoint must be rejected, not crash.
- Structural separation: page position alone does not determine reading order; an EPUB footnote backlink is not `precedes`.
- Identity: identities are unique within declared scope and stable under canonical serialization; global cross-edition identity requires external mapping.
- Determinism: pinned descriptor, profiles and dependencies yield identical canonical output or identical classified failure.
- Composition: for applicable f:A→B, g:B→C and h:C→D, `(h∘g)∘f` and `h∘(g∘f)` agree on declared observable semantics and loss scope. Pure descriptor identity preserves declared observables.
- Non-invention: mappings never assert unobserved semantic facts as direct observations.
- Failure of factorization: if two source observations flatten to identical text but differ in semantically essential column position, no text-only transformation can claim to preserve that sign interpretation; mark loss.
- Conditional cross-format agreement: align *corresponding* content across PDF and EPUB using an independent oracle and compare agreed semantic structure only; never assert entire-format equivalence.
- Provenance: a derived claim's support relation resolves to recorded sources/transformations or an explicitly unsupported/unattributed status.

## 5. Compatibility and rollout

Stage A: map each law to existing deployed 0.3 entities, validators, and documentation; publish gaps. Do not change 0.2 validator.
Stage B: implement golden fixtures and tests in a separate consumer harness, maintaining existing first-consumer tests.
Stage C: evaluate failures; only then submit minimal wire deltas for expressivity gaps.
Stage D: document capability and conformance matrix in README/status, distinguishing `specified`, `implemented`, `tested`, `independently reproduced`.

Rollback: remove new purpose/law delta and tests if the normative intent is rejected; existing 0.3 wire and historical archives remain untouched.

## 6. Verification matrix

| Scenario | Expected observation |
|---|---|
| Native PDF, no OCR | structural descriptor succeeds using native PDF observations and declares unsupported carrier features |
| EPUB with footnotes | spine/navigation and hyperlinks remain distinct; no fake page coordinates or reading-order edges |
| Scanned Ahira periodical | page/regions/poem lines and competing reading orders expressible with provenance |
| Hybrid PDF | native text and OCR observations coexist without overwriting either |
| Financial statement | structural core describes table/header/continuation without adding a banking primitive to core |
| Mis-typed edge | structured rejection; no exception |
| Two independent consumers | both read and canonically interpret shared neutral fixtures with matched observables |
| Lossy flattening | change of sign-bearing geometry makes preservation claim fail or emit declared loss |

## 7. Open questions

- Exact current deployed capability IDs and requirements: UNKNOWN until checkout inspection.
- Which laws can be enforced by Specodelic's kernel versus external conformance: determine by `spk explain`, never infer from prose.
- What canonical observational equivalence policy is appropriate for PDF/EPUB editions: define per fixture, not globally.
- What minimum information about native PDF vector/annotation resources belongs to the default profile: coverage-driven decision.
