# Reference regions scopes — schema v1 (sunset-rmx.23)

Status: implemented by `digitization/references.py` (`validate_verdicts`,
`validate_reference`, `verdicts_to_reference`); pinned by
`tests/tracer/test_digitization_references.py` with the first non-empty golden
example at `fixtures/digitization/reference-regions-golden.json`.

## Normative sources (derive from parsers, not prose)

- Verdict vocabulary: the review SPA's pinned `VERDICTS = ["agree", "differ",
  "unknown"]` (hitl/visual-review/templates/visual-review-spa.html,
  `buildVerdictJson`). Unknown is an answer, never a gap to be resolved.
- Regions-scope shape: the shared evaluate parser
  (`digitization/evaluation.py`): `reference.get('regions', [])` — a flat list
  across pages — fed to `match_regions(refs, cands, policy.region_iou_threshold)`,
  where each reference entry needs `bbox` `[x, y, w, h]`, `page` (int; IoU is 0
  across pages), and `id` (or `region_id`). This document describes that shape
  plus provenance keys the evaluator ignores.

## Artifact A — `review-verdicts.json` (input; SPA output + schema-v1 extension)

```json
{
  "reviewer": "string|null",
  "rules": "string",
  "carriers": [{
    "carrier": "descriptor id (string)",
    "pages": [{
      "page": "int|null (null: page number not derivable)",
      "unavailable": "string|null (typed reason; never silently dropped)",
      "regions": [{
        "id": "string (descriptor region id, verbatim)",
        "rect_px": "[x, y, w, h]|null (null: unknown frame, region kept)",
        "verdict": "agree|differ|unknown|null (null = unreviewed)",
        "note": "string",
        "correction_px": "[x, y, w, h]  (OPTIONAL schema-v1 extension)"
      }],
      "missed_ink": [{"rect_px": "[x, y, w, h]"}]
    }]
  }]
}
```

`correction_px` is the human's corrected truth rect for a `differ` verdict. The
SPA template is deliberately untouched (file://-safe contract): the field is
added after export, under this schema, or by a future SPA version. A `differ`
without `correction_px` is a recorded disagreement that yields no truth.
Rects must be finite numbers with positive width/height.

## Artifact B — reference-regions-scope v1 (converter output)

```json
{
  "version": "1",
  "kind": "reference-regions-scope",
  "source": {
    "carrier": "descriptor id",
    "reviewer": "string|null",
    "rules": "string|null",
    "descriptor_sha256": "sha256 of the run's descriptor.json",
    "verdicts_sha256": "sha256 of the verdicts file bytes",
    "frames": {"<page>": ["page render frame names, first-seen order"]}
  },
  "regions": [
    {"id": "…", "page": 1, "bbox": [x, y, w, h], "origin": "witness",
     "claim_bbox": "[x, y, w, h]  (counterexample entries only: the disputed extractor claim)"}
  ],
  "pages": [{
    "page": "int|null",
    "status": "partial|missing",
    "regions": "[truth entries as above] | null when status=missing",
    "witnesses": ["region ids whose entries have origin=witness"],
    "differed": [{"id": "…", "claim_bbox": [x, y, w, h], "correction_bbox": null}],
    "missed_ink": [{"id": "missed-ink-<page>-<n>", "page": 1, "bbox": [x, y, w, h],
                    "origin": "missed-ink"}],
    "unknown": [{"id"?: "…", "bbox"?: [x, y, w, h], "reason": "<typed reason>"}]
  }],
  "missing_pages": ["page numbers (or null) whose scope is missing"]
}
```

## Mapping (no silent resolution anywhere)

| Verdict / input                     | Result                                                              |
|-------------------------------------|---------------------------------------------------------------------|
| `agree` + valid rect                | truth entry, `origin: "witness"` (extractor≈human)                  |
| `differ` + `correction_px`          | truth entry, `origin: "counterexample"`, bbox = human correction, disputed claim kept in `claim_bbox` |
| `differ` without correction         | page `differed` entry, `correction_bbox: null` — excluded from truth (a disputed claim is never elected truth) |
| missed-ink box                      | truth entry, `origin: "missed-ink"` (human-only region)             |
| `unknown` verdict                   | page `unknown`, `reason: "reviewer-unknown"` — recorded, excluded from denominators |
| unreviewed (`verdict: null`)        | page `unknown`, `reason: "unreviewed"`                              |
| `rect_px: null`                     | page `unknown`, `reason: "unmapped-rect"`                           |
| `unavailable` page                  | all entries `unknown`, `reason: "page-unavailable"`                 |
| `page: null`                        | all entries `unknown`, `reason: "page-number-not-derivable"`        |
| descriptor page absent from verdicts| page scope `missing` (unreviewed pages stay visible, never implicit)|
| no truth on a page                  | `status: "missing"`, `regions: null` — MISSING scope (evaluation-incomplete), never a fabricated empty truth (an empty list is rejected by `validate_reference`) |

Top-level `regions` is the flat, evaluate-consumable scope: only entries from
`partial` pages, ready for `evaluate()`/`match_regions` in a follow-up wiring
test and for sunset-12h ingest. Conversion freezes per page-stage: `source`
digests pin descriptor and verdicts bytes, `frames` pins the page render
frames from the run's regions.json.

## Why conversion lives outside the SPA module

`dsc03/visual/review.py` stays a pure bundle builder so the offline file://
review contract is untouched and the UI never gains reference semantics:
resolution of disagreements is a data decision, not a UI behavior, and keeping
it server-side (this module) means neither the SPA nor the converter can
silently resolve an unknown — the schema has no representation for it. The
module lives in `digitization/`, next to the evaluate parser that normatively
defines the regions scope, avoiding shared-file co-modification of the SPA
template and review module.
