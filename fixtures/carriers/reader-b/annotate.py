"""Reader-B (Ing. Rafa Quiroga) annotator: 2 annotations per PDF, skeptical QA persona."""
import os
import pymupdf

AUTHOR = "reader-B"
FILES = [
    "accounting-made-simple-excerpt.pdf", "agentic-patterns-excerpt.pdf",
    "bank-statement-ca-excerpt.pdf", "bank-transfer-redacted.pdf",
    "budgeting-basics-excerpt.pdf", "cta-cte-propietario-redacted.pdf",
    "diario-de-poesia-excerpt.pdf", "estado-deuda-abl-redacted.pdf",
    "invoice-arca-redacted.pdf", "lab-result-redacted.pdf",
]

def is_image_only(doc):
    return all(len(p.get_text()) == 0 for p in doc)

def densest_band(page, bands=12):
    """Return (y0, y1) in page coords of the darkest horizontal band."""
    pix = page.get_pixmap(matrix=pymupdf.Matrix(0.25, 0.25), colorspace=pymupdf.csGRAY)
    w, h, n = pix.width, pix.height, pix.n
    samples = pix.samples
    counts = [0] * bands
    for y in range(h):
        band = min(bands - 1, y * bands // h)
        row = samples[y * w * n:(y + 1) * w * n]
        counts[band] += sum(1 for v in row if v < 128)
    best = max(range(bands), key=lambda i: counts[i])
    y0 = page.rect.height * best / bands
    y1 = page.rect.height * (best + 1) / bands
    return y0, y1, counts[best]

def save(doc, src):
    tmp = src.replace(".pdf", ".annotated.pdf")
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, src.replace(".pdf", ".annotated.pdf"))

def tag(annot):
    annot.set_info(title=AUTHOR)
    annot.update()

def text_pdf_job(doc, strike_rects, note, note_pos):
    page = doc[note_pos["page"]]
    a = page.add_strikeout_annot(strike_rects)
    tag(a)
    p2 = doc[note_pos["page"]]
    r = note_pos["rect"]
    f = p2.add_freetext_annot(
        r, note, fontsize=7, text_color=(0, 0, 0),
        fill_color=(1, 1, 0.85), align=0)
    tag(f)
    p2.parent.xref_set_key(f.xref, "BS", "<< /W 0.7 /S /S /C [ 0.55 0 0 ] >>")  # bordered note

def image_pdf_job(doc, note, page_idx=0):
    page = doc[page_idx]
    y0, y1, density = densest_band(page)
    W = page.rect.width
    x0, x1 = W * 0.15, W * 0.85
    yc = (y0 + y1) / 2
    pts = [(x0, yc), (W * 0.45, yc - (y1 - y0) * 0.35), (W * 0.65, yc + (y1 - y0) * 0.35), (x1, yc)]
    ink = page.add_ink_annot([pts])
    tag(ink)
    tp = pymupdf.Point(W * 0.55, page.rect.height * 0.12)
    t = doc[page_idx].add_text_annot(tp, note, icon="Note")
    tag(t)

def freetext_rect(anchor, page, w=250, h=52, dy=6):
    r = anchor
    rect = pymupdf.Rect(r.x0, r.y1 + dy, r.x0 + w, r.y1 + dy + h)
    pr = page.rect
    if rect.y1 > pr.y1 - 5:
        rect = pymupdf.Rect(r.x0, max(pr.y0 + 5, r.y0 - h - 6), r.x0 + w, max(pr.y0 + 5, r.y0 - h - 6) + h)
    rect.x0 = max(rect.x0, pr.x0 + 5)
    rect.x1 = min(rect.x1, pr.x1 - 5)
    return rect

NOTES = {
    "accounting-made-simple-excerpt.pdf":
        "RQ: Endnote 2 flows one word per line with giant gaps; line rebuilders will join 'Just a reminder Sample' wrongly and corrupt endnote text.",
    "agentic-patterns-excerpt.pdf":
        "RQ: Reference URLs hard-wrap mid-token ('strea'/'ming'); line-based extractors emit broken links and split hostnames in references.",
    "bank-statement-ca-excerpt.pdf":
        "RQ: Header splits 'Resumen' / 'al 21/09/2017' with stray spaces; balance 1.234,56 is ambiguous (thousands vs decimal) for dot/comma parsers.",
    "bank-transfer-redacted.pdf":
        "RQ: 79-hyphen rule extracts as a plain text line; naive parsers log it as content and field anchors near the reference block get lost.",
    "budgeting-basics-excerpt.pdf":
        "RQ: Running footer '&' and bare '209' pollute the flow; exhibit tables ship headers with no data rows, so parsers emit label-only records.",
    "cta-cte-propietario-redacted.pdf":
        "RQ: Final row '...por $ 115' truncates at the page edge and resumes on page 2; split rows plus out-of-order dates break balance replay.",
    "estado-deuda-abl-redacted.pdf":
        "RQ: Label 'Puerta alter:' is truncated and 'fisica' lost its accent; emission dated 16/06/2026 is future-dated; zero-filled fields invite false hits.",
    "invoice-arca-redacted.pdf":
        "RQ: FX rate 1488.500000 floats detached from its sentence; USD/ARS amounts are scattered, so label-value pairing can attach the wrong total.",
    "diario-de-poesia-excerpt.pdf":
        "RQ: Pure bitmap scan, zero text layer on every page; extraction is 100% OCR-dependent and margin handwriting will be silently lost.",
    "lab-result-redacted.pdf":
        "RQ: No text layer at all; values like hemoglobin or glucose exist only as pixels, so un-OCR'd ingestion returns an empty document.",
}
for k, v in NOTES.items():
    assert v.startswith("RQ:") and len(v) <= 180, (k, len(v))

# ---- text PDFs ----
jobs = []

d = pymupdf.open(FILES[0]); p = d[5]
r1 = p.search_for("Just")[0]; r2 = p.search_for("reminder:")[0]
jobs.append((FILES[0], d, pymupdf.Rect(min(r1.x0, r2.x0), r1.y0, max(r1.x1, r2.x1), r1.y1),
             {"page": 5, "rect": freetext_rect(r2, d[5])}))

d = pymupdf.open(FILES[1]); p = d[4]
r = p.search_for("advanced-features/strea")[0]
jobs.append((FILES[1], d, r, {"page": 4, "rect": freetext_rect(r, d[4])}))

d = pymupdf.open(FILES[2]); p = d[0]
r1 = p.search_for("SALDO ANTERIOR")[0]; r2 = p.search_for("1.234,56")[0]
jobs.append((FILES[2], d, pymupdf.Rect(r1.x0, r1.y0, r2.x1, r1.y1),
             {"page": 0, "rect": freetext_rect(r1, d[0], dy=16)}))

d = pymupdf.open(FILES[3]); p = d[0]
r = p.search_for("- - - - - - - - - - - -")[0]
r = pymupdf.Rect(p.rect.x0 + 5, r.y0, p.rect.x1 - 5, r.y1)
jobs.append((FILES[3], d, r, {"page": 0, "rect": freetext_rect(r, d[0], h=46)}))

d = pymupdf.open(FILES[4]); p = d[0]
r = p.search_for("209")[0]
jobs.append((FILES[4], d, r, {"page": 0, "rect": freetext_rect(r, d[0], dy=12)}))

d = pymupdf.open(FILES[5]); p = d[0]
r = p.search_for("$ 115")[-1]
jobs.append((FILES[5], d, r, {"page": 0, "rect": freetext_rect(r, d[0], h=46, dy=5)}))

d = pymupdf.open(FILES[7]); p = d[0]
r = p.search_for("Puerta alter")[0]
jobs.append((FILES[7], d, r, {"page": 0, "rect": freetext_rect(r, d[0], dy=14)}))

d = pymupdf.open(FILES[8]); p = d[0]
r = p.search_for("1488.500000")[0]
jobs.append((FILES[8], d, r, {"page": 0, "rect": freetext_rect(r, d[0], h=46, dy=5)}))

for name, doc, rects, note_pos in jobs:
    text_pdf_job(doc, rects, NOTES[name], note_pos)
    save(doc, name)
    print("annotated:", name)

# ---- image-only PDFs ----
for name in (FILES[6], FILES[9]):
    d = pymupdf.open(name)
    assert is_image_only(d), name
    image_pdf_job(d, NOTES[name])
    save(d, name)
    print("annotated (image-only):", name)

print("ALL PDFS DONE")
