# Design decisions — views/space/context slice (sunset-905.2, 2026-10-15)

Decision record for `specs/document-views/spec.md`,
`specs/document-space/spec.md` and `specs/document-context/spec.md` (this
change). Scope: the three deltas' **Properties tables** (16 named
properties) as realized by the consumer-side modules
`dsc03/substrate/views.py`, `dsc03/substrate/space.py` and
`dsc03/substrate/context.py` with law fixtures
`tests/substrate/test_views_space_context.py` (19 fixtures, 16 properties
covered). Companion to `design-decisions-assembly.md` (sunset-905.1). No
new normative scope is introduced; every decision resolves an
underspecified point *inside* the deltas' existing invariants. The deployed
wire (`openspec/specs/`, frozen bundle) is untouched; these are
machinery-level witnesses, never conformance claims. Synthetic fixtures
only — no subprocesses, no OCR runs, no real carriers (sunset-7hs finding).

## Placement

Three modules (one per delta) rather than one `composition.py`: each delta
names its own invariant family and its own fixture builder, so 1:1
module↔delta mapping keeps traceability direct (each module header cites
its delta). All three reuse `laws.typed_check` (classified validation,
never raising), the synthetic-instance patterns, and — for
`no_union_on_assembly` — `assembly.compose()` from slice 1.

## D1 — Cycle path witnesses are computed, not stored (cycle_refused, partial_order_ok)

**Decision.** The deployed validator rejects containment and reading-order
cycles but reports only the reason codes (`containment_cycle`,
`order_cycle`). `views.containment_cycle_report` / `views.order_status`
re-derive the **cycle path** (first region == last region) from the
declared edges, so the refusal names the offending cycle itself. The
deployed wire gains no field; the witness is a consumer-side diagnostic.

## D2 — Projection keeps view roots as structural anchors (projection)

**Decision.** `views.project(desc, keep)` keeps exactly the selected
regions and each *surviving view's root* region. The 0.3 wire mandates
every view's root exists (`containment_roots`), so dropping a view's root
would make the result an invalid descriptor; view roots are therefore
structural anchors, not selected payload. Everything else cascades to a
fixpoint: dropped regions orphan their edges; pruned contents orphan
evidence; pruned evidence orphan relations and annotations. Every dropped
edge is reported in `excluded`; dropped **precedes** (reading-order
continuation) links are additionally recorded as *wire coverage entries*
(`status: omitted`, with reason) — the projection never claims full
fidelity. An invalid result is a classified refusal, never a silent merge.

## D3 — Refinement is conflict-by-default (refinement_conflict)

**Decision.** `views.refinement_check(base, refined)` classifies a
refinement that removes established scoped edges: edges present in base
but absent in refined are a **conflict** unless they are *declared*
superseded under an explicit policy (then the outcome is `superseded` with
the policy name). There is no silent path: both classifications name the
removed edge ids as witnesses. Supersession is a module-level declared
policy (the wire has no supersession field — that remains a recorded
finding, see the property table).

## D4 — Links stay links; reading order is over leaf blocks
(links_not_containment, partial_order_ok)

**Decision.** `views.link_check(a, b)` reads the declared edges between
two endpoints and reports their kinds; a `contains` edge between the pair
is a violation — the module only *reads*, it never invents a parent
pointer. `views.order_status` computes incomparable pairs over **leaf
content blocks only** (container regions with contains children are
structural, not sequence members): with no declared precedes edge the two
columns stay incomparable and no total order or linearization view is
inferred.

## D5 — Spatial predicates return typed unknowns and emit nothing
(cross_page_unknown, spatial_not_order, no_spatial_reading_order)

**Decision.** `space.above/left_of/overlap` compare two geometry loci
*only within one declared coordinate frame* (`space` string): across
frames without a pinned transform the result is
`{"status": "unknown", "reason": "incompatible_frames"}` — a typed
unknown, never `false`, never `null`, never an exception. `space.
spatial_predicates(desc)` evaluates the predicates read-only and
`space.emitted_order_edges(report)` is **always empty by law**: no
above/left-of/overlap result is ever turned into a `precedes` or
`contains` edge; the descriptor's relation set is unchanged after
evaluation (asserted in the fixtures).

## D6 — The rotation transform is a declared bijection with explicit
tolerance (pdf_rotation, roundtrip_transform)

**Decision.** `space.transform_rot90(box_w, box_h)` declares both
directions (normalize: rotated frame → source frame;
denormalize: source → rotated) and a numeric tolerance (0 — the fixture
arithmetic is exact on integers). `roundtrip_transform` composes
forward∘inverse and checks equivalence *within the declared tolerance*,
not bit equality, so a lossy transform would be classified honestly.

## D7 — EPUB identity is the spine selector; viewport XY is rendering state
(epub_reflow)

**Decision.** `space.epub_identity` anchors identity on the stable
spine/fragment selector (`epub-fragment` selector, its locator); viewport
observations are module-level rendering records (deliberately not wire
geometry) and differing viewport XY is *allowed and recorded*
(`xy_differs`), never used as identity.

## D8 — Native and OCR readings coexist by declared lineage (native_ocr_coexist)

**Decision.** `space.hybrid_page_fixture` declares the OCR reading as an
`extracted` observation with a full transform lineage (evidence transform
+ derived-from to the input's producer — the deployed kernel validates
exactly this binding). `space.mixed_observations_report` asserts
coexistence: distinct contents, distinct evidence origins (`source` vs
`extracted`), and no record claiming both readings — no supersession is
invented. Synthetic OCR only (`ocr-sim` dependency label); no OCR runs.

## D9 — Claims are wire annotations; classification is structural
(publication_date, quoted_author, uncertain_ocr)

**Decision.** Semantic claims use the deployed annotation record
(target/term/value/origin/status/evidence — exactly what
`claims_attributed` names). `context.claim_classification` separates
**publication context** (metadata term on a container region that binds no
content) from a region's own **narrated claim**, so the issue date stays
issue metadata and is never a date narrated by the poem.
`context.inherited_bindings` returns `[]` by default — nothing is
inherited automatically; with a *declared* policy (inherit terms + along
`contains`) inherited bindings are collected from ancestor regions and
always marked `provenance: "inherited"`. `context.elected_winner` returns
`None` whenever more than one attributed claim exists: the OCR
transcription keeps `status: disputed` with its evidence (declared
transform lineage) and is never laundered into a fact.

## D10 — Dispute retention; precedence only when declared (context_dispute)

**Decision.** `context.resolve_bindings` keeps incompatible active
bindings **disputed** (all claim ids retained) unless a declared
precedence rule deterministically applies — then the winner is recorded
(`prefer_origin` match) and the losing claims stay retained, never
deleted. No precedence match is itself classified (`no_claim_matches_
precedence`), never a silent pick.

## D11 — Replay equality uses reader A on claim envelopes (same_pinned_input)

**Decision.** `context.evaluate_claims` pins the rule version ("1") and
returns the canonical claim set (sorted by claim id). Claim envelopes are
not wire descriptors, so the deployed two-reader contract
(`dsc03.canonical.reader_a` + `reader_b`, key-set checked against
TOP_LEVEL) does not apply to them directly: replay equality is measured
with reader A's canonical bytes. The descriptor-level two-reader equality
remains available via `assembly.canonically_equal` (exercised by the
assembly slice, sunset-905.1).

## D12 — Assembly unions regions, not truth (no_union_on_assembly)

**Decision.** `context.two_claim_parts` + `assembly.compose()` (slice 1)
assemble two parts each attributing its own `mag:publication-date` claim
to its own poem region. `context.assembled_meaning` verifies no merged or
spanning claim appeared (each claim stays scoped to its own part's
region) and returns `requires_pinned_domain_rule`: assembling regions
does not by itself union their semantic truth.

## Per-property status table

All 16 named properties across the three deltas are **satisfied** — each
has a fixture in `tests/substrate/test_views_space_context.py` and a
realization in the module named below. No property required a wire delta;
no property was left partial or missing.

| Property | Delta | Status | Fixture | Module fn |
|---|---|---|---|---|
| view_overlap | document-views | satisfied | `test_view_overlap` | `views.content_bindings` |
| cycle_refused | document-views | satisfied (path witness computed — D1) | `test_cycle_refused` | `views.containment_cycle_report` |
| partial_order_ok | document-views | satisfied (incomparability + declared-cycle rejection, D1/D4) | `test_partial_order_ok` | `views.order_status` |
| projection | document-views | satisfied (excluded link as wire coverage loss — D2) | `test_projection` | `views.project` |
| refinement_conflict | document-views | satisfied (conflict/supersession classification — D3; wire supersession field remains a recorded finding) | `test_refinement_conflict` | `views.refinement_check` |
| links_not_containment | document-views | satisfied | `test_links_not_containment` | `views.link_check` |
| pdf_rotation | document-space | satisfied (declared bijection — D6) | `test_pdf_rotation` | `space.transform_rot90` / `space.normalize` |
| cross_page_unknown | document-space | satisfied (typed unknown — D5) | `test_cross_page_unknown` | `space.above` |
| epub_reflow | document-space | satisfied (spine selector identity — D7) | `test_epub_reflow` | `space.epub_identity` |
| native_ocr_coexist | document-space | satisfied (declared transform lineage — D8) | `test_native_ocr_coexist` | `space.mixed_observations_report` |
| spatial_not_order | document-space | satisfied (no edge emitted — D5) | `test_spatial_not_order` | `space.spatial_predicates` |
| roundtrip_transform | document-space | satisfied (declared tolerance — D6) | `test_roundtrip_transform` | `space.within_tolerance` |
| no_spatial_reading_order | document-space | satisfied (relation set unchanged — D5) | `test_no_spatial_reading_order` | `space.emitted_order_edges` |
| publication_date | document-context | satisfied (structural classification — D9) | `test_publication_date` | `context.claim_classification` |
| quoted_author | document-context | satisfied (no automatic inheritance — D9) | `test_quoted_author` | `context.inherited_bindings` |
| context_dispute | document-context | satisfied (dispute retained — D10) | `test_context_dispute` | `context.resolve_bindings` |
| same_pinned_input | document-context | satisfied (reader-A replay equality — D11) | `test_same_pinned_input` | `context.evaluate_claims` |
| uncertain_ocr | document-context | satisfied (disputed status + evidence kept — D9) | `test_uncertain_ocr` | `context.elected_winner` |
| no_union_on_assembly | document-context | satisfied (compose + scoping check — D12) | `test_no_union_on_assembly` | `context.assembled_meaning` |

Recorded findings (no action taken — they would need wire deltas, which
are out of scope for this slice):

- `refinement_explicit`: the wire has no supersession/conflict field, so
  the supersession policy is declared module-side (D3).
- `same_pinned_input`: the deployed two-reader contract is
  descriptor-shaped; claim-envelope replay uses reader A only (D11).
- `projection`: view roots are structural anchors the wire forces the
  projection to retain (D2).
