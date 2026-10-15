# Design decisions — assembly slice (sunset-905.1, 2026-10-15)

Decision record for `specs/document-assembly/spec.md` (this change). Scope:
**stable canonical equality** and **explicit ID namespace collision behavior**
(task 4) as realized by the consumer-side module `dsc03/substrate/assembly.py`
with law fixtures `tests/substrate/test_assembly_laws.py` (task 5). No new
normative scope is introduced here; every decision below resolves an
underspecified point *inside* the delta's existing invariants. The deployed
wire (`openspec/specs/`, frozen bundle) is untouched; the deployed kernel
still has no composition checker (law 5 stays **partial** per
`restore-document-substrate/mapping.md`) — this is machinery-level
witnessing, never a conformance claim.

## D1 — Canonical equality (assembly_identity, assembly_associative)

**Decision.** Canonical equality of assembly results is byte equality under
**both** independent canonical readers of the deployed two-reader contract
(`dsc03/canonical.py`: `reader_a` generic sorted-key walk, `reader_b`
independent top-level emission with key-set check). `canonically_equal(a, b)`
requires both readers to agree; disagreement is never collapsed into a
winner. This inherits the substrate identity law (mapping.md law 3: stable
under canonical serialization) instead of defining a second equality.

**Resolved sub-decisions (forced by the delta's "up to canonical
representation" clause):**

- **Assembled `id`.** The assembled descriptor takes the `id` of its first
  non-empty operand (left-biased). This makes identity and both
  associativity bracketings agree at the canonical level
  (`compose(compose(A,B),C).id == compose(A,compose(B,C)).id == A.id`)
  without inventing an id-merge scheme.
- **Array order is preserved, not canonicalized.** Merging appends the left
  operand's items first, then the right's new items (first occurrence wins on
  dedupe). Both bracketings yield the same A,B,C order, so associativity
  holds; re-sorting arrays would be a wire-visible change and is avoided.
- **The empty part is an assembly-layer identity element.** The deployed 0.3
  wire cannot represent a fully empty descriptor (a logical view with an
  existing root region is mandatory — `invalid_view`), so `empty_part()` is a
  structurally empty skeleton (no regions/views/contents/relations/evidence/)
  defined *at the assembly layer*. `compose(A, empty)` admits it without
  descriptor-level validation (nothing to validate) and returns the other
  operand unchanged up to canonical bytes. **Recorded expressivity note:** a
  wire-level empty-descriptor state does not exist; adding one would be a
  wire delta and is out of scope for this slice.

## D2 — ID namespace collision behavior (assembly_compatible, boundaries_preserved)

**Decision.** Shared IDs designate **one source identity** (design §2: "not
duplicate copies"); collision behavior is refuse-with-witness by default and
merge only under the identical-claims precondition:

| Case | Behavior | Rule / witness |
|---|---|---|
| Same ID, **different source** | refuse | `same_id_conflicting_source`; smallest witness = one colliding entity id (cross-edition identity has **no** deployed entity — mapping.md finding 2; silently renaming the source is exactly what the delta forbids) |
| Same ID, same source, **conflicting record** (any field, e.g. `kind`, `view_id`, geometry) | refuse | `same_id_conflicting_claims`; smallest witness = the colliding id. Record-level equality is deliberately strict: "identical claims" means the canonically equal item record, not a field-subset match |
| Same ID, same source, **identical record** | merge into a single identity; original edges and provenance retained (left-first, dedupe) | `boundaries_preserved` — exercised by `shared_id_merges` |
| Same **vocabulary namespace**, different version | refuse | `namespace_mismatch`; witness = the namespace ("aligned namespace" precondition of the assemble guard) |
| Different sources, **disjoint** ids | refuse | `source_mismatch` — one source record per descriptor on this wire; cross-carrier composition is not representable |
| Union fails validation (incl. cross-collection id reuse) | refuse | `assembled_invalid` with the validator's classified reasons |
| **Different sources, same ids** with non-edges… | — | covered by row 1; no merge path exists across carriers |

**Refusal shape** (classified, never a crash — same discipline as
`typed_check`): `{"status": "refused", "rule": <id>, "smallest": [<ids>],
"detail": {...}}` — the "smallest known witness" is the minimal fact set
(usually a single id) proving the conflict.

**Justification against the invariants.** `assembly_compatible` requires
"aligned namespace, compatible region identity, jointly satisfiable
constraints … smallest known witness" — rows 1, 2, 4, 5, 6 are exactly the
classified refusals with minimal witnesses. `boundaries_preserved` requires
"shared region IDs refer to a single source identity; composed boundary links
preserve original edges and provenance" — the merge row keeps one identity
with all original operand edges and evidence records, and the refusals
prevent a shared ID from ever denoting two identities. `order_not_implicit`
holds structurally: compose carries **only** operand-declared edges, so no
`precedes` edge (and no edge at all) is ever invented by assembly
(`no_invented_order` fixture asserts the assembled edge set equals the union
of operand edge sets).

## D3 — Parts are partial; references resolve against the union

A part may declare an edge whose endpoint lives in another part (the
magazine continuation edge: `precedes` declared on part A targeting B's
region). Per-part descriptor validation is therefore **not** an assembly
precondition (`parts_ready` state); the *assembled union* must validate
(`typed_check` accepted) — that is the "all references resolve" guard of the
`assemble` transition. An unresolvable or inconsistent union refuses as
`assembled_invalid`. This keeps the fixture honest about the delta's
scenario ("two regions on separate magazine pages and a continuation
relation") without inventing a cross-part reference wire type.

## D4 — Composition of refusals

Nested notation `compose(compose(A,B),C)` composes prior result envelopes
directly; a refusal on either side propagates (composition with a refused
operand is refused, never a crash). This is an operational convenience for
the law fixtures, not new semantics.

## Placement

`dsc03/substrate/assembly.py` (consumer-side, beside the existing `Mapping`
algebra in `dsc03/substrate/laws.py`), tests in
`tests/substrate/test_assembly_laws.py`. Justification: the deployed kernel
has no assembly/composition checker; placing the operation in the substrate
harness (a) reuses the `typed_check`/classified-result discipline and
`synthetic_instance` conventions, (b) avoids implying deployed-spec
conformance, and (c) leaves `dsc03/conformance.py` labels untouched. Moving a
kernel-level composition checker into `dsc03/` would be a later, separately
specified change.

## Falsifiability

The nine fixtures in `tests/substrate/test_assembly_laws.py` map to the
delta's Properties table: `compatible_pair`, `duplicate_conflict`,
`left_right_identity` (law), `associate_three` (law), `no_invented_order`,
`shared_id_merges`, plus three decision backstops (`same_id_conflicting_claims`,
`namespace_mismatch`, `source_mismatch`). Any future kernel implementation
must reproduce these outcomes; a kernel that silently merges conflicting
shared IDs, invents edges, or breaks a bracketing fails these fixtures.
