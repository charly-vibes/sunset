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
   **Ruled (owner, 2026-11-24, via sunset-gpd gate G1): additive within DSC 0.3.** The identity profile is opt-in; descriptors without it keep the existing label-id semantics and canonical bytes, so no wire break for non-users. The position-dependence audit (below) found zero order dependence outside canonicalization/assembly, supporting the additive reading. Tasks 2.2+ unblocked.
2. Should `coverage` entries gain derived ids or keep the triple key?

## Position-dependence audit (task 1.1, 2026-11-24, agent-executed at HEAD)

Audit of every dependence on array position in the eight set-like sections of
Decision 3 (`regions, contents, selectors, evidence, annotations, coverage,
interpretations, profiles`), across deployed requirements, validator rules,
canonicalization, assembly, native extraction, compare and migrate. All
file:line grounded at HEAD.

### regions

| Hit | Location | Evidence |
|---|---|---|
| No position dependence found | `dsc03/validator.py:320-348` (regions loop) | per-item checks only: `err("duplicate_id")` keyed on the id set; no index, no neighbor, no order predicate |
| (context, not a set-semantics violation) | `openspec/specs/document-core/spec.md:95` | "Geometry and array positions SHALL NOT imply order or require a total order." — spec already mandates position independence |

### contents

| Hit | Location | Evidence |
|---|---|---|
| No position dependence found | `dsc03/validator.py:350-361` | id-set uniqueness (`if c["id"] in content_ids: err("duplicate_id")`); no ordering rule |

### selectors

| Hit | Location | Evidence |
|---|---|---|
| No position dependence found | `dsc03/validator.py:363-388` | id-set uniqueness and per-selector field/target checks; note `openspec/specs/document-evidence/spec.md:201` "a nonempty ordered array of selector ids" — that is the `selector_ids` array *inside an annotation record*, a declared ordered list, not section array position |

### evidence

| Hit | Location | Evidence |
|---|---|---|
| Positional uniqueness of producers | `dsc03/validator.py:535-556` | `producers.setdefault(cid, []).append(eid)` then `producers[i][0]` (line 555) — takes the *first* evidence id per content; safe only because `invalid_transform_binding` (line 552, `len(producers.get(cid, [])) != 1`) guarantees exactly one producer, so `[0]` is degenerate, not order-reliant |

### annotations

| Hit | Location | Evidence |
|---|---|---|
| Page-index-derived identity | `digitization/native.py:148-153` | `annotation['id'].startswith(f'an{r["id"][2:]}-')` over `int(r['id'][2:])` — the `an{page}-` id prefix encodes the page number (a page *index*), used to retarget an annotation when its content is excluded. This is identity derived from a page ordinal, exactly what Decision 1 replaces with anchor tuples |

### coverage

| Hit | Location | Evidence |
|---|---|---|
| No position dependence found | `dsc03/validator.py:623-652` (`for c in d["coverage"]`) | per-entry field checks (`invalid_coverage`); identity is the uniqueness key, cf. `dsc03/validator.py:59` where coverage's canonical key is the field tuple including `("inventory_id", "feature", "scope", ...)` |

### interpretations

| Hit | Location | Evidence |
|---|---|---|
| No position dependence found | `dsc03/validator.py:313-318, 600-621` | id collection only (`interp_ids.add(i["id"])`); reading-order semantics live in `precedes` relations via `order` values, not section position |
| (relations, not this section) | `dsc03/validator.py:529-530` | `err("order_cycle")` — order is carried by `precedes` edges, confirming Decision 3's premise |

### profiles

| Hit | Location | Evidence |
|---|---|---|
| No position dependence found | `dsc03/validator.py:296-311` | id-set uniqueness (`duplicate_id`) plus per-profile field checks |

### Canonicalization (both readers)

| Reader | Location | Evidence |
|---|---|---|
| reader_a | `dsc03/canonical.py:28-29` | `if isinstance(x, list): return [_canon_a(v) for v in x]` — array order preserved verbatim |
| reader_b | `dsc03/canonical.py:46-48` | `"[" + ",".join(_item_bytes(item) for item in x) + "]"` — emits list items in input order; `for key in sorted(descriptor)` (line 58) sorts only object keys |
| Contract | `openspec/specs/document-conformance/spec.md:57` | "readers SHALL preserve ids, array order and exact text" — order preservation is a deployed requirement |

### Assembly (dsc03/substrate/assembly.py)

| Hit | Location | Evidence |
|---|---|---|
| Left-operand-first ordering | `dsc03/substrate/assembly.py:100-104` | `merged, index = [], {}` / `for item in a_items + b_items:` — first occurrence wins; header comment (lines 23-24): "left operand's items first (first occurrence wins), then the right's new ones" |
| Section merge order | `dsc03/substrate/assembly.py:164-176` | `for section in _BY_ID:` iterates sections in a fixed order, then coverage by its triple `("inventory_id", "feature", "scope")` (`_COVERAGE_KEY`, line 32) |

### compare.py and migrate.py

| Hit | Location | Evidence |
|---|---|---|
| Ordered-witness rule id | `dsc03/compare.py:70` | `RULE_WRONG_ORDER = "dbg.reading_order.conflict"` — order violations detected via `precedes` relations (fixture `wrong-reading-order`, lines 350-357), not array position |
| Sign-column witness tie-break | `dsc03/compare.py:174-176` | `witness = f"sign_column:{differing[0]}"` — picks the first of a `sorted()` set for the witness string only; comparison itself is `ls != rs` on dict values |
| Deterministic re-synthesis | `dsc03/migrate.py:134-146` | `for j, (a, b) in enumerate(edges):` synthesizes ids `migrated-precedes-{vid}-{j}` and `for vid, edges in order_edges.items():` `migrated-order-{vid}` — generated ids depend on dict insertion order of the *source* descriptor's relation array (migration is a one-shot translation, and the emitted order lives in relations/interpretations, which Decision 3 sorts by id afterwards) |
| Sorted rebind | `dsc03/migrate.py:170` | `regions = sorted(content_bindings[t])` — order-normalizes before disambiguation, a position-removing measure |

### Summary

| Section | Dependence count |
|---|---|
| regions | 0 |
| contents | 0 |
| selectors | 0 |
| evidence | 1 (degenerate `producers[i][0]`, safe under uniqueness rule) |
| annotations | 1 (`an{page}-` id prefix = page-index identity, `digitization/native.py:151`) |
| coverage | 0 |
| interpretations | 0 |
| profiles | 0 |

**Answer for coverage (informs Open Question 2):** nothing relies on array
order for `coverage`. Identity is entirely the uniqueness triple
`(inventory_id, feature, scope)` — enforced by validator per-entry checks
(`dsc03/validator.py:623-652`), used as the merge key by assembly
(`assembly.py:32,175-176`), and coverage is the only section already merged
by a non-id key. Entries may therefore keep the triple key with no
position-order obligation; granting them derived anchor ids is optional.

**Caveat:** this audit is agent-executed; a human pass supersedes it.
