---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-c0v-ceil-extent-binding, pipeline-step:orient]
---

ORIENT: sunset-c0v ceil extent binding. bd ready item sunset-c0v (rule-of-5 GREEN re-measurement 2026-11-24): pdftoppm renders ceil(pt*dpi/72) px (verified in poppler utils/pdftoppm.cc savePageSlice) while dsc03/visual/frames.py resolve_pixel_mapping used round(); carrier budgeting-basics-excerpt.pdf (432.063x648.063pt CropBox verified) can never bind via poppler - page-extent-mismatch at every dpi. Owner ruled 2026-11-25 option A: binding adopts ceil. Scope: frames.py comparison + convention comments, improve-geometry-render-binding/design.md wording, variant-matrix ground-truth helper. Out of scope: e2e dpi=72 pinning, certificates, tolerance option B, document option C.
