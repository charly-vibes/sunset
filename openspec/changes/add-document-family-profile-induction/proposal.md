# Change: Document-family profile induction (learned, versioned wrapper profiles)

## Why

Extraction treats every document as a stranger: nothing accumulates across
documents of the same family (gazette editions, journal issues), so recurrent
structure — masthead bands, column grids, rule placements, decorative ink — is
re-derived per document or missed. `digitization/detect.py` proposes geometry
only, with kind pinned to `ink-block` and classification explicitly deferred
("content-class territory (sunset-pkj), not a threshold tweak").

sunset-9rg's agent-external BORA gazette experiments (transcript
`chatgpt~6ae4669e`, recorded in the ticket with caveats) showed the shape of the
fix: native objects miss raster ink entirely (70.03% coverage on a scanned-era
page vs 96.31–97.44% on modern pages), and content-class-aware observation lifted
that page from 71.89% to 99.55%. Its final recommendation is **wrapper induction
+ learned versioned document-family profiles** — observe documents → discover
recurrent structure → propose a model → test counterexamples → compile
deterministic rules → reconstruct and validate new documents, with **abstention**
when evidence is insufficient — tested on held-out editions **BEFORE** any DSC
core expansion, learning machinery kept **outside normative DSC core**.

The machinery to do this honestly exists at HEAD and is unused for families
(verified 2026-11-24):

- `dsc03/visual/content_classes.py::observe_page` already emits `graphic-hypothesis`
  entries with `interpretation_status: "hypothesis"`, role `hypothesis`,
  `status: "not-derived"` until derived — provenance-carried hypotheses, never
  observations.
- Deployed `document-ontology-boundaries` forbids silent coercion (O-A01) and
  applies projections only with declared provenance ("a projection omits its
  declaration → it is not applied as a valid mapping").
- Deployed `document-core` "Pinned profile declarations" closes the descriptor
  profile kinds to `selector|geometry|carrier-inventory|adapter-manifest|alignment`;
  a learned family profile cannot become a new descriptor kind without a core +
  validator change — which is out of scope here by anti-goal.
- Deployed `document-evidence` already distinguishes origins
  (`source|extracted|inferred|manual|external`) and requires transform records
  with pinned dependencies and lineage edges.

What is missing is the induction loop itself: an artifact shape for learned
profiles, deterministic compilation, counterexample testing, a held-out edition
gate, and typed abstention. Without that definition, family knowledge stays
tribal, or leaks into core as unjustified observations.

## What Changes

- New capability `document-family-profiles`: learned, versioned, digest-pinned
  **profile artifacts** produced by the induction loop above. All requirements
  ADDED.
- The profile is a **wrapper artifact outside the descriptor**. Induction and
  learning machinery stay outside normative DSC core; everything a profile
  contributes to a descriptor travels through existing DSC mechanisms (evidence
  records with transform lineage naming the profile as a pinned dependency,
  origin-typed annotations, existing pinned profile kinds) — never through new
  core vocabulary.
- **Deterministic compilation**: the proposed model compiles to deterministic
  rules as a pure function of recorded inputs; recompilation reproduces
  byte-identical rules. Extraction applies only compiled rules — **no runtime
  LLM or model inference in the extraction path**.
- **Typed abstention**: when a compiled profile's preconditions or evidence
  sufficiency fail on a new document, the wrapper abstains with a typed outcome
  naming the unsatisfied condition and emits nothing profile-derived.
- **Held-out edition gate**: acceptance requires reconstruction validation on
  editions *not* used during induction, with measured agreement recorded in the
  artifact. A held-out record is a prerequisite for any future proposal to
  expand DSC core — never a part of this change.
- **Graphic-region candidates stay typed hypotheses** (HEAD precedent:
  `graphic-hypothesis`); a projection of profile knowledge is applied only with
  declared provenance — projections without provenance are not applied (O-A01/O-A04).
- **Caveats travel**: the BORA numbers are proxy metrics tuned on 3–11 pages;
  the caveat block is carried verbatim in this change and must be carried into
  any implementation ticket.

## Anti-goals (binding)

- **No runtime LLM in the extraction path.** Learning happens offline at
  induction time; extraction consumes compiled deterministic rules only.
- **No claims on BORA numbers.** Proxy metrics, not annotated accuracy; tuned
  iteratively on the same 3–11 BORA pages; no LLM evaluation was executed;
  ownership checks are internal. Every number cited here is agent-external
  measurement carrying these caveats; none is an accuracy or conformance claim.
- **No validator changes.** Frozen 0.2 untouched; the 0.3 validator, core
  vocabulary, profile-kind set, canonical form and validity rules unchanged.
- **No implementation in this change.** Proposal only; an owner approval gate
  precedes any implementation ticket (pattern: sunset-rmx.1).

## Impact

- Affected specs: new capability `document-family-profiles` (all requirements
  ADDED). No MODIFIED or REMOVED deltas to any deployed capability.
- Affected code: none in this change. Future implementation would add an
  induction module over recorded run artifacts and `dsc03/visual` observations,
  plus a wrapper application step in the digitization route — exact module
  names are implementation decisions under the owner gate.
- Depends on deployed machinery only: `document-evidence` (origin typing,
  replay material), `document-ontology-boundaries` (O-A01, O-A04, inference
  isolation), `document-core` (pinned profiles, local registry resolution),
  `dsc03/visual/content_classes.py`.
- Independent of the in-flight proposal set: no dependency on
  `add-scale-complete-regions` or `add-claim-verification-ladder`.
- No conformance label changes; no claims beyond existing machinery.
