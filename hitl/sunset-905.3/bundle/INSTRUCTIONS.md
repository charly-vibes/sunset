# How to fill an observation sheet

**Easiest path:** open `templates/observations-spa.html` in a browser — it
works fully offline (just a file, no server, no network), and it is a guided
wizard: every screen explains what to do and offers exactly one next step
(reader id → carrier → nine recording sections → review & download → progress
across the four carriers → zip-and-return instructions). The carrier itself is
shown at the top of the page in a built-in viewer (button **Show carrier**;
PDFs render natively in the browser — the built-in viewer counts as a normal
viewer; EPUB must be opened in an EPUB reader, as browsers cannot render it).
The field guide below is exactly what the wizard asks, section by section.

Manual path: copy `templates/observations-template.json` to
`<reader-id>/<carrier-stem>.observations.json` and fill every field. Read the
carrier in a normal PDF/EPUB viewer. The four carriers:

| Carrier | Class | What to pay attention to |
|---------|-------|--------------------------|
| `diario-de-poesia-excerpt.pdf` | scanned magazine (image-only) | pages with no text layer; what a viewer shows vs what can be selected/copied |
| `agentic-patterns-excerpt.pdf` | native PDF (born-digital) | selectable text, links, headings, section structure |
| `sunset-carrier-sample.epub` | reflowable EPUB | chapter/spine structure, how text reflows if you resize the window, internal links |
| `bank-statement-ca-excerpt.pdf` | financial statement | table rows, totals, what identifies the document (dates, account labels) |

## Field guide (all fields except `reader`, `carrier`, `elapsed_minutes` may be `"unknown"`)

- `reader`, `carrier`, `elapsed_minutes` — identity and effort.
- `page_inventory` — one entry per page/slide/spine item you can perceive:
  the `index` (1-based as shown by the viewer), whether it is
  `image_only` (nothing selectable) or `text`, and a ≤1-line `summary`.
- `structure` — the document's parts as a reader sees them: headings,
  sections, articles, table titles. On PDF carriers the SPA **renders the
  pages itself** (vendored pdf.js, still fully offline): pages fit to width
  or page, with working Zoom and real page counts — so rectangles you draw
  map exactly to page coordinates. The page frame calibrates itself
  automatically (the canvas is the page); press *Draw regions*, drag a
  rectangle around each part, pick its type (text, title, image, table…),
  and step through pages with *Prev/Next*. Each rectangle becomes an entry
  with `label`, `type`, `page`, `bbox` (page-relative drawn region — that
  is the evidence), and `order_rank` for reading order (the ↑/↓ arrows).
  If your browser blocks reading the local PDF (normal over `file://` in
  Chrome), press *Load the PDF file…* once and pick the carrier — or
  serve the bundle with `python3 -m http.server`. If two orderings seem
  defensible, record both in `order_alternatives`. On the EPUB (or "other"
  carriers) record parts by hand: `label`, `evidence` (page + quote),
  `page`, and `order_rank`.
- `relations` — cross-part relations you can observe:
  - `continuation`: a sentence/flow that continues from page N to page M
    (quote both fragments, `from`/`to`).
  - `reference`: a link, footnote anchor, or internal cross-reference
    (from where, to where).
- `space` — physical-layout facts a reader can state without measuring:
  per page: `rotation` (does the page display sideways/upside-down?),
  `columns` (single/multi, and whether a column interrupts the other),
  `reading_order_ambiguous` (true if layout makes order unclear).
- `context` — claims about the document's own context, each with evidence:
  `publication_date` (and whether it is the carrier's date or a date
  *described inside* the content — they are different things),
  `publisher_or_source`, `author_or_attribution`, and any
  `quoted_material` (a quotation inside the document attributed to someone
  else — record who is quoted and who quotes).
- `annotations` — annotations already visible in the carrier (highlights,
  notes, strikethroughs): type, page, the text they mark. (These are part
  of the carrier as shipped; record what you see, do not add your own.)
- `losses` — anything a structural record could not preserve: e.g. visual
  impressions, image content, typography, layout nuances, "the scan is
  skewed", "the table's shading carries meaning". One entry per loss with
  `what` and `why_unrepresentable`.
- `uncertainties` — every entry you were unsure about: the `field`, the
  `alternatives` you considered, and a one-line `reason`.
- `notes` — free text.

## Worked example (fictional, shows the shape)

```json
{
  "reader": "reader-a",
  "carrier": "diario-de-poesia-excerpt",
  "elapsed_minutes": 14,
  "page_inventory": [
    {"index": 1, "image_only": true, "summary": "magazine cover, masthead + cover photo"},
    {"index": 2, "image_only": true, "summary": "table of contents, two columns"}
  ],
  "structure": [
    {"label": "Table of contents", "evidence": "page 2, upper half", "order_rank": 1}
  ],
  "relations": [],
  "space": [
    {"index": 2, "rotation": "0", "columns": "two", "reading_order_ambiguous": true}
  ],
  "context": [
    {"kind": "publication_date", "value": "unknown",
     "evidence": "no legible date on any excerpt page", "status": "observed_absent"}
  ],
  "annotations": [],
  "losses": [
    {"what": "cover photo content", "why_unrepresentable": "image conveys mood, no text equivalent"}
  ],
  "uncertainties": [],
  "notes": ""
}
```

Rules of thumb:

- `status` on context entries: `observed` (you read it),
  `observed_absent` (you looked and it is not there), `unknown`.
- Every non-`unknown` value needs `evidence` you could point another human to.
- Do not infer: "looks like a table of contents" is fine as a `summary`;
  asserting a continuation you did not actually trace is not.
