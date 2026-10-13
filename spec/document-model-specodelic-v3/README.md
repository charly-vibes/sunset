# Document Structural Core — DSC 0.3 specification proposal

## TL;DR

Build on the executable **DSC 0.2** baseline while addressing the failure modes found in comparative document-model research: multiple structural views, incompatible reading orders, source-addressable text/layout, explicit normalization lineage, and honest extraction coverage. The **0.3 contract is a design proposal, not an implemented extractor or validator**.

## Provenance

- Agent/model: OpenAI GPT-6; generation date: 2026-10-13.
- Primary input: user-uploaded `document-model-specodelic-v2(1).zip` (copied baseline specs and test fixtures).
- Comparison: Docling, METS/ALTO, GROBID/TEI, PyMuPDF/PDFBox, EPUB 3.3, IIIF, Unstructured/Adobe, with links in [RESEARCH-DECISIONS.md](RESEARCH-DECISIONS.md).
- Repository commit: UNKNOWN (no commit pin supplied); document bundle is not a Git commit.
- Original six Specodelic capability specs preserved and amended with explicitly identified proposed 0.3 requirements.

## Read order

1. [CONTRACT.md](CONTRACT.md) — proposed 0.3 normative wire contract (not yet validated).
2. [ACCEPTANCE.md](ACCEPTANCE.md) — falsifiable requirements and release gates.
3. [RESEARCH-DECISIONS.md](RESEARCH-DECISIONS.md) — evidence/decision traceability.
4. [ONTOLOGY-BOUNDARIES.md](ONTOLOGY-BOUNDARIES.md) — guaranteed expressivity, gap registry, extension/projection rules and counterexamples.
5. `openspec/specs/` (repo root, two levels up) — the capability specs, converted to OpenSpec format: 0.2 baselines deployed, 0.3 additions proposed as change `add-dsc-03`. This bundle originally shipped its own `specs/`; they were moved to avoid duplication (originals in git history).
6. [CONTRACT-0.2.md](CONTRACT-0.2.md) — executable predecessor contract.

## Relocation note

This bundle is otherwise preserved as received; its original `specs/` directory
was converted into the repo's `openspec/` tree (OpenSpec standard) and removed
here so the corpus holds exactly one copy of each capability spec. Original
file hashes remain in `manifest.json` history.

## Current executable truth

Run `python3 validator.py test` to test the **unmodified 0.2** descriptor fixtures. Do not invoke it on 0.3 descriptors and call them valid; it correctly rejects the new version. Synthetic fixtures do not prove fidelity to real PDFs or EPUBs. The v0.3 validator, selector profiles, manifest grammar, migrated fixtures, PDF/EPUB adapters and cross-reader benchmark remain unimplemented.

## Scope/assumptions

The 0.3 changes are scoped to preserving uncertainty and traceability with minimal core additions. Domain semantics, total reading orders, carrier-specific links, nonlinear geometry and cross-edition equivalence remain explicit profiles or external projections. Unknowns and incompleteness are recorded in [ACCEPTANCE.md](ACCEPTANCE.md).

## Universal ontology boundary

DSC 0.3 is not a universal ontology. The proposed normative boundary policy in [ONTOLOGY-BOUNDARIES.md](ONTOLOGY-BOUNDARIES.md) explains when to use core primitives, registered profiles, external projections or explicit unsupported/unexamined outcomes. This document adds design requirements only; no new JSON fields or implemented ontology mappings are implied.
