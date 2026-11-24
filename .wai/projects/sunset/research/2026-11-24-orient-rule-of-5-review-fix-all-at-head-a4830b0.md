---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:orient]
---

ORIENT: rule-of-5 review "fix all" at HEAD a4830b0.
Fix set: (1) CORR-001 G6 locator-boundary sentence in add-scale-complete-regions/design.md; (2) CORR-002 cropped-page oracle GREEN re-measurement into docs/src/status.md; (3) CORR-003 bd hygiene: dep edges 12h<-3oq, f06<-mav, 2uo<-doc; owner-gate labels on 5ay/sc3/xlh/elx; sunset-7b4 stale 23/139 description fix; .beads/issues.jsonl export refresh; (4) CLAR-001 structured refusal field {code, reason} in dsc03/visual/review.py _page_record (unavailable keeps display string for SPA); (5) CLAR-002 covered by owner-gate label; (6) EDGE-001 finite guard in substrate/space.py quantize_scalar + typed NativeInputError wrap in digitization/native.py; (7) EXCL-001 dsc03/visual/_pixels.py extraction done pre-start, behavior-preserving, pinned by existing oracle tests; (8) EXCL-003 _maybe_render helper in review.py; (9) EXCL-002 shared fixtures to tests/tracer/conftest.py.
Deviation: _pixels.py + import swaps landed before pipeline start; recorded here.

