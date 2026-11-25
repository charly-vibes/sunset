> *I scanned the menu options*
> *I did not have a choice*
> *I'd like to teach the world to sing*
> *But I do not have a voice*
>
> — A Sunset, PULP

# Status

**sunset** is **experimental**.

- Develops local source-linked extraction alongside the DSC specification corpus.
- Product direction: PDF → searchable text with source locations → inspection.
  The local PyMuPDF native baseline now retains word/line mappings, supports
  read-only inspection/resume and verified offline replay, and reports distinct
  native outcomes (`text-complete` / `text-with-gaps` / `no-text-read`) per the
  deployed [document-adapters](../../openspec/specs/document-adapters/spec.md)
  outcome requirements. OCR and visual completeness remain separate work. See
  [current commands](digitization.org).
- Orientation: [What is DSC and why](what-is-dsc.md) — the docs entry point.
- Frozen DSC 0.2 baseline — `spec/document-model-specodelic-v3/validator.py`
  (frozen at 0.2), `PASS 11 descriptor fixtures`.
- DSC 0.3 machinery is implemented (`dsc03/` package, tests under
  `tests/tracer/`, gate `just spec-check`). The 0.3 capability deltas were
  deployed to the openspec specs on 2026-10-15 from the archived change
  [`openspec/changes/archive/2026-10-14-add-dsc-03/`](../../openspec/changes/archive/2026-10-14-add-dsc-03/proposal.md)
  (8 deployed capabilities as of 2026-11-03, when `document-visual-oracles`
  deployed). No real-carrier conformance is claimed:
  `dsc03/conformance.py` labels remain honest and scoped.
- **Substrate gates (sunset-7hs, 2026-10-15):** the
  [restore-document-substrate](../../openspec/changes/restore-document-substrate/proposal.md)
  implementable tasks are executed: the six conceptual roles and nine design
  §4 laws are mapped onto deployed 0.3 entities with a
  satisfied/partial/missing table ([mapping.md](../../openspec/changes/restore-document-substrate/mapping.md));
  deterministic oracles (native PDF without OCR, EPUB spine/navigation,
  scanned-with-derived-OCR, hybrid coexistence, financial domain
  independence) and law checks with negative counterexamples run in the
  separate consumer harness `tests/substrate/` (machinery
  `dsc03/substrate/`); a second independent scripted reading path is measured
  ([conformance matrix](conformance-matrix.md) — machinery-level,
  agent-executed, NOT human review). Purpose/consumers/non-goals are now
  stated normatively in the [README](../../README.md#purpose-consumers-non-goals)
  without upgrading any conformance-claim language. No wire changes; the
  substrate spec deltas remain undeployed pending review; recorded
  expressivity findings live in mapping.md § "Unresolved expressivity
  findings".
- The first-consumer demo's pinned extractors originally reaped children
  via `os.wait4` before draining stdout — a pipe-buffer deadlock that hung
  the suite once page output exceeded the buffer (surfaced 2026-10-18
  during sunset-905.3 gate runs). Fixed by `dsc03.demo.run_pinned`
  (file-backed stdout, WNOHANG polling, hung child killed after timeout);
  regression tests in `test_first_consumer_demo.py::TestPinnedRunner`.
- The sunset-905.3 two-human-readers gate remains open: the reader-grok /
  reader-claude sheet sets returned via cotorreo were ingested as a labeled
  agent-executed agreement run (owner ruling b, 2026-10-18) — see
  `hitl/sunset-905.3/agreement-matrix-agent-run.md` (55 observables: 27
  AGREE, 14 COMPATIBLE, 8 UNKNOWN, 6 DISAGREE retained; a human pass
  supersedes).
- **openspec 1.x compatibility (sunset-rtl, 2026-10-19; completed
  sunset-hhy, 2026-10-21):** the whole corpus passes
  `openspec validate --all --strict` under the ratified pin
  @fission-ai/openspec@1.14.2. To satisfy 1.x's 500-character
  requirement-text limit, ten overlong deployed requirements were
  **editorially split** into multiple requirements (normative prose
  partitioned verbatim, sentence order preserved;
  `tests/test_spec_composition.py` now guards the splits by asserting each
  part set reproduces the archived body's prose verbatim). Recorded
  micro-deviations in the split prose (human pass supersedes): "Features
  absent from the source may be preserved" → "SHALL be preserved"
  (document-adapters, Absence and unavailability honesty) and "yield" →
  "SHALL yield" ×3 (document-evidence, Selector outcome codes) — modality
  strengthened, meaning unchanged; both flips were **reverted to the
  original archived wording on 2026-11-25** per owner ruling sunset-xlh.
  The revert left two split parts ("Absence and unavailability honesty",
  "Selector outcome codes") with SHALL-free bodies, which openspec 1.x
  strict rejects (body-keyword rule); the SHALL-bearing sentence directly
  preceding each in the archived body moved across the split boundary
  into the part (verbatim, order-preserving; no normative text added or
  dropped; `tests/test_spec_composition.py` guards these requirements
  against future modality drift). A few scenarios were
  restated as witnesses for newly standalone requirements.
- **Specodelic Revision 19 delta migration (sunset-hhy, 2026-10-21):** the
  original residual gap (dual-format deltas failing 1.x strict: the
  `## Requirements` mirror registered as orphaned requirements, the
  Constraints/Model/Properties tables as uncarried content) was resolved
  upstream when specodelic Revision 19 retired the dual-format delta class
  (charly-vibes/specodelic#20, change `add-delta-layer-sidecar`). All
  three active changes were migrated to the Revision 19 shape: each delta
  `spec.md` is now a plain openspec delta (`## Purpose` +
  `## ADDED Requirements`, no frontmatter/mirror/tables) and the
  specodelic layer moved to a sibling `layer.md` sidecar (id
  `<capability>.layer`, authored Constraints/Model/Properties preserved,
  cross-delta refs rewired to the `.layer` row ids). `spk lint`
  (0 issues, 8 delta files + 8 sidecars) and 1.x strict (`--all`, 10/10)
  both pass; `openspec@1.14.2` is now the ratified gate binary
  (`versions.ddl.toml`, folded into `just spec-check`).
- **Raster visual oracles (sunset-xzy, 2026-11-02/03):** implemented as
  scoped machinery and deployed 2026-11-03 into the
  [`document-visual-oracles`](../../openspec/specs/document-visual-oracles/spec.md)
  capability (archived from owner-approved change `add-raster-visual-oracles`,
  `sunset-zo5` ruling 2026-11-02; tasks.md sections 3–7 all done). Two
  properties only (`ink-coverage`, `region-alignment`), every outcome
  labeled `correlated`/`independent`, calibration bounded to the recorded
  carriers in `fixtures/visual/calibration.json` (the committed faint
  fixture is honestly uncalibrated → `unknown` → aggregate blocked), and
  conformance labels stay inert: visual results are recorded as a separate
  evidence class (`dsc03/visual/reports.py`) and never substitute for
  independent readers, extractor comparison or reviewed anchor mapping. No
  accuracy, completeness or semantic claims are made; all measurements,
  thresholds and fixtures are AGENT-EXECUTED (a human pass supersedes).
  Contract and limits: [visual-oracles.md](visual-oracles.md).
- Recorded deviations across the 0.3 work (each human pass supersedes):
  reviewer personas, reader annotations and review times in the
  [first-consumer demonstration](tracer-bullet.org) are agent-executed; the
  anchor-mapping review of record was agent-executed rule-of-5
  (TypeSafe-verified), accepted by the owner in sunset-r68.12; the
  documentation-suite review of record (sunset-msj.6) was likewise
  agent-executed — every runnable claim reproduces verbatim, links resolve,
  and the fixture catalog matches disk — with the same standing caveat:
  a human pass supersedes.
- Active openspec deltas include the review corrections; the preserved
  research draft is historical input where its details differ.
- Three proposed (not deployed) openspec changes are integrated as of
  2026-10-15, grounded and strictly validated against this checkout
  (`spk lint` 0 issues each; provenance in each change's `proposal.md`):
  [`restore-document-substrate`](../../openspec/changes/restore-document-substrate/proposal.md)
  (general purpose + categorical laws, additive) — **implemented at the gate
  level 2026-10-15 (sunset-7hs), see the substrate-gates bullet above**;
  [`define-document-composition-semantics`](../../openspec/changes/define-document-composition-semantics/proposal.md)
  (assembly/views/space/context laws, additive, depends on the former) and
  [`add-document-structural-debugger`](../../openspec/changes/add-document-structural-debugger/proposal.md)
  (read-only Sunset Lens debugger, optional consumer). No wire changes and no
  implementation are claimed; the proposals' conformance fixtures and
  second-reader gates are unexecuted and tracked in beads
  (sunset-7hs, sunset-905, sunset-xx7).
- The baseline's [known validation limitations](baseline-limitations.md)
  remain visible. The proposal composition regression checks specification
  replacement only, not 0.3 behavior.
- A repository-local Python digitization command exists. An installable product
  is not shipped; packaging remains outside the native-extraction proposal.

## Deviations from the fleet standardization checklist

**Current scope:** the owner selected a usable local extraction tool backed by
DSC as Sunset's product direction. The native PDF workflow is implemented under
`add-native-pdf-extraction`; the Python command also consumes recorded
observations. This direction does not claim a packaged release or authorize
publishing, deployment or fleet registration.

**Historical scope ruling (2026-10-15, `sunset-408`):** Sunset was scoped as a
specification corpus with external consumers, and tool-registry work was excluded.
The exclusions below describe the current checkout; they are not a prohibition
on delivering the extraction workflow. Packaging and fleet-registration work can
be scoped when there is a working product to distribute.

Other recorded deviations:

- **§1 distribution deviation (sunset-f06/sunset-mav, recorded 2026-11-24):**
  sunset ships Python source in this checkout only — no prebuilt GitHub Release
  assets, no published wheel or sdist, no package-manager entry. A user without
  a source checkout cannot install it today; the substitute install path is
  install-from-source (`git clone https://github.com/charly-vibes/sunset` +
  `uv sync`, then `uv run python -m digitization …` from the repository root),
  documented in the [README install section](../../README.md#install) and
  install/FAQ sections. This is the standardization §1 substitute-path record
  for the status-list note above that an installable product is not shipped.
- No CI workflow files (`just ci` arrives with an implementation; the spec
  gates run via `just spec-check` for now)
- No `book.toml`/theme or book pages
- No tool-registry `llm.txt`; [`llms.txt`](../../llms.txt) exists but serves
  documentation discovery only — it is not the tool-registration form the
  checklist assumes (same scope ruling as above)
- Not registered in ddl's registry, capability matrix, or dogfood matrix
- The research bundle's `specs/` were relocated to `openspec/` (single source
  of truth) — the recorded exception to "preserved as received" in the root
  [AGENTS.md](../../AGENTS.md)

## Acceptance gates for the 0.3 proposal

The bundle's [ACCEPTANCE.md](../../spec/document-model-specodelic-v3/ACCEPTANCE.md)
provides the original cases. The 0.3 requirements now live in the deployed
openspec specs (deployed from the archived add-dsc-03 change). The
[first-consumer demonstration](tracer-bullet.org) was executed 2026-10-15
(sunset-r68.13): 0 FP/FN against the reviewer oracle, R3/R5 correct only via
DSC — traceability benefit demonstrated; speed benefit not claimed.

## Tracer bullet (walking skeleton)

The 0.3 slice is implemented and green: descriptor → validate →
pinned profile resolve → evidence replay, plus adapters, coverage,
lineage/replay, reports, migration and honest conformance labels
(`dsc03/` package, full suite in `tests/tracer/`).
See [tracer-bullet.org](tracer-bullet.org) for the demo run and the
first-consumer workflow. The
frozen 0.2 validator stays untouched (PASS 11 descriptor fixtures).

## Native PDF extraction

The implemented native baseline extracts embedded text locally with PyMuPDF
1.28.2 and retains DSC, raw/search text, word/line maps, page frames and pinned
configuration. Its manifest declares semantic artifact hashes separately from
run context. Inspection verifies the retained source and mappings without
re-extraction; replay verifies and copies a native run offline. Scanned or
textless pages and unsupported/mixed page features remain partial or
unexamined. OCR, visual completeness and installable packaging are not part of
this baseline. Commands and exit statuses are documented in
[digitization.org](digitization.org).

## Geometry/render-binding baseline (agent-executed, 2026-11-24)

Re-measurement at HEAD before any implementation, from the RED tasks of
[`improve-geometry-render-binding`](../../openspec/changes/improve-geometry-render-binding/proposal.md)
(beads sunset-7b4.1). Both records are agent-executed and supersede the
2026-11-24 chat baseline (23/139 false word misses on a cropped fixture).

- **Variant matrix (tasks.md 1.1, test
  `tests/tracer/test_visual_variant_matrix.py`):** every PDF carrier in
  `fixtures/carriers/` (11 carriers) deterministically derived into rotation
  (0/90/180/270) and cropbox (30pt inset) variants at test runtime; native
  extraction run per variant; every native page-map frame resolved against a
  pinned `RenderConfig` via `resolve_pixel_mapping`. Outcome: 200 frames
  (carrier × variant × page) — **all 200 `unknown/unresolvable_source_scope`**,
  because native page-map records carry `source_frame`/`target_frame`/
  `source_to_page`/`source_origin`/`source_dimensions` but not the declared
  `source_scope`/`origin`/`axes`/`scale`/`rotation`/`crop` fields. No
  carrier×variant produced zero frames — the image-only carriers
  (`diario-de-poesia-excerpt.pdf`, `lab-result-redacted.pdf`) still yield one
  page-map frame per page; `resumen-periodical-excerpt.pdf` yields 5 frames
  per variant (page 1 aligner-fails on every variant, `text-with-gaps`).
  Suite green with the strict xfail honored.
- **Cropped-page oracle word-miss path (tasks.md 1.2):** carrier
  `fixtures/carriers/budgeting-basics-excerpt.pdf` (3 pages, 405 extracted
  words), cropbox = mediabox inset by 30pt on each side (e.g. page 1:
  crop 30,30 → 402,618 of media 0,0 → 432,648), saved deterministically with
  pymupdf. Rendered through the independent poppler path
  (`dsc03/visual/render.py`, `pdftoppm` 26.01.0, 150 dpi — renders the media
  box, no `-cropbox`); each word's cropbox-relative box mapped as the HEAD
  machinery would (no crop knowledge) and binarized ink presence evaluated
  per word (fixed threshold 128, 1px ink dilation). **False word misses:
  158/405** (page 1: 55/127, page 2: 61/165, page 3: 42/113); the uncropped
  carrier measures 0 misses under the identical pipeline, isolating the
  crop-box disagreement. This is the false-disagreement that tasks 2.1–2.3
  (crop-box render, extent binding, native frame record) must drive to zero.

## Geometry/render-binding re-measurement at the fix HEAD (agent-executed, 2026-11-24)

Same procedure as the RED baseline above, re-run at the fix HEAD (tasks 2.1–2.3
landed: crop-aware `pdftoppm -cropbox` render, extent binding, declared native
frames) through the fixed machinery (`resolve_pixel_mapping` + pinned
`RenderConfig` with `render_cropbox`, threshold 128, 1px ink dilation), agent
throwaway script, superseding the RED false-miss record.

- **Outcome: 0/405 false word misses counted — every run is a typed refusal.**
  Cropped and uncropped alike, all 3 pages of
  `budgeting-basics-excerpt.pdf` are refused by the extent binding with
  `page-extent-mismatch` (rendered 901×1351 / cropped 776×1226 vs declared
  900×1350 / 775×1225 at 150 dpi): poppler `pdftoppm` rounds page dimensions
  **up** (ceil of `pt·dpi/72`), while the declared extent binding uses
  `round`. The oracle therefore never silently counts cropped-page words —
  the RED disagreement path is closed with a typed unknown instead.
- **New observation (owner-flag candidate, recorded 2026-11-24):** this
  carrier's point dimensions are non-integral (432.063×648.063 pt); for such
  carriers ceil ≠ round at *every* dpi, so a native frame from
  `budgeting-basics` cannot bind through `pdftoppm` at any resolution —
  crop or no crop. Crop-correct binding on integral-dimension carriers is
  proven by the suite (`test_extent_binding_end_to_end_crop_and_rot_crop`);
  whether the binding rule should adopt the renderer's ceil convention is an
  owner ruling, not an agent change.

## Identity §5.4: native identity-descriptor byte-identity across two processes (agent-executed, 2026-11-24)

- **Run:** for each of the 11 carriers in `fixtures/carriers/`,
  `python -m digitization native --source <carrier> --output <tmp>/run` was
  executed twice, each invocation a separate OS process writing a fresh
  directory; the two `descriptor.json` files were compared byte-for-byte
  (identity ids derive from declared anchors — deployed scenario
  "Independent derivation"). Comparison scope is the descriptor only: sibling
  run artifacts (word-map, line-map) are outside this record and still carried
  float geometry at run time — the quantization adoption that post-dates this
  run is identity task 5.5.
- **Outcome: 11/11 byte-identical.** Descriptor sha256 prefixes per carrier:

  | carrier | status | descriptor sha256 (both runs) |
  |---|---|---|
  | accounting-made-simple-excerpt.pdf | text-with-gaps | b12f370af5c1fcac |
  | agentic-patterns-excerpt.pdf | text-complete | 1c0df55d43b5a14a |
  | bank-statement-ca-excerpt.pdf | text-complete | 5549f29b3e945a05 |
  | bank-transfer-redacted.pdf | text-complete | 0e810898cbd9115b |
  | budgeting-basics-excerpt.pdf | text-complete | c91af76f89464c52 |
  | cta-cte-propietario-redacted.pdf | text-complete | 07c2fdcd0ea927ed |
  | diario-de-poesia-excerpt.pdf | no-text-read | 77b929477ae6daf7 |
  | estado-deuda-abl-redacted.pdf | text-complete | 2d83563fe9f172a4 |
  | invoice-arca-redacted.pdf | text-complete | 5c5ed13c624c3313 |
  | lab-result-redacted.pdf | no-text-read | 3ebc45bf8c3425ed |
  | resumen-periodical-excerpt.pdf | text-with-gaps | 309d55d0ddaa42fd |

  Image-only carriers (`diario-de-poesia-excerpt.pdf`,
  `lab-result-redacted.pdf`) still emit page-map-only identity descriptors.
- **Harness notes (pre-existing CLI defects, ticketed sunset-qdy):**
  `--pages all` is rejected ("comma-separated integer PDF indices") and a
  pre-created output directory is refused (`output-already-exists`); the run
  omitted `--pages` and used non-existent `<tmp>/run` paths.

## Render-binding §3-§4 + identity §5.5 review fixes (agent-executed, 2026-11-24)

- **Correlated-render gate (tasks.md 3.1):** RED captured at HEAD — oracle
  evaluation accepted a correlated render config (failed only via a renderer
  error, no typed refusal). Now `dsc03/visual/review.py` refuses correlated
  configs up front with a typed `unavailable` outcome
  (`CORRELATED_RENDER_REFUSED: evaluation reads only independent renders…`),
  before any pixels exist; the carrier entry still records
  `evidence_class: "correlated"`. Deployed scenario "Review crop never feeds
  an oracle" pinned in `tests/tracer/test_visual_lineage_gate.py`.
- **Path labeling (tasks.md 3.2):** `digitization/render.py` outputs now carry
  `extractor_lineage`/`renderer_lineage`/`evidence_class` (always
  `correlated`: pymupdf render + pymupdf extraction share lineage), reusing
  `dsc03.visual.render.evidence_class` as the single rule source. Pixel bytes
  unchanged (page-1 PNG md5 identical before/after: `99e7ae7e8597552ad3373ad014fb46f5`).
- **Quantization adoption (identity tasks.md 5.5):** native word/line maps now
  carry integer operative geometry — `box` quantized once at extraction
  (1/1000 pt, round-half-even via `quantize_scalar`); line boxes derive from
  quantized word boxes. Verified on `budgeting-basics-excerpt.pdf`: 405 word +
  130 line boxes, 0 non-integer operative coordinates. The raw extractor box
  is retained as `source_box` (declared provenance; inspection re-derives and
  re-snaps from it — exact comparison, tolerance not loosened). The
  quantization transform record is written per run to `carrier/quantization.json`
  (quantum/rule/extractor version) and picked up by the manifest artifact
  scan. Descriptor bytes unchanged by the adoption (byte-compared HEAD vs
  working tree). RED evidence: word-map boxes float at HEAD, transform record
  absent, cross-run word-map bytes differed — all three captured before the fix.

### Review-fix round (rule-of-5, same day, agent-executed)

- **Structured refusal + single render site (CORR/CLAR):** the correlated
  refusal now also carries a machine-readable `record["refusal"] =
  {code, reason}` next to the prefixed display string, and "a correlated
  config never invokes a renderer" is stated once in `_maybe_render`
  (`dsc03/visual/review.py`), used by all three render sites.
- **Shared pixel module (EXCL-001):** decode/binarize/dilate machinery
  extracted from `coverage.py` (duplicated in `masks.py` and
  `content_classes.py`) into `dsc03/visual/_pixels.py` with public names
  (`decode_grayscale`, `ink_table`, `parse_dilation`, `dilate`,
  `comparison_mask`) and a `MaskUnavailable` typed failure; the three
  consumers share it and `pymupdf` is imported only there.
- **Non-finite geometry refused at extraction (EDGE-001):** `quantize_scalar`
  rejects NaN/±inf with `ValueError`; `digitization/native.py` converts that
  into the existing typed vocabulary
  (`NativeInputError('malformed-pdf', 'extraction produced non-finite word
  geometry')`) instead of crashing mid-run. Word/line geometry red test pinned
  in `tests/tracer/test_native_quantization.py` /
  `test_space_quantization.py`.
- **Shared test builders (EXCL-002):** the pinned poppler `RenderConfig`
  builder and synthetic-carrier builder, duplicated across four oracle
  suites, moved to `tests/tracer/conftest.py` together with the shared
  `CARRIERS` path constant; mapping-only suites keep their deliberately
  fake-pinned local configs.
- **G6 boundary amendment (CORR-001):** MuPDF block numbers restricted to
  oracle/containment statistics; identity `locator_path`s keep
  page/transform-granular anchors absent a selector-profile delta
  (`add-scale-complete-regions/design.md` Open Questions).
- **GREEN re-measurement (CORR-002):** recorded in the
  "re-measurement at the fix HEAD" section above — typed refusals everywhere,
  0/405 silent false counts; new owner-flag candidate filed for the
  ceil-vs-round extent convention (sunset ticket).
- **Region-table size measurement (add-scale-complete-regions task 3.3,
  agent-executed 2026-11-24):** native extraction of
  `fixtures/carriers/agentic-patterns-excerpt.pdf` (the carrier whose HEAD
  line map is the 421-line / 155 KB baseline quoted in
  `add-scale-complete-regions/proposal.md`) with manifest version 3. The
  descriptor region table — word/line/block regions plus their interval+box
  selectors, 8,703 words / 421 lines / 29 blocks — serializes to
  6,072,829 bytes (192,214 JSON lines); the full `descriptor.json` is
  7,740,879 bytes (248,163 lines). Byte-identity of the regenerated
  `line-map.json` and `page-map.json` exports was verified on this carrier.
  The descriptor region table is roughly 38x the HEAD line-map baseline, so
  the deferred dense columnar encoding (task 3.4) now has a measured size
  signal against its "hurts gate runs or review crops" trigger; the decision
  remains with the owner, and 3.4 stays unticked.
