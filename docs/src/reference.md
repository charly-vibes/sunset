# Reference

Lookup index for the DSC corpus: deployed capability specs, the `dsc03`
machinery surface, conformance labels, and fixture inventory. Descriptive
only — no procedures here. Companion pages: [what-is-dsc.md](what-is-dsc.md)
(what this is), [first-descriptor.md](first-descriptor.md) (tutorial).

## Capability specs

Deployed truth lives under `openspec/specs/` — seven capabilities. Every
deployed spec carries the 0.3 updates from the archived change
`openspec/changes/archive/2026-10-14-add-dsc-03/`; the frozen 0.2 executable
(`spec/document-model-specodelic-v3/validator.py`) tests only the 0.2 core
and must keep rejecting 0.3 descriptors.

| Capability | Baseline | Scope (from the spec's Purpose) |
|---|---|---|
| [document-core](../../openspec/specs/document-core/spec.md) | 0.2 (revised by 0.3 delta) | Validates the typed structure of a DSC 0.2 document descriptor (JSON wire contract per the bundle's `CONTRACT-0.2.md`) and returns complete error reasons; canonical form is an RFC 8785-style subset. Reference implementation: `spec/document-model-specodelic-v3/validator.py`. |
| [document-structure](../../openspec/specs/document-structure/spec.md) | 0.2 (modified by 0.3 delta) | Separates physical containment from logical grouping and reading sequence: `view` is physical or logical, `realizes` links logical regions to several physical placements, `contains` is exclusive-parent ownership, `precedes` is a strict partial-order generating edge. |
| [document-semantics](../../openspec/specs/document-semantics/spec.md) | 0.2 (modified by 0.3 delta) | Retains typed, namespaced domain claims without reinterpreting the structural core; vocabulary registration is versioned; cross-edition equivalence is an optional, explicitly scoped comparison via a named projection and comparator. |
| [document-evidence](../../openspec/specs/document-evidence/spec.md) | 0.2 (modified by 0.3 delta) | Retains evidence, transformation fingerprints, and honest uncertainty: claim `origin` (source/extracted/inferred/manual/external), `asserted_without_evidence`, coexisting disputed claims, transformation lineage as a DAG. |
| [document-adapters](../../openspec/specs/document-adapters/spec.md) | added by 0.3 | Preserves declared source-native observations via an applicable adapter without OCR; adapter result is separate from document validity. Structured JSON is the mandatory baseline adapter; PDF native and EPUB adapter execution is not claimed. |
| [document-conformance](../../openspec/specs/document-conformance/spec.md) | added by 0.3 | Reports per-instance outcomes (`valid`, `invalid`, `unsupported`, `ambiguous`) separately from suite readiness (`passed`, `failed`, `incomplete`) and from Specodelic lint; the reference tests cover JSON descriptors only. |
| [document-ontology-boundaries](../../openspec/specs/document-ontology-boundaries/spec.md) | added by 0.3 | Ontology boundary rules for DSC 0.3: out-of-core semantics (relations beyond `contains`/`precedes`/`realizes`) are represented without silent coercion (acceptance checks O-A01, O-A04, O-A05); executable projection evaluator in `dsc03/boundaries.py`. |

## `dsc03` module surface

One line per module, quoted or condensed from its docstring.

### Consumer-facing

| Module | Docstring summary |
|---|---|
| `dsc03/validator.py` | "DSC 0.3 descriptor validator (not a PDF/EPUB extractor)." Implemented limits (resource_limit reporting): no size limits enforced yet; nesting depth is bounded by Python's JSON parser recursion limit, surfacing as `parse_error`, never as valid. |
| `dsc03/adapters.py` | "Real-carrier adapters: PDF/EPUB bytes -> 0.3 descriptors preserving source observations." |
| `dsc03/report.py` | "Separate schema / profile / source-coverage / interpretation reports." |
| `dsc03/conformance.py` | "Conformance labels: classify a suite; never overclaim." (See taxonomy below.) |
| `dsc03/evidence.py` | "Evidence replay: resolve the link, apply its anchors, report typed outcomes." |
| `dsc03/migrate.py` | "0.2 -> 0.3 migration with a loss-accounting report; nothing is invented." |
| `dsc03/boundaries.py` | "Boundary projection evaluator: O-A01, O-A04, O-A05; no silent coercion." |

### Reviewer / developer machinery

| Module | Docstring summary |
|---|---|
| `dsc03/profiles.py` | "Pinned profile resolution: a local registry supplies exact artifact bytes." |
| `dsc03/canonical.py` | "Canonical-byte readers: two independent implementations, one output." |
| `dsc03/projection.py` | "Pinned projection + comparator: match by anchors, retain alternatives." |
| `dsc03/corpus.py` | "Adversarial corpus builder + corpus gate (machinery-only)." |
| `dsc03/demo.py` | "First-consumer demo: pinned extractors, snapshots, projection, measurement." |
| `dsc03/coverage.py` | "Scoped coverage verification: inventories, manifests, dispositions, summaries." (support module feeding the reports above) |

Package docstring (`dsc03/__init__.py`): "DSC 0.3 validator package
(sunset-r68). Implements the add-dsc-03 capability deltas. The frozen 0.2
executable under `spec/document-model-specodelic-v3/` stays untouched and
must keep reporting PASS 11 descriptor fixtures."

## Conformance label taxonomy

Source of truth: `classify(suite)` in `dsc03/conformance.py`
("Honest conformance label classification … never overclaim"). Suite keys
(all optional, defaulting to False/0): `v02_fixtures`, `v03_schema`,
`v03_profiles`, `v03_coverage`, `migration`, `adversarial_corpus`,
`real_carriers`, `independent_readers` (int), `extractor_comparison`,
`anchor_mapping_reviewed`, `first_consumer_demo`, `native_output_baseline`,
`demo_result` (`functional_gates_passed`, `review_time_delta`).

### Claims emitted

| Label | Condition |
|---|---|
| `0.2 fixture coverage` | `v02_fixtures` truthy. |
| `0.3 contract validation` | all of `v03_schema`, `v03_profiles`, `v03_coverage` truthy. |
| `0.2-to-0.3 migration` | `migration` truthy. |
| `real-carrier conformance` | `real_carriers` truthy AND `adversarial_corpus` truthy AND `independent_readers >= 2` AND `extractor_comparison` truthy AND the missing list is empty. |

### Missing-list entries (why conformance stays incomplete)

| Missing entry | Produced when |
|---|---|
| `adversarial corpus` | `real_carriers` truthy but `adversarial_corpus` falsy. |
| `two independent readers` | `real_carriers` truthy but `independent_readers < 2`. |
| `declared extractor comparison` | `real_carriers` truthy but `extractor_comparison` falsy. |
| `reviewed anchor mapping` | `extractor_comparison` truthy but `anchor_mapping_reviewed` falsy — an unreviewed (machinery-only) mapping can never support conformance claims. |
| `real PDF/EPUB carrier fixtures` | no real carriers, but the 0.3 contract is validated or an adversarial corpus exists. |

### Workflow benefit

| Value | Condition |
|---|---|
| `unproven` | default — no `first_consumer_demo` or no `native_output_baseline`. |
| `traceability: demonstrated` / `speed: demonstrated` | demo present, `functional_gates_passed` truthy, `review_time_delta <= 0`. |
| `traceability: demonstrated` / `speed: not claimed` | demo gates pass but review time increased. |
| `traceability: failed` / `speed: not claimed` | demo present but functional gates failed. |

### Honest-claim boundaries (what can never be claimed)

- 0.2-fixture-only suites claim 0.2 coverage only.
- 0.3 contract suites without real carriers, the adversarial corpus, two
  independent readers, or a declared extractor comparison are `incomplete`
  and never claim real-carrier conformance.
- Workflow benefit stays `unproven` without the first-consumer demonstration
  and native-output baseline.
- Scripted persona annotations (author tags reader-A / reader-B,
  `fixtures/carriers/MANIFEST.org` "Annotation provenance caveat") are a
  machinery exercise; they are NOT conformance evidence.
- Demo time measurements are agent-executed time and must never be reported
  as human reviewer time (`fixtures/demo/review-agreement.org` deviation note).

## Fixture catalog

Fixture inventory with redaction and provenance rules is maintained in
`fixtures/carriers/MANIFEST.org` — that file is authoritative; this section
only indexes it.

### `tests/tracer/` — tracer suite inputs

- `fixture_minimal.json` — minimal DSC 0.3 descriptor (`tracer-minimal`):
  one page/paragraph/article region set, `contains`/`has-content`/`realizes`
  relations, one disputed manual annotation
  (`asserted_without_evidence`), one source-origin evidence entry.
- `profiles/` — pinned resolution profiles:
  `geometry-page-pt.json`, `inventory-pdf.json`, `inventory-pdf-short.json`,
  `inventory-epub.json`, `manifest-pdf.json`, `manifest-epub.json`,
  and selector-text profiles (`selector-text-bytes.json`,
  `selector-text-closed.json`, `selector-text-graphemes.json`,
  `selector-text-scalar.json`, `selector-text-scalar-v2.json`).

### `fixtures/carriers/` — real-carrier fixtures

Actual carrier files (inventory per `MANIFEST.org`):

| File | Features exercised |
|---|---|
| `agentic-patterns-excerpt.pdf` | glyphs, 276 link annotations (src) |
| `accounting-made-simple-excerpt.pdf` | glyphs, images, links (81 src) |
| `budgeting-basics-excerpt.pdf` | glyphs, dense images (305 src) |
| `diario-de-poesia-excerpt.pdf` | scanned image-only pages (36pp src) |
| `invoice-arca-redacted.pdf` | ARCA factura (text); QRs removed |
| `lab-result-redacted.pdf` | medical lab report, rasterized redaction |
| `bank-statement-ca-excerpt.pdf` | bank statement, bank name mocked |
| `bank-transfer-redacted.pdf` | transfer receipt, all parties mocked |
| `estado-deuda-abl-redacted.pdf` | gov debt constancia, address mocked |
| `cta-cte-propietario-redacted.pdf` | account ledger, names/CUIT mocked |
| `resumen-periodical-excerpt.pdf` | periodical demo issue: tables, p5->p6 continuation, scanned notice (p13 orig) |
| `sunset-carrier-sample.epub` | synthetic EPUB 3: manifest/spine/nav/svg |
| `sunset-carrier-sample-annotations.json` | CFI highlight/text sidecar for the EPUB |
| `reader-a-epub-annotations.json` / `reader-b-epub-annotations.json` | two disjoint CFI annotation sets for the EPUB |
| `reader-agreement.org`, `reader-b/` | reader-layer agreement analysis; reader-B layer carriers |

- **PII-screening rule** (per `MANIFEST.org`): all PDFs screened over full
  text, docinfo, XMP, annotation contents, and embedded-file scan; no CUIT/
  CUIL/DNI, CBU, account or reference numbers, real names, addresses, or bank
  names (redacted to MOCK values); no embedded attachments. Redaction uses
  real content removal (`add_redact_annot`), re-screened clean afterwards.
- Copyright caveat: excerpt carriers of published works are for local
  fixture testing only — do not redistribute or push to any public remote.
- **Preserved provenance, not test input**: the bundle under
  `spec/document-model-specodelic-v3/` is a preserved research artifact
  (validator deliberately frozen at 0.2); the executable tracer tests live in
  `tests/tracer/` and do not consume the bundle as fixture input.

### `fixtures/demo/` — first-consumer demo artifacts (sunset-r68.13)

- Demo issue: `reader-a-annotated.pdf`, `reader-b-annotated.pdf` — the two
  scripted reviewer layers annotating the pristine
  `fixtures/carriers/resumen-periodical-excerpt.pdf` (sha256
  `4317fca9fe017f3cc3088c7188ea54432b9ab8875c44b36eea6a6bd769012162`); layer
  details and region-agreement record in `review-agreement.org`.
- `measurement.json` — measurement sheet: pinned extractor versions
  (pdftotext 26.01.0, PyMuPDF 1.28.2, tesseract 5.5.3, spa, 200 dpi),
  projection pin (`sunset-common-projection` v1), oracle requirements
  (`page-text` required and allowed-unresolved), comparison results.
- `snapshots/` — pinned extraction snapshots with descriptor, inventory, and
  manifest per extractor: `snapshot-pdftotext/`, `snapshot-pymupdf/`.
