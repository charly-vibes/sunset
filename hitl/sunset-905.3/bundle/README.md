# Sunset 905.3 — independent reader bundle

**Ticket**: sunset-905.3 "Composition slice 3: real-carrier conformance + two
independent readers (HITL)" — epic sunset-9pf.

## What this bundle is

A self-contained package for **two independent human readers**. Each reader
receives an identical copy of this bundle and, working completely separately,
fills one **observation sheet per carrier**. The sheets are the readers'
independent canonical observations of four real carriers; the sunset
machinery later compares them into an agreement matrix with explicit
unknown/loss entries (no silent winner election).

Your observations are the **reference set**: they are recorded BEFORE any
extraction output is shown to anyone, and disagreements between the readers
are retained and classified — never resolved by picking a winner.

## Ground rules (independence contract)

1. **Work separately.** Reader A and reader B must not see each other's
   sheets, annotations, or notes until both are submitted. Do not discuss
   the carriers while filling the sheets.
2. **No extraction tooling.** Do not run pdftotext/PyMuPDF/OCR or any DSC
   code. Observe the carriers as a human reader: open the PDF/EPUB in a
   normal viewer and read.
3. **Record before interpretation.** Fill every sheet from what the carrier
   itself shows, citing evidence (page number, a quoted fragment, or an
   annotation) for each entry.
4. **"unknown" is an answer.** Where you cannot determine something, write
   `"unknown"` — that is a valid, classified outcome, never a failure.
   Likewise record anything you perceive as *lost* or *unrepresentable*
   under `losses` rather than omitting it.
5. **No smoothing.** If two readings seem possible (a table that could be
   two sections, a date that could be issue or publication date), record
   both as alternatives with your note; do not silently choose one.
6. **Time yourself** (stopwatch, per carrier). Record the minutes at the
   bottom of each sheet — reviewer effort is part of the measurement.

## Contents

| Path | Purpose |
|------|---------|
| `INSTRUCTIONS.md` | How to fill the observation sheets, field by field |
| `carriers/` | The four carriers (pristine copies, sha256 in `SHA256SUMS.txt`) |
| `templates/observations-spa.html` | **Easiest path:** open this file in a browser (works offline, `file://`); guided wizard that renders PDF pages itself (vendored pdf.js, offline) with fit/zoom under your control, lets you draw rectangles around the document's parts (type them as text/title/image/table…), times each carrier, and downloads the filled JSON |
| `templates/observations-template.json` | Copy one per carrier, rename, fill (fallback if you prefer editing JSON by hand) |
| `templates/agreement-matrix-template.md` | For the orchestrator, not the readers |

## How to return your work

“Resume a saved session” loads a previously downloaded
    `<carrier>.observations.json` — your recorded sections, drawn
    rectangles, page frames, and elapsed time come back, and you continue where
    you stopped (works across browsers and machines).

Using the SPA: it is a guided wizard — every screen tells you what to do next.
Start → choose your reader id and carrier → open the carrier in a normal viewer
alongside the form → follow the nine steps (one section each) → review,
**Build JSON**, **Download file** → “Mark carrier done”. Repeat for all four
carriers (the progress screen tracks it), then zip and send back as below.
The SPA lists soft warnings, not blockers.

Rename each filled sheet to `<reader-id>/<carrier-stem>.observations.json`
(e.g. `reader-a/diario-de-poesia-excerpt.observations.json`), zip your folder
including a `notes.md` with anything the sheets had no place for, and send it
back to the sunset owner. Do **not** commit to the sunset repo yourself.

The SPA is fully offline and self-contained (no network access, no server);
your draft is kept in your browser's local storage until you download it.
The independence contract is unchanged: the SPA only shapes your own
observations; it never sees the other reader's work.

### If a carrier does not display in the built-in viewer

Three ways in, in order: the built-in viewer → **Open in new tab ↗** (always
allowed, even over `file://`) → double-click the file in `carriers/`. Last
resort, serve the bundle from your own machine: open a terminal in the
unzipped bundle folder and run `python3 -m http.server`, then reopen the form
at `http://localhost:8000/templates/observations-spa.html` — everything
(embedding, drafts) then works with browser defaults. This is still fully
offline: nothing leaves your machine.

## Reader identities

Use the reader id you were assigned (`reader-a` or `reader-b`) on every file
and in the `reader` field of every sheet.
