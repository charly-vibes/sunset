# Evidence-to-decision ledger — 2026-10-13

The following are design decisions based on comparative research; links are public sources and do **not** constitute tests of DSC.

| Evidence / precedent | Risk | Requirement | Disposition |
|---|---|---|---|
| [Docling document model](https://github.com/docling-project/docling/blob/main/docs/concepts/docling_document.md) | tree order conflated with reading order | named views + explicit order interpretations | proposed v0.3 |
| [METS](https://www.loc.gov/standards/mets/) and [ALTO](https://www.loc.gov/standards/alto/) | physical/logical structure confusion; coordinate ambiguity | independent trees + coordinate frames | proposed v0.3 |
| [GROBID coordinates](https://github.com/grobidOrg/grobid/blob/master/doc/Coordinates-in-PDF.md) | semantic fragment cannot be found in PDF | typed selectors + alignment profile | proposed v0.3 |
| [PyMuPDF text extraction](https://pymupdf.readthedocs.io/en/latest/app1.html) | natural reading order and string identity are not guaranteed | retain source observations + order hypotheses | proposed v0.3 |
| [EPUB 3.3](https://www.w3.org/TR/epub-33/) | spine, nav, links, pages differ | registered carrier profile, no invented geometry | proposed v0.3 |
| [IIIF Presentation 3](https://iiif.io/api/presentation/3.0/) | OCR overlay confused with source image | addressable observed layers | proposed v0.3 |
| [Unstructured PDF strategies](https://docs.unstructured.io/open-source/core-functionality/partitioning) | extraction may be partial or require fallback | adapter coverage manifest | proposed v0.3 |

**Assumptions:** JSON wire-format continuity is valuable; portability over all source formats is not required in one core schema; source selectors are meaningful only with a registered interpretation profile. **Unknown:** best profile grammar, minimum useful geometry primitive, comparative extraction accuracy, implementation cost, and real-corpus conformance. Do not treat a cited project's engineering choice as proof it is universally correct.

## Ontology boundary clarification (2026-10-13)

DSC is a document-structure substrate rather than a universal semantic ontology. The gap inventory, counterexamples, mapping obligations and conditional fidelity claims are in [ONTOLOGY-BOUNDARIES.md](ONTOLOGY-BOUNDARIES.md). W3C RDF/OWL/JSON-LD, TEI, IIIF, METS/ALTO and EPUB are interoperability reference points, not tested DSC mappings.
