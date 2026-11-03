# Change: Add raster visual oracles for automated extraction validation

> **Status: PROPOSED — not approved.** No implementation is authorized by this
> document. This proposal records the validated direction from the October 2026
> raster-geometry review (source: cotorreo conversation
> `6ae4669e-fca4-83e9-92de-3a7a312d0c2e`; review verdict WITH NOTES).

## Why

Extracted observations are currently validated by descriptor rules, canonical
reader agreement and extractor-vs-extractor comparison — all of which share
implementation lineage with the extraction itself, and none of which look at
the rendered page. An independently rendered source page provides a different
evidence class: raster checks can confirm that extracted regions align with
visible ink, and seeded-mutation experiments (2026-10-30 BORA-page prototype)
demonstrated that a binarized ink/geometry-mask comparison detects an
introduced 22 px displacement (ink coverage 96.42% → 89.96%; prototype
numbers, unreproduced in-repo — the mutation gate below supersedes them with
in-repo demonstrations). The same review
established the limits: those prototype metrics proved sensitivity, not
accuracy — extraction and rasterization both used PyMuPDF, and no threshold was
calibrated across varied pages. Sunset needs a contract that captures what
raster comparisons may claim, how renders and coordinate frames are pinned, and
which checks must stay distinct from reader agreement and extractor comparison.

## What Changes

- Add a new `document-visual-oracles` capability defining raster-based
  validation oracles: pinned render configuration, declared frame mapping,
  labeled evidence classes (`correlated`/`independent`), scoped property
  claims, mutation-validated sensitivity, calibrated per-page outcomes
  (`agree`/`differ`/`unknown`/`unavailable`), no silent resolution, and a distinct evidence
  class in demonstrations.
- Reuse existing machinery: pinned extractors and `run_pinned` subprocess
  handling (`dsc03/demo.py`), declared geometry-profile frames
  (document-adapters), the pinned projection comparator (`dsc03/projection.py`),
  and the existing rendered-page oracle patterns (`dsc03/substrate/oracles.py`).
- Add oracle implementation, mutation fixtures and a calibration record for the
  first two properties (binarized ink coverage; geometry-mask alignment) as
  follow-on work gated by this contract — only after owner approval.

## Impact

- Affected capability: **new** `document-visual-oracles` (additive; cross-
  references document-adapters declared coordinate frames and
  document-conformance evidence classes).
- Expected code: a `dsc03/visual/` oracle module, mutation fixtures under
  `tests/tracer/fixtures/visual/`, calibration sheet, tracer tests. Reuse
  decisions precede new code; poppler (`pdftoppm`) is the initial renderer —
  independent of MuPDF-lineage extractors, correlated with pdftotext (poppler)
  extraction; PyMuPDF renders allowed but labeled `correlated`.
- Applicability: renderable page-based carriers (PDF). Formats the pinned
  renderer cannot rasterize (e.g. EPUB) are out of scope and report `unknown`,
  never silent absence.
- No DSC core wire changes, no frozen-validator changes, no OCR, no
  conformance-label changes (`dsc03/conformance.py` labels unchanged), no
  Bajan export, no universal image-similarity gate, no preserved-bundle edits.

## Success

A raster oracle run over pinned carriers reports per-page, per-property
outcomes with recorded render configuration, frame mapping, evidence class and
calibration status. Seeded shift/omission/duplication/frame-error mutations are
detected by the properties that claim them. Correlated results and
uncalibrated properties never gate any decision, and visual results never
substitute for independent readers, extractor comparison or reviewed anchor
mapping. No accuracy, completeness or semantic claim follows from an oracle
pass.
