# Ontology boundaries and extensibility — DSC 0.3 proposal

## TL;DR

DSC is a **deterministic, loss-aware document-structure substrate**, not a universal semantic ontology. It may record that a document *asserts* a claim, but validating the descriptor does not establish that claim as true. An external ontology may add meaning, reasoning and cross-document identity using explicit, testable projections. Unknown concepts must not be silently coerced into core relationships.

## Provenance and status

- Authoring model: OpenAI GPT-6; date: 2026-10-13.
- Based on `CONTRACT.md`, `specs/`, `ACCEPTANCE.md`, and the comparative research recorded in `RESEARCH-DECISIONS.md`.
- Repository/source commit: **UNKNOWN**. Normative for the **proposed** boundary policy only; no v0.3 implementation or interoperability test is claimed.
- Terms **MUST**, **SHOULD**, **MAY** denote proposed behavioral requirements. They do not imply working validation.

## 1. Three different meanings of “universal”

1. **Carrier coverage:** represent observations extracted from diverse document types (native PDF, EPUB, images, etc.) without silently discarding distinctions.
2. **Semantic coverage:** represent the meaning of arbitrary document content as formally defined, interoperable concepts and relations.
3. **Reasoning coverage:** infer conclusions with explicit semantics and soundness/completeness boundaries.

DSC targets a constrained version of (1), offers attachable claims and projections for (2), and **does not implement (3)**. It does not guarantee faithful representation of every object in every carrier. A failure to represent content is an observable outcome, not grounds for inventing an approximation.

## 2. Guaranteed, proposed and outside scope

| Concern | DSC 0.3 proposed core guarantee | External/profile responsibility | Not guaranteed |
|---|---|---|---|
| Carrier observations | Typed structural entities, views, evidence, selectors, declared coverage | Decoding source-specific structures; selector resolution | Every native feature is represented |
| Structural relationships | Declared `contains`, `precedes`, `realizes`, etc., with scoped validity | Domain-specific relation vocabulary and interpretation | General ontological composition |
| Semantics | Namespaced, attributed annotations; alternative hypotheses | Formal definition of terms, units, ontology mapping | Semantic truth / entailment |
| Identity | Unique snapshot-local IDs | Persistent URI policies and entity reconciliation | Automatic identity across editions |
| Time | Recorded evidence/transform lineage | Revision ontologies and temporal validity | Temporal reasoning |
| Rich media | Anchors/coverage for supported content | Audio/video tracks, time spans, multimodal profiles | General multimodal synchronization |
| Interoperability | Versioned declarations and explicit projections | RDF, OWL, JSON-LD, TEI, IIIF adapters | Native bidirectional equivalence |
| Canonical bytes | Reproducible serialization for valid declared inputs | Stable algorithm/environment and external asset handling | Semantic equivalence, losslessness |

## 3. Gap registry (counterexample → boundary)

| Gap ID | Counterexample DSC may not faithfully model | Route | Observable policy |
|---|---|---|---|
| O01 | A paragraph simultaneously belongs to several independent editorial hierarchies | Existing named views first; extension only if insufficient | Preserve distinct memberships; never pick one silently |
| O02 | The predicate “cites” has transitivity or inverse semantics | Versioned semantic ontology projection | Preserve claim and ontology URI; do not infer properties in core |
| O03 | Two editions refer to the same intellectual work but differ materially | External reconciliation model | Explicit candidate mappings, authority, evidence and unresolved state |
| O04 | A correction was valid only during a dated revision interval | Temporal/revision profile | Preserve dates with scope; no undocumented present-time assumption |
| O05 | Video subtitles align to frames and overlapping audio tracks | Temporal media profile | No spatial rectangle fabricated as a time span |
| O06 | Rival semantic interpretations imply a contradiction | External reasoner / belief-revision policy | Retain claims separately; no automatic winner |
| O07 | RDF blank nodes, OWL restrictions, qualified cardinality, logical negation | Ontology-specific projection | Either explicit representation or `unsupported`; no `contains` proxy |
| O08 | EPUB hyperlink encodes a footnote backlink, not reading order | EPUB navigation profile | Do not convert backlink to `precedes` |
| O09 | Layout is transformed by arbitrary non-affine warping | Geometry extension | Declare unsupported unless a registered geometry model covers it |
| O10 | Historical periodical OCR reading diverges from corrected edition | Competing text observations and alignment profile | Source and correction independently traceable |
| O11 | Ambiguous referent in an image caption points to an external person | Entity-linking extension | Keep uncertainty and source evidence; no ungrounded global identity |
| O12 | A carrier holds executable/interactive/embedded resources | Carrier capability and loss manifest | Report observed, unsupported or unexamined portions honestly |

These are **design counterexamples**, not measured failures of real adapters. Whether individual cases are fully representable by the proposed 0.3 wire contract remains **UNKNOWN** until exercised.

## 4. Boundary decision procedure

For each requested concept, test in order:

1. **Existing core** — express it exactly using current typed entities and relationships without changing their definitions. If possible, add a fixture; do not extend.
2. **Registered profile** — express carrier- or domain-specific data using versioned extension vocabulary, selector and validation rules. Declare the producer and capabilities. The profile MUST NOT redefine core identity, relation kinds, or canonicalization.
3. **External projection** — where formal ontology semantics, inference, global identity, or specialist operations are required, produce a named, versioned mapping to an external representation. Make forward and (if claimed) reverse mapping rules explicit.
4. **Unsupported or unexamined** — if faithful expression is impossible or has not been evaluated, return an explicit limitation with scope, affected source references when available, and reason. **MUST NOT** coerce to the nearest core relation or claim successful preservation.
5. **Core-change proposal** — consider a new primitive only after at least two unrelated real counterexamples require the same invariant and cannot be served by steps 1–4. This is a design policy, not a mathematically necessary threshold. Specify migration impact, a minimal witness and negative test.

An unrecognized extension name alone must not be treated as faithful semantic preservation. Retaining uninterpreted bytes or opaque identifiers is **retention**, not validated interpretation.

## 5. Projection contract

A declared mapping `P: DSC[version, profiles] → TargetOntology[version]` SHOULD include:

- Identifier, version, source/target vocabularies and links to normative definitions.
- Applicable source subset/preconditions, required profiles, selector-resolution assumptions, URI and namespace policy.
- Explicit source-to-target rules for individuals, types, relations, ordering, text anchors and evidence.
- Cardinality policy (zero/one/many), including the handling of overlapping membership and duplicate observations.
- Equivalence criterion: **byte identity**, **structural equivalence**, or **semantic equivalence**; never conflate them.
- Loss classification per mapped feature: `preserved`, `transformed`, `approximated`, `omitted`, `unsupported`, `unexamined`. An approximation requires an explanation.
- Handling of uncertainty, conflicts, unmapped vocabularies, unresolved references, and ontology inconsistency.
- If reverse projection is advertised: `Q` and a declared roundtrip relation. Never infer invertibility from existence of `P`.
- Fixtures with valid examples, counterexamples and independently reviewed expected mappings.

**Proposed formal checks** (relative to a declared domain `D` and observable projection `obs`):

- Determinism: for pinned mapping, input and dependencies, canonical `P(x)` bytes equal on repeat execution, where target serialization supports canonical bytes.
- Source traceability: every target statement claimed as sourced resolves to an eligible source entity/fragment and transformation, or is explicitly declared derived/unattributed.
- Non-invention: every output semantic relation is entailed by declared mapping rules **or** marked as inference/hypothesis, not misreported as direct observation.
- Loss reporting: for each feature within the declared coverage inventory, exactly one disposition and justification are recorded.
- Conditional roundtrip: `obs(Q(P(x))) = obs(x)` **only if** explicitly promised for `x ∈ D`; do not require full document roundtrip by default.

Formal RDF/OWL semantic soundness requires a chosen entailment regime, ontology versions and validated mapping. DSC does not supply that proof.

## 6. Compatibility questions, not equivalence assertions

| Ecosystem | Useful projection | Difficult boundary |
|---|---|---|
| RDF / JSON-LD | URI-addressable nodes, sourced relationships | Open-world reasoning and RDF term semantics differ from local closed descriptor validation |
| OWL | Formal concepts, axioms, inferred classification | DSC claims do not become logically true merely by serialization |
| TEI | Editorial and textual structures | Overlap, milestones, witnesses, variants, stand-off markup |
| IIIF | Canvas regions, source annotations and viewer presentation | Canvas painting/presentation behavior is not the same as semantic reading order |
| METS / ALTO | Archival files, physical/logical maps and OCR positioning | Archival metadata, file relations and OCR-specific granularity |
| EPUB 3.3 | Package, spine, navigation and XHTML | Reflow, embedded resources, hyperlink semantics and scripted behavior |

No official mapping or interoperable implementation is supplied in this bundle; compatibility is a **design target**, not a verified claim.

## 7. Proposed acceptance checks (unimplemented)

- **O-A01 — unknown relation:** encode an unsupported domain relation. A compliant mapping preserves it via a registered profile, emits an external projection, or reports unsupported; never substitutes `contains` or `precedes`.
- **O-A02 — contradictory claims:** two interpretations assert conflicting classifications. Both remain attributable, and no inference of a winning truth occurs.
- **O-A03 — cross-edition identity:** similarly named entities from different editions are not automatically merged; candidate equivalence requires a named comparator and evidence.
- **O-A04 — RDF/OWL projection:** unmapped predicates and axioms appear in a loss manifest; mapping output does not claim semantic equivalence without an entailment policy.
- **O-A05 — roundtrip scope:** a text-only projection may pass text checks while explicitly failing geometry preservation; a full-fidelity badge is rejected.
- **O-A06 — carrier unknown:** a PDF with a potentially uninspected attachment must be marked `unexamined`, not silently `preserved` or `omitted`.
- **O-A07 — temporal media:** timed subtitles require a declared temporal profile; bogus page rectangles are rejected.
- **O-A08 — reproducibility:** canonical repeatability is asserted only after fixing parser, projection version, source bytes and declared dependencies.

## 8. Open questions and known limitations

1. Does the existing wire-contract coverage schema allow distinguishing `unexamined` from `unsupported` for all carrier assets? **UNKNOWN; requires validator and adapters**.
2. What minimal external profile registry and namespace-resolution process is sufficient? **UNKNOWN**.
3. Which anchor selectors remain stable after resaving/reflow/edition conversion? **UNKNOWN**.
4. Should mappings be described declaratively or as versioned executable transformers? **OPEN**.
5. What is the minimal ontology conformance oracle for historical periodical annotations? **OPEN**.
6. Neither source-fidelity nor semantics can be guaranteed by a passing structural validator.

## 9. Primary references

- RDF 1.2 Concepts: https://www.w3.org/TR/rdf12-concepts/
- OWL 2 Overview: https://www.w3.org/TR/owl2-overview/
- JSON-LD 1.1: https://www.w3.org/TR/json-ld11/
- TEI Guidelines: https://tei-c.org/guidelines/
- IIIF Presentation 3: https://iiif.io/api/presentation/3.0/
- METS: https://www.loc.gov/standards/mets/
- ALTO: https://www.loc.gov/standards/alto/
- EPUB 3.3: https://www.w3.org/TR/epub-33/

References are design precedents; this update does not claim a fresh interoperability certification against their full normative texts.
