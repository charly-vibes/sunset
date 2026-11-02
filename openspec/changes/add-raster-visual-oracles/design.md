# Design: raster visual oracles

## Context

The October 2026 review (rule-of-5, verdict WITH NOTES) validated the
raster-comparison direction from the BORA-page prototypes while fixing its
claims: prototype metrics demonstrated sensitivity to a seeded 22 px shift,
not accuracy; extraction and rasterization shared PyMuPDF (correlated);
thresholds rested on one page; and frame mismatches could silently produce
wrong pass/fail results. The contract in the spec delta encodes those fixes.
This design records the implementation-shaping decisions.

## Decisions

### D1 — New capability, additive

A separate `document-visual-oracles` capability keeps the evidence-class rules
in one place and leaves document-conformance, document-adapters and the
digitization contracts untouched. Cross-references, not modifications: frame
mapping reuses document-adapters "Declared coordinate frames"; demonstration
integration reuses document-conformance reporting levels and reference-oracle
rules.

### D2 — Renderer independence strategy

The initial independent renderer is poppler `pdftoppm` (already a pinned
dependency of the first-consumer demo: pdftotext 26.01). Rendering with the
same library family as the extractor under test (e.g. PyMuPDF render for a
PyMuPDF extraction) is permitted but MUST be labeled `correlated`. Version,
DPI, page selection and binarization are recorded per render and must
reproduce byte-identical output.

### D3 — Representation levels

Four representation levels were prototyped in the source conversation:
(A) full-page render, (B) binarized ink mask, (C) geometry-only masks,
(D) semantic layout maps. Ship B and C first: they isolate layout/geometry
from glyph rendering. A remains a debugging tool. D is deferred until its
region labels come from independently validated sources (human sheets or the
debugger annotation contract) — labeling pages by learned heuristics would
reintroduce the correlated-evidence problem at the semantic level.

### D4 — Like-with-like comparison

A geometry-mask oracle must compare against a geometry simplification of the
source image, not raw glyph pixels: rectangles naturally cover whitespace
between glyphs, so naive mask-vs-pixels diffs produce misleading differences.
Each oracle defines its own source simplification (e.g. ink dilation for
coverage tolerance) and records it in the render configuration.

### D5 — Outcome vocabulary

Per page and per property: `agree`, `differ`, `unknown`. `unknown` covers
frame mismatch, unrenderable pages, insufficient resolution and missing
calibration — it never collapses to pass or fail. `differ` results are
retained with region attribution; no winner election, no smoothing, no
mutation of extracted observations (consistent with document-conformance
"Anchored matching without silent resolution").

### D6 — Calibration by seeded mutations

A property is `calibrated` only after a recorded run shows it detects each
defect class it claims (shift, omission, duplication, wrong frame) on pinned
carriers, with thresholds chosen from calibration data over varied pages
(native, scanned, mixed, rotated, faint). The prototype's single-page,
single-mutation result motivates this gate; uncalibrated properties cannot
gate any decision.

### D7 — Conformance labels unchanged

`dsc03/conformance.py` labels gain no visual-oracle inputs. Visual results
appear in demo/evaluation reports as a separate evidence class; suites that
lack independent readers, extractor comparison or reviewed anchor mapping stay
`incomplete` regardless of oracle outcomes.

## Risks

- Renderer drift: poppler upgrades change raster output; mitigated by pinning
  the renderer version in the configuration record.
- Threshold brittleness on degraded scans: mitigated by `unknown` outcomes and
  per-page reporting rather than corpus-wide aggregates.
- Scope creep toward visual completeness claims: explicitly out of scope;
  completeness remains a coverage-inventory concern.
