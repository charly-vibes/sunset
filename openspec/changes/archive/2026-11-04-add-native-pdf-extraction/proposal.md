# Change: Add automatic native PDF extraction with source locations

> **Implementation status (2026-10-30):** The local native-text capability is
> implemented in `digitization/native.py` with CLI extraction, integrity
> inspection, read-only resume and offline replay. This proposal remains the
> historical design source; OCR, visual completeness and installable packaging
> remain outside the implemented baseline.

## Why

A user with a PDF containing embedded text should obtain searchable text and
verifiable source references without assembling recorded recognition inputs.
Sunset already has native page-text adapters and evidence machinery, but their
public workflow does not yet provide word/line mappings. The product promise is
PDF → searchable attributed text → inspection; DSC supplies the underlying record.

## What Changes

- Establish a local native-text extraction route with source and output as its
  required inputs, optional page selection and documented pinned defaults.
- Reuse the existing adapter, selectors, artifact integrity and inspection paths.
- Preserve raw text, word/line geometry, search derivations and extractor metadata.
- Define repeatable semantic outputs and explicit partial coverage and failures.
- Document the working command and outputs when implemented, rather than advertise
  a proposed invocation as currently available.

## Impact

- Affected capability: document-adapters (additive consumer requirements).
- Expected code: dsc03/adapters.py and digitization CLI, pipeline, artifacts,
  rendering and inspection modules as needed; reuse decisions precede new code.
- Documentation now describes Sunset as developing an extraction tool alongside
  DSC. This supersedes the historical no-CLI scope; packaging is separate work.
- No DSC core wire changes, frozen-validator changes, Rust rewrite, automatic
  domain-field extraction, OCR, remote services or preserved-bundle edits.

## Scope and execution

**Proposal-time execution plan:** This change specified future runtime delivery,
tracked by `sunset-jbb`; it did not claim implementation at proposal time. The
owner authorized completing all implementation tickets via wai orchestration
with Codex gpt-6-luna subagents (2026-10-29). `sunset-jbb.1` through `.4` track
sequential vertical slices; those slices implemented the native route described
above. Native extraction is independent of the Diario OCR pilot and its
engine/reference approvals; those remain intact for OCR execution.

Use generated or redistributable test PDFs. The owner's
`pba-judicial-2026-07-29.pdf` is a local acceptance example, not a published fixture.
No permission to publish that PDF, push, deploy or release is inferred.

## Success

One local invocation produces validated DSC, searchable text and inspectable
source mappings. With identical PDF bytes, settings and extractor dependencies,
two fresh runs produce byte-identical semantic artifacts. Source geometry and
raw text remain available; incomplete coverage is visible. No OCR accuracy,
human-effort improvement or broad conformance claim follows from this journey.
