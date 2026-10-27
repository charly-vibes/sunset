# Change: Add iterative document digitization

## Why

Digitizing Diario de Poesía requires recovering text and structure from scanned pages whose columns, images, captions and poems vary. Whole-page OCR can mix reading order and discard meaningful poetic layout. Sunset preserves attributed observations but does not yet orchestrate region detection, recognition and structural refinement into an economical automatic workflow.

## What Changes

- Add an optional digitization consumer of DSC: propose regions, recognize content, propose structure, check results and refine affected regions in a bounded loop.
- Prefer deterministic processing and explicit policies; isolate OCR/AI variability in immutable, content-addressed artifacts with exact recorded replay.
- Preserve region revisions, splits/merges, competing readings, poem layout and unresolved coverage without promoting model claims to source facts.
- Add configured cost/call/iteration limits, selective retries, public crash-safe resume, real local crop-OCR integration and a reproducible evaluator with known-answer scoring fixtures.
- Gate difficult-page and six-page experiments separately, freezing each stage's references/settings before inference; explicitly authorized engineering runs with missing references remain evaluation-incomplete.

## Impact

- New capability: document-digitization. Existing document-evidence, document-adapters, document-structure and document-semantics contracts are reused, not duplicated or modified.
- Future implementation: a separate orchestration package and provider adapters, DSC projection, local run artifacts and digitization tests; exact module names are implementation decisions.
- Lens may inspect emitted results when available; its pending browser milestone is not a prerequisite for a headless pilot.
- No changes to frozen 0.2 validation, preserved research documents, raw human sheets or existing conformance labels.

## Scope and approval

Proposal only. Approval authorizes a first difficult-page vertical slice, followed by evaluation across the six-page excerpt; full-issue scaling is a later decision based on measured results. No provider, paid account or external document upload is selected or authorized here. Local processing must be possible; remote inference requires separately authorized service access.

## Reviewable user outcome

A local headless run accepts a PDF, page selection and pinned configuration, then returns a run directory containing searchable text with source mappings, DSC descriptors, retained artifacts, unresolved diagnostics and a resource ledger. Resume, offline replay and local inspection use that directory. The design defines refusal and status behavior; the design pins public invocation syntax and implementation task 1.1 must document working examples. The local OCR integration slice must precede measured pilots; both pilot stages use the same local evaluate operation. Quality/economy success requires the reviewed reference coverage defined in the design; absent evidence is evaluation-incomplete.

## Success

A reviewer can obtain searchable text and proposed structure from the existing scan, inspect their source links and revision history, and replay recorded results without inference. Evaluation reports segmentation/text/structure quality, poetry layout preservation, omissions, actual resource usage and correction effort against a fixed baseline. Improvement and low cost are hypotheses to measure, not promises.
