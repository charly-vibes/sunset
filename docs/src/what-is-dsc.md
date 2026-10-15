# What is DSC and why

DSC — the **Document Structural Core** — is a specification for exchanging
observations about documents: what text and layout a tool saw, where each
observation came from in the source file, how it was transformed, and what
was *not* captured. This page explains the problem DSC addresses, the shape
of the model, which version of the spec applies to you, and what this
repository (sunset) does and does not provide. It is explanation, not
instruction: the tutorial is [your first descriptor](first-descriptor.md)
and the normative requirements live in
[the deployed capability specs](../../openspec/specs/).

## The problem DSC solves

Comparative research on document models (Docling, METS/ALTO, GROBID/TEI,
PyMuPDF, EPUB 3.3, IIIF, Unstructured/Adobe) surfaced a recurring set of
failure modes that a document-exchange format can either hide or make
honest. DSC is designed to make them honest:

- **Multiple structural views.** A document has a physical structure (pages,
  regions, coordinates) and a logical structure (sections, paragraphs,
  footnotes). Formats that collapse these into one tree conflate reading
  order with layout order — a two-column page becomes scrambled text.
- **Incompatible reading orders.** There is no single "correct" reading
  order; different interpretations (print layout, columnar layout,
  table-first) contradict each other. A format that picks one silently
  discards the others; DSC keeps competing interpretations as separate,
  named hypotheses with no inferred winner.
- **Source-addressable text and layout.** Extracted text is useless for
  review if you cannot point back at the bytes it came from. A semantic
  fragment that cannot be located in the PDF — a known GROBID-coordinates
  failure — breaks the human verification loop. DSC binds every observation
  to typed selectors and evidence anchored in the source.
- **Silent normalization.** Tools normalize Unicode (e.g. to NFC), re-order
  strings, and rescale coordinates without saying so. Two tools then
  "disagree" about bytes that were never comparable. DSC preserves exact
  code points and records normalization as an explicit content transform
  with input and output.
- **Dishonest extraction coverage.** An adapter that reports what it
  extracted, without reporting what it *cannot* extract, invites consumers
  to treat absence of evidence as evidence of absence. DSC requires
  independent source-feature inventories and scoped coverage with
  conservative loss aggregation, so "the table was not captured" is a
  statement in the record, not an omission from it.

The evidence-to-decision trail for these choices — including which prior
art failed which way — is preserved in the research bundle's
[RESEARCH-DECISIONS ledger](../../spec/document-model-specodelic-v3/RESEARCH-DECISIONS.md).

## What a DSC descriptor is

A **descriptor** is the central artifact of the model: a machine-readable
record of one document observation set. Conceptually it has five parts
(this is orientation, not the wire format — see
[document-core](../../openspec/specs/document-core/spec.md) for the
normative shape):

1. **Views** — named structural interpretations of the document
   (e.g. a physical page view, a logical section view). Views are
   independent; contradictory views coexist.
2. **Selectors** — typed addresses into the source (byte ranges, page and
   region coordinates, carrier-specific anchors), bound to an explicitly
   declared interpretation profile rather than to assumed defaults.
3. **Evidence** — pointers tying each derived claim back to the source
   content and anchors that produced it, so a reviewer can replay the
   observation from the original bytes.
4. **Coverage** — inventories of source features and of what the extractor
   did and did not handle, with losses aggregated conservatively.
5. **Interpretation profiles** — explicit local declarations, pinned by
   version and artifact digest, stating the rules under which selectors,
   geometry, and orders are to be read.

The intent throughout is *preserving uncertainty and traceability*: a
descriptor carries its own provenance and its own doubt.

## Which version applies to you

The corpus carries two versions with different statuses:

- **DSC 0.2 is the executable baseline, frozen permanently.** The validator
  at `spec/document-model-specodelic-v3/validator.py` is deliberately
  frozen at 0.2 (it passes 11 descriptor fixtures and correctly rejects 0.3
  descriptors). Do not build against it expecting 0.3 behavior; its
  [known validation limitations](baseline-limitations.md) are documented
  and visible.
- **DSC 0.3 is the current target.** Its requirements are deployed in the
  openspec specs (seven capabilities) from the archived change
  [add-dsc-03](../../openspec/changes/archive/2026-10-14-add-dsc-03/proposal.md),
  and the executable machinery is implemented in the `dsc03/` package with
  its test suite under `tests/tracer/` (gate: `just spec-check`). One
  caveat on maturity: the 0.3 machinery and its reviews were agent-executed,
  with the deviations recorded in [status](status.md) — a human pass
  supersedes them, and no real-carrier conformance is claimed beyond what
  `dsc03/conformance.py` honestly labels.

**Newcomers should target 0.3.** 0.2 exists as the preserved, falsifiable
baseline that 0.3 was proposed against; it is history and evidence, not the
on-ramp.

## What sunset is (and is not)

This repository, **sunset**, is a **DSC specification corpus**: the
capability specs, the frozen 0.2 executable truth, and the 0.3 conformance
machinery (`dsc03/`, fixtures, tracer tests). It is **not a tool** — there
is no CLI, no installable package, and none is planned; the
[scope ruling](status.md#deviations-from-the-fleet-standardization-checklist)
records this deliberately. The intended adoption path is external
consumers implementing DSC and running the conformance suite against their
own implementations. A walk-through of the machinery in action —
descriptor → validate → profile resolve → evidence replay — is in the
[first-consumer demonstration](tracer-bullet.org).

## Where next

- [Your first descriptor](first-descriptor.md) — the tutorial
- [Reference](reference.md) — index of specs, machinery, and gates
- [Status](status.md) — current state, gates, and recorded deviations
- The [deployed specs](../../openspec/specs/) — the normative source of truth
