# Law mapping: conceptual roles and categorical laws onto deployed DSC 0.3

Stage A deliverable of [restore-document-substrate](proposal.md) (sunset-7hs,
2026-10-15). Everything below cites deployed entities (`dsc03/*.py`, deployed
specs under `openspec/specs/`) or this change's own harness (`dsc03/substrate/`,
`tests/substrate/`). Per design §1, **no bijection between the six conceptual
roles and 0.3 wire types is asserted** — the roles are a presentation of a
typed relational schema, and the mapping below is the explicit record of how
each role and law is (or is not yet) carried by deployed representations.

Status legend — **satisfied**: a deployed entity carries the role/law and a
test exercises it; **partial**: carried with a recorded expressivity gap;
**missing**: no deployed carrier exists (recorded, never silently dropped).

## Six conceptual roles → deployed 0.3 entities

| Role | Deployed entity | Status | Evidence / gap |
|---|---|---|---|
| Document | descriptor root: `version`/`id`/`source{format,sha256,locator}` + two-reader canonical serialization (`dsc03/canonical.py`, both readers agree and roundtrip) | satisfied | document-core "Descriptor identity"; `tests/substrate/test_substrate_gates.py::TestLawChecks` identity/determinism gates |
| Region | `regions[]` typed `id/view_id/kind(+geometry)`, membership via `contains` trees per named view (`dsc03/validator.py` FIELD_SPECS + containment-tree integrity); page scope grammar `page:N` | satisfied | validators reject orphan/duplicate/cyclic regions; native/scanned/financial oracles assert declared page+coordinate basis |
| Content | `contents[]` kinds `text/image/number/structured/binary-reference`, bound by `has-content` (region→content, may attach one content to regions in several views) | satisfied | scanned oracle: OCR text + image digest contents; EPUB oracle: structured spine/nav observations |
| Relation | typed edges `contains/precedes/realizes/has-content/derived-from` with `RELATION_RULES` arity table; reading order only under a declared `interpretations[]` record (`kind=reading-order|segmentation`) | satisfied | validator rejects mistyped/dangling/unknown edges (`relation_type`, `dangling_reference`, `unknown_relation`) — substrate counterexample test asserts structured rejection, no crash |
| Annotation | `annotations[]` namespaced `term` (`vocabularies[]`), `origin`/`status` (`supported` ⇒ evidence-bound; `asserted_without_evidence` ⇒ unverifiable) | satisfied | financial oracle: domain roles are `fin:*` annotations over core regions, `origin=inferred`, `status=asserted_without_evidence` — interpretation layer stays interpretation |
| Evidence | `evidence[]` + `selectors[]` + pinned `profiles[]` (`selector/geometry/carrier-inventory/adapter-manifest/alignment`) + `coverage[]` dispositions + transform lineage replay (`dsc03/evidence.py`, `dsc03/profiles.py`, `dsc03/coverage.py`) | satisfied | scanned oracle replays OCR transforms to the recorded text (`evidence.replay` → `replayed`); coverage verified per real enumeration |

**Partial role notes (recorded gaps, no wire delta submitted — Stage C is out
of scope for this ticket):**

- A region names exactly one `view_id`; "one region in two logical views" is
  expressed today by reified region nodes per view (`realizes` to shared
  content), not by one node with two memberships. Workable, but the
  categorical-model scenario "overlapping document hierarchies" is only
  indirectly expressible — **partial**; candidate expressivity gap for a
  future wire delta.
- Many-to-many relations beyond spans of the five core kinds (e.g. arbitrary
  evidence-to-evidence support graphs) have no generic typed-edge vocabulary —
  **partial**.

## Nine design §4 laws → deployed 0.3 entities and harness checks

| # | Law | Status | Satisfying entity / requirement | Falsifiable check |
|---|---|---|---|---|
| 1 | Type/ref integrity: every typed edge has in-scope endpoints; invalid endpoint rejected, not crash | satisfied | `dsc03/validator.py` semantic phase (`document-core` outcome states); substrate `laws.typed_check` wrapper never raises | `TestLawChecks::test_mistyped_edge_rejected_not_crashed`, `::test_dangling_endpoint_rejected_not_crashed` |
| 2 | Structural separation: page position does not determine reading order; an EPUB footnote backlink is not `precedes` | satisfied | `precedes` requires a declared `interpretations[]` record; EPUB adapters capture spine order as structured observation; `oracles.epub_link_edges` classifies backlinks and never emits reading order | `TestEpubOracle::test_no_reading_order_edges_invented`, `::test_footnote_backlink_is_not_a_precedes_edge` |
| 3 | Identity: unique within declared scope, stable under canonical serialization; global cross-edition identity needs external mapping | satisfied (in-scope) / missing (cross-edition) | two independent canonical readers (`dsc03/canonical.py`); descriptor `id` + `source.sha256` scope identity. Cross-edition identity has **no** deployed entity (alignment profiles exist as a kind but no mapping machinery) — recorded missing, alignment-profile route noted | substrate identity gates: canonical agreement + roundtrip stability in `TestNativePdfOracle::test_determinism_across_runs` and every oracle's canonical comparison |
| 4 | Determinism: pinned descriptor, profiles, dependencies → identical canonical output or identical classified failure | satisfied | pinned profiles resolve by (kind, version, sha256) — never URI/`latest` (`dsc03/profiles.py`); adapters pin `config_sha256` per run | oracle re-run equality tests (native, scanned incl. full OCR pipeline) assert identical canonical bytes |
| 5 | Composition: identity + associativity on declared observables for scope-compatible mappings; incompatible mappings rejected before composition; identity of pure descriptor preserves observables | partial | transform lineage (`document-evidence` MODIFIED, `dsc03/evidence.py` replay with `derived-from` producer edges) carries provenance through chains, but the deployed kernel has **no** composition checker; the substrate harness supplies a typed `Mapping` algebra (`dsc03/substrate/laws.py`: source/target schemas, observable scope, loss scope, `compose` pre-checks scopes, loss union propagates) and witnesses the laws on validated finite fixtures | `TestLawChecks::test_identity_mapping_preserves_observables`, `::test_composition_associativity_on_declared_observables`, `::test_incompatible_composition_rejected`, `::test_loss_accounting_accumulates`. Machinery-level witness, not a kernel proof |
| 6 | Non-invention: derived interpretation never becomes a direct source observation | satisfied | validator: `origin ∈ {extracted, inferred}` ⇒ `transform` required (producer semantics); OCR contents produced by `origin=extracted` transform evidence with pinned engine/lang/dpi dependencies | `TestScannedHybridOracle::test_non_invention_holds` (0 violations) + counterexample `::test_non_invention_counterexample_flagged` (`derived_marked_as_source`) |
| 7 | Failure of factorization: sign-bearing geometry vs text-only flattening ⇒ declared loss | satisfied | coverage loss vocabulary (`preserved/transformed/approximated/omitted/unsupported/unexamined` least-first summaries, `dsc03/coverage.py`) + ontology-boundaries O-A04 loss manifests; harness sign-column counterexample renders the law falsifiable | `TestLawChecks::test_factorization_limit_sign_counterexample` (`loss_declared`) + `::test_sign_claiming_mapping_refuted` (`claimed_illegitimately`) |
| 8 | Conditional cross-format agreement: equivalence only under a declared alignment relation + scope with independently justified alignment | partial | `alignment` profile kind exists; `dsc03/boundaries.py::equivalence_claim` refuses unevidenced equivalence claims (O-A05); harness refuses any cross-carrier equivalence without a declared scope | `TestLawChecks::test_equivalence_without_alignment_is_unsupported` + `::test_equivalence_with_alignment_compares_only_agreed_scope`. Full PDF↔EPUB edition alignment: **missing** (no deployed alignment oracle) |
| 9 | Provenance: derived claims resolve to recorded sources/transformations or explicit unsupported/unexamined status | satisfied | evidence source_refs anchor `sha256:<carrier>#page:<i>`; unexamined/unsupported coverage statuses REQUIRE a reason (validator-enforced); report stack separates schema/profile/coverage/interpretation (`dsc03/report.py`) | scanned oracle's OCR replay (`replayed` for all 6 pages of the diario carrier); native oracle's declared approximated image dispositions |

## Second independent reader (machinery-level, agent-executed)

Recorded deviation (standing rule: a human pass supersedes): reader B is an
**independently coded scripted reading path** (`dsc03/substrate/reader_b.py`
— pdftotext-based text runs, own OPF walk, own descriptor builder; it reuses
no reader-A grouping logic). Agreement is measured on **declared
observables** matched by source anchors. This is NOT human review and NEVER a
real-carrier conformance claim. Full table: see
[docs/src/conformance-matrix.md](../../../docs/src/conformance-matrix.md).

Summary: on the EPUB carrier both readers agree on every declared package
observable; on all four PDF carriers page inventory and per-page text
presence agree while exact text differs (extraction engines legitimately
disagree on whitespace/hyphenation — the disagreement is reported, not
forced into a winner); reader B honestly leaves `pdf:images`,
`pdf:vectors`, `pdf:annotations`, `pdf:attachments` unexamined with reasons.

## Unresolved expressivity findings (Stage C inputs — no deltas submitted)

1. Two-view membership for a single region is only indirectly expressible
   (reified nodes + `realizes`) — candidate wire delta, unproven necessity.
2. Cross-edition identity needs a deployed external-mapping contract;
   alignment profile kind alone does not provide one.
3. The composition laws are witnessed harness-side; a kernel-level
   composition checker would move law 5 from partial to satisfied.
