# Visual oracles

Reference for the raster visual-oracle machinery (`dsc03/visual/`): what a
rendered-page comparison may and may not claim about extracted observations.
Companion pages: [reference.md](reference.md) (machinery index),
[integrate.md](integrate.md) (how results are recorded into reports),
[status.md](status.md) (machinery state and recorded deviations).

**Provenance.** The machinery is implemented under the active change
[`openspec/changes/add-raster-visual-oracles/`](../../openspec/changes/add-raster-visual-oracles/proposal.md)
— a proposal under implementation, **not deployed truth**; the deployed
capability specs under `openspec/specs/` are unchanged by it. Owner approval
was recorded 2026-11-02 in decision ticket `sunset-zo5` (beads): APPROVED,
with all nine rule-of-5 findings applied as amendments in commit `eeac8b0`;
the authorization scope is that change's tasks.md sections 3–7 only.
Every measurement, threshold and fixture behind this page is AGENT-EXECUTED
(coding agent, 2026-11-02/03); a human pass supersedes.

## What the oracles are

Two scoped properties over pinned PDF carrier pages:

- **`ink-coverage`** (`dsc03/visual/coverage.py`) — binarized ink fractions
  of claimed regions against recorded calibration bounds.
- **`region-alignment`** (`dsc03/visual/masks.py`) — claimed descriptor
  region rects, mapped through the declared frame, against the simplified
  source render.

The shared pipeline is: pinned render (poppler `pdftoppm`) → binarize under
the recorded threshold → map pixel↔descriptor coordinates through the
declared frame → compare against the one recorded calibration entry for that
carrier+page → typed per-page outcome (`agree` / `differ` / `unknown` /
`unavailable`). The pipeline never reads text: no OCR and no text extraction
happens anywhere in it.

## The oracle contract

One guarantee per requirement in the change's spec delta (a proposal, not
deployed truth — see the provenance note above):

| Contract requirement | What it guarantees |
|---|---|
| Pinned render configuration | Renderer name/version, DPI, page selection and binarization are recorded for every render; identical configurations reproduce byte-identical renders. A missing renderer yields a typed `unavailable` outcome, never a silent skip. |
| Declared frame mapping | Pixel↔descriptor coordinates resolve only through a declared geometry-profile frame. Missing, incompatible or ambiguous frames produce `unknown` — never `agree` or `differ`. |
| Labeled evidence class | Every result carries `correlated` or `independent`, derived from the render configuration's declared extractor/renderer lineages. |
| Scoped property claims | Each oracle evaluates exactly one property and carries it as a field on every outcome. A pass establishes nothing about text correctness, reading order, semantic grouping or visual completeness. |
| Mutation-validated sensitivity | A property may claim a defect class (shift, omission, duplication, wrong frame) only after seeded mutations on pinned carriers demonstrate detection of it. Undemonstrated properties stay `uncalibrated` and cannot gate any decision. |
| Calibrated thresholds with per-page outcomes | Thresholds come from recorded calibration over varied pinned carriers; outcomes are reported per page and per property. No aggregate reports pass while any page is `unknown` or `unavailable`, or its property is `uncalibrated`. |
| No silent resolution | Disagreements are retained and attributed to their source regions. No winner election, no smoothing, no mutation of extracted observations. |
| Distinct evidence class in demonstrations | Visual results are recorded separately from reader agreement, extractor comparison and reviewed anchor mapping, and never substitute for any of them. |

## Evidence-class rules

- **`correlated`** — the render shares the extractor's implementation
  lineage (e.g. a PyMuPDF render over a PyMuPDF extraction). It demonstrates
  **sensitivity only**: it SHALL NOT support accuracy claims
  (`dsc03/visual/render.py` `supports_accuracy_claim` encodes exactly this
  restriction).
- **`independent`** — render and extraction are distinct lineages. The
  committed calibration renders with poppler `pdftoppm` 26.01.0 at 72 dpi
  against PyMuPDF extraction, labeled `independent`; it may support scoped
  claims per the change's spec, subject to the remaining gates (calibration,
  declared frames).
- The label travels with the outcome, per page: every outcome entry records
  its `evidence_class`, and a report section mixing both classes is labeled
  `mixed`.

## Calibrated limits, stated honestly

Thresholds exist **only** for the carriers recorded in
[`fixtures/visual/calibration.json`](../../fixtures/visual/calibration.json)
(five: three real-carrier pages — native text, image-only scan, mixed — and
two synthetic strip rasters, one of them rotated). The record carries the
six calibration fields the change's design D6 names: properties, defect
classes exercised, carriers, per-page outcomes, thresholds with derivation
provenance, and the render configuration.

- Pages **outside the recorded set** have no threshold entry: the property
  is `uncalibrated` for them, the per-page outcome is `unknown` (typed
  reason), and the aggregate blocks. Nothing extrapolates.
- The committed faint fixture (`visual-strip-faint.pdf`) is **uncalibrated
  by design**: its strip is drawn in uniform gray 200, strictly lighter than
  the pinned threshold-128 binarization, so it measures identically to a
  blank page and no honest calibration window exists. Its outcomes are
  `unknown` and they block the aggregate. That is the documented behavior,
  not a gap — no outcome is faked and no window is weakened.
- A `differ` outcome is a retained disagreement with region attribution —
  not a diagnosis. An `agree` is a bounded measurement against one recorded
  window — not a certificate.

All thresholds and fractions in the record are AGENT-EXECUTED measurements
(recorded 2026-11-03 through the pinned render pipeline); a human pass
supersedes.

## Conformance inertness

Visual results are a **separate evidence class**, never a conformance input:

- `dsc03/visual/reports.py` `record(report, visual_results)` returns a new
  report dict carrying a distinct `visual_oracles` section: per-page
  outcomes with statuses passed through verbatim (`unknown`, `unavailable`
  and `uncalibrated` are never upgraded or dropped), the shared aggregate
  scalars, the section-level evidence class, and an explicit
  `non_substitution` note naming the conformance inputs the section does not
  provide (`real_carriers`, `independent_readers`, `extractor_comparison`,
  `anchor_mapping_reviewed`).
- `dsc03/conformance.py` `classify` never reads the section: conformance
  labels are provably inert to oracle outcomes. Passing oracles plus no
  independent readers leave the label `incomplete` — oracles cannot complete
  a suite.

See [integrate.md](integrate.md) Recipe 3 for the recording call.

## Where the machinery lives

- `dsc03/visual/` — render, frames, coverage, masks, reports.
- `tests/tracer/` — oracle, mutation and calibration test suites; strip and
  seeded-mutation rasters under `tests/tracer/fixtures/visual/`
  ([README.org](../../tests/tracer/fixtures/visual/README.org) documents the
  set; AGENT-EXECUTED fixtures, a human pass supersedes).
- [`fixtures/visual/calibration.json`](../../fixtures/visual/calibration.json)
  — the calibration record, the only source of thresholds.

## Honest boundary

What an oracle result never establishes: text correctness, reading order,
semantic grouping, visual completeness, extraction accuracy (for correlated
results), or OCR quality. The oracles complement — never replace — reader
agreement, extractor comparison and reviewed anchor mapping, and they never
change a conformance label. No accuracy, completeness or semantic claim
follows from an oracle pass anywhere in this machinery.
