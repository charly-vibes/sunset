# DSC conformance matrix

Stage D deliverable of
[`openspec/changes/restore-document-substrate`](../../openspec/changes/restore-document-substrate/proposal.md)
(sunset-7hs, 2026-10-15). It separates, per capability area, what is
**specified** (deployed openspec specs), **implemented** (deployed 0.3
machinery, `dsc03/`), **tested** (tracer + substrate gate suites) and
**independently reproduced** (second independent reading path agreement —
machinery-level, agent-executed; see the standing deviation note below).

**No real-carrier conformance is claimed.** Every label here is scoped to the
machinery and its scripted gates; `dsc03/conformance.py` labels stay
unchanged and honest, and a human pass supersedes anything on this page.

## Capability areas

| Capability area | Specified | Implemented | Tested | Independently reproduced |
|---|---|---|---|---|
| document-core (descriptor schema, canonical bytes, profiles) | yes — deployed spec | `dsc03/validator.py`, `canonical.py`, `profiles.py` | `tests/tracer/` (schema, profiles, negative core) + substrate identity/determinism gates | canonical two-reader agreement on every oracle descriptor and on reader-B's descriptors |
| document-structure (views, containment, typed edges, reading order) | yes | validator semantic phase | tracer tests + substrate typed-edge counterexamples | same validators run inside the independent reader B path (both readers' descriptors validate) |
| document-adapters (inventory, scoped coverage dispositions) | yes | `dsc03/adapters.py`, `coverage.py` | tracer adapter tests over real carriers + substrate oracles (native/scanned/hybrid/financial) | reader B reproduces page inventory + text presence on 4 PDF carriers; leaves other features honestly unexamined |
| document-semantics (annotations, interpretations, vocabularies) | yes | validator annotation/interpretation rules; `report.interpret` | tracer tests + financial-oracle namespaced-role gate | — (no independent reader touches interpretation layers; honest gap) |
| document-evidence (source evidence, selectors, transforms, replay) | yes | `dsc03/evidence.py`, selectors/profiles | tracer replay/lineage tests + scanned-oracle OCR replay (`replayed` ×6) | OCR replay recomputes pinned tesseract output against recorded text |
| document-conformance (readers, projection, first consumer) | yes | `projection.py`, `corpus.py`, `demo.py`, `conformance.py` | tracer conformance-corpus/labels/demo tests | — **real-carrier conformance UNCLAIMED** (anchor-mapping review remains agent-executed; HITL open) |
| document-ontology-boundaries (projection rules O-A01/O-A04/O-A05) | yes | `dsc03/boundaries.py` | tracer ontology tests | — |
| document-purpose (this change) | specified in the change delta (not deployed) | substrate harness gates | `tests/substrate/` (39 tests: oracles + laws) | reader-B agreement, table below; **independent_conformance_demonstrated state NOT reached** |
| document-categorical-model (this change) | specified in the change delta (not deployed) | `dsc03/substrate/laws.py` mapping algebra + scanners | composition/identity/loss/non-invention/factorization gates incl. negative counterexamples | — (law witnesses are machinery-level; no formal verification claimed) |

## Second independent reader — agreement, overhead, unrepresentable cases

Reader B (`dsc03/substrate/reader_b.py`) is an independently coded reading
path: PDF text runs come from `pdftotext` (per-page form-feed stream), the
EPUB package is walked with reader B's own ElementTree traversal, and
descriptors are assembled by reader B's own builder — it reuses none of
reader A's (`dsc03/adapters.py`) grouping logic. Agreement is measured per
**declared observable**, matched by source anchors, never by local ids.

> **Independence caveat (recorded deviation, applies to the whole table):**
> machinery-only, agent-executed. This is scripted-reader independence, not
> human review, and never real-carrier interchange conformance. A human pass
> supersedes.

| Carrier | pages/Package observables | text presence | exact text | Verdict | Reader A bytes | Reader B bytes | Reader B leaves unexamined |
|---|---|---|---|---|---|---|---|
| agentic-patterns-excerpt.pdf | agree | agree | differ | partial-agree | 37 843 | 39 556 | images, vectors, annotations, attachments |
| budgeting-basics-excerpt.pdf | agree | agree | differ | partial-agree | 9 272 | 9 223 | images, vectors, annotations, attachments |
| invoice-arca-redacted.pdf | agree | agree | differ | partial-agree | 10 279 | 15 973 | images, vectors, annotations, attachments |
| cta-cte-propietario-redacted.pdf | agree | agree | differ | partial-agree | 12 920 | 23 603 | images, vectors, annotations, attachments |
| sunset-carrier-sample.epub | agree (manifest/spine/nav/resources) | — | — | agree | 5 490 | 4 979 | — |

Reading of the table:

- **Exact text differing is honest, not failure**: pdftotext and PyMuPDF are
  distinct extraction engines; the descriptor layer keeps both readings
  attributed (source page anchors), and neither is forced into a winner.
- **Descriptor overhead** stays within the same order of magnitude; reader B's
  PDF descriptors run larger where per-page text verbosity dominates
  (`-layout` mode) and smaller on the EPUB (no annotation layer).
- **Unrepresentable-under-B cases**: source annotations, embedded images,
  vector graphics and attachments are outside reader B's examined feature set
  and are declared `unexamined` with a reason, per coverage least-preserving
  semantics — never silently dropped.

## Honest boundary

What this matrix does **not** establish: general document-interchange
conformance, PDF↔EPUB equivalence, OCR fidelity, or human-verified
interoperability. The `document-purpose` state machine stays at
`fixtures_tested` (or `scope_limited` for disputed cases); the
`independent_conformance_demonstrated` transition requires agreement evidence
beyond this machinery-only run.
