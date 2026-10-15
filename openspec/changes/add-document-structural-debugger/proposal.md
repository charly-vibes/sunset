# Change: Add Sunset Lens — document structural debugger

## Why

Sunset's Document Structural Core (DSC) needs a human-verifiable way to inspect source documents against deterministic structural descriptions. Schema-valid descriptors can still encode incorrect reading orders, mistaken regions, lost observations, unsupported assertions and unjustified equivalences. A first-class *consumer* of DSC can surface these errors without altering the core or turning extraction reconciliation into the system's purpose.

## What changes

1. Add a read-only debugger of DSC descriptions with synchronized document, structure and evidence views, linked by stable region/selector identities.
2. Render native PDF, scanned PDF/images, and reflowable EPUB through carrier-specific viewer adapters without treating viewport coordinates as persistent identity.
3. Surface typed diagnostics for schema, containment, ordering, selector resolution, provenance, unexamined coverage, and domain-specific checks; separate machine-checked failures from manual review.
4. Compare multiple typed descriptions or transformation paths on an explicit, versioned observable scope and equivalence relation. Do not assume equality of independent editions.
5. Export minimal reproducible counterexample bundles linking failure, witness, source hash, descriptor hash, rule ID, versions, and reproduction instructions. Allow redaction without falsifying hashes.
6. Link diagnostic IDs to Specodelic constraint/property references where available; unresolved links remain explicit.

## Dependencies

- `restore-document-substrate`: its `document-purpose` and `document-categorical-model` contracts are conceptual dependencies. If not merged, the debugger can initially operate only on currently deployed DSC 0.3 wire semantics; it must not silently assume the proposed categorical requirements are already normative.
- Exact existing Sunset capability IDs and its current canonical profile and trace schema require verification against the integration checkout (UNKNOWN here).

## Non-goals

- Editing the source PDF/EPUB, implementing OCR, automatic semantic repair, new DSC primitives, a mandatory network service, or a general-purpose category theory runtime.
- Proving semantic truth from visual alignment, or calling uncertain results errors without a declared oracle.
- A performance claim about human review speed before a controlled measurement.

## Compatibility and rollout

The debugger is a separate, optional consumer. No core wire changes are authorized by this change. Any discovered representation gap must become a minimized counterexample and a separate core change with migration analysis.

## Success

A reader can load a fixture for each native PDF, EPUB, scanned magazine and hybrid PDF; navigate from an annotation to the exact available source evidence; see a deliberately false reading-order claim; and export and replay that failure with no source mutation. A second implementation must agree on diagnostic identifiers and equivalence outcomes for frozen deterministic fixtures.

## Integration record (grounded 2026-10-15)

- **Checkout:** sunset `518a71a4abb7caa5e253cc1d5711b7cfce61fbe7`. Deployed
  capability IDs verified as listed in the proposal's mapping targets. The
  conceptual dependency `restore-document-substrate` is integrated in the same
  changeset as a proposal (not yet deployed); this debugger change still only
  assumes deployed DSC 0.3 wire semantics until that change is archived.
- **Validations actually run** (spk 0.10.0):
  `openspec validate add-document-structural-debugger --strict` → valid;
  `spk lint openspec/changes/add-document-structural-debugger` → 0 issues;
  `just spec-check` → all gates green.
- **Integration normalizations applied** (integrated files diverge from the
  as-received zip): ids rekeyed to dotted law (`document.debugger`,
  `document.debugger.comparison`); `## Requirements` mirrors added via
  `spk migrate`; transition guards cite own-file constraints so all
  states/transitions reach the intent rows. Existing diagnostic IDs of the
  deployed 0.3 machinery are enumerated in `dsc03/report.py`; the open
  decision on which to reuse remains open.
- **Not done:** no viewer, adapter, diagnostic or comparator implementation
  exists; `fixtures/README.md` specifies oracles only (see `tasks.md`).
