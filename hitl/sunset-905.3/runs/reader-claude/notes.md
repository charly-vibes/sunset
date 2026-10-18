# Notes — reader-claude (AI reader)

## Deviations from the bundle's protocol (please read before comparing)

1. **Not a human reader.** These sheets were filled by Claude (an AI model), not by a human using a normal viewer. The bundle is designed for two independent *human* readers, so this set should not be counted as one of them without a decision from the sunset owner.
2. **Reader id.** No id (reader-a / reader-b) was assigned to me. I used `reader-claude`; rename if needed.
3. **Not independent of the shipped annotations.** The PDFs carry sticky notes and highlights by "reader-A" with "ES:" notes (bank, agentic-patterns, diario p.1). The instructions treat annotations as part of the carrier, so I recorded them, but I read their text (via a PDF library) before writing my sheets. Their wording (e.g. folio numbers, "no text layer", "78-character text layer") may have shaped my observations. I did not copy claims I could not see myself; where I only have their claim I said so in `uncertainties`.
4. **Tooling.** I rendered PDF pages to PNG images and looked at them; I did not run pdftotext/OCR. I used a PDF library only to read annotation contents and page rotation flags, and I read the EPUB's XHTML/OPF files directly instead of using a reflowing viewer.
5. **Elapsed time.** I had no stopwatch, so `elapsed_minutes` is `null` on every sheet.
6. **image_only** is `"unknown"` for the PDFs: I never tested whether text can be selected.
7. **Diario de Poesía:** I read headlines, bylines and the Sumario carefully, and only skimmed body text and agenda listings.

## Things the sheets had no good place for

- Checksums: `SHA256SUMS.txt` lists bare filenames, so `sha256sum -c` fails from the bundle root; run it from inside `carriers/`. All five checksums match.
- `templates/agreement-matrix-template.md` was not opened or used (orchestrator-only, per README).
- The diario cover has an archival-photo nude portrait; recorded only as a photograph under `losses`.
