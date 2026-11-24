## Context

Identity today is whatever string the producer chose. The validator enforces uniqueness within a descriptor but nothing relates an id to what it denotes. Canonicalization (`dsc03/canonical.py`, two independent readers) preserves ids and array order exactly, which is correct for label ids and wrong for set semantics.

## Goals / Non-Goals

Goals: ids that are functions of anchors; order-independent canonical bytes for set-like sections; exact geometry; explicit, reversible relabeling.

Non-goals: changing the meaning of any existing relation kind; deciding the wire-version question here (Open Question 1); content hashing of text values as identity (text can legitimately differ between producers at the same anchor).

## Decisions

1. **Anchor tuple.** `(source_sha256, record_kind, locator_path, profile_id, profile_version)`. Text values are excluded so two producers reading the same anchor yield the same id and their *claims* about it remain separately attributed. `locator_path` is the selector's profile-bound locator, e.g. `page:3/line:12/word:4`, or a raw-text interval `raw:[120,128)` for text-bound records.
2. **Digest form.** `a:` + first 128 bits of SHA-256 over the canonical JSON of the tuple, lowercase hex. 128 bits keeps ids short; collisions are detected, not assumed impossible (Requirement: Collision refusal).
3. **Set-like sections.** `regions, contents, selectors, evidence, annotations, coverage, interpretations, profiles`. Sorted ascending by id (coverage by its existing uniqueness triple). Ordered meaning already lives in `precedes` relations; the audit task confirms no deployed requirement relies on array position in these sections.
4. **Quantum.** Default 1/1000 pt, round-half-even, applied once at extraction. The pre-quantization float is not retained in the descriptor; the transform record names quantum, rule and extractor version so the loss is declared, as DSC already requires for normalization.
5. **Relabeling.** `migrate` emits `relabel-table` evidence mapping old→new ids. Content values are never touched.

## Risks / Trade-offs

- Ids become opaque to humans. Mitigation: tools display `kind + locator_path`, never the digest.
- Quantization loses sub-quantum precision. Mitigation: quantum is declared; 1/1000 pt is far below PDF text-positioning noise, but the claim "no loss" is not made.
- Anchor-derived ids require a stable locator grammar per carrier. Mitigation: scoped to PDF native first; EPUB (CFI) follows its existing selector profile.

## Migration Plan

1. Ship the profile and validator support behind opt-in.
2. `native` emits identity-profile descriptors; label-id output remains available until identity-profile descriptors become the only emitted form (the rotation is recorded as a task in tasks.md).
3. Re-run the fixture corpus and diff canonical bytes between two processes.

## Open Questions

1. Is the identity profile additive within DSC 0.3, or does set-like sorting require 0.4? Needs owner ruling.
2. Should `coverage` entries gain derived ids or keep the triple key?
