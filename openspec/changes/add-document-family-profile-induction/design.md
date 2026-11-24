# Design: Document-family profile induction

## Context

sunset-9rg's final recommendation (recorded in the ticket from the cotorreo
investigation, agent-external): wrapper induction + learned versioned
document-family profiles — observe → discover → propose → counterexample-test →
compile deterministic rules → reconstruct and validate → abstain — validated on
held-out editions BEFORE expanding DSC core, learning machinery outside
normative DSC core.

Verified at HEAD, 2026-11-24:

- `dsc03/visual/content_classes.py` (landed via sunset-pkj) emits four typed
  content classes per page; `graphic-hypothesis` entries carry
  `interpretation_status: "hypothesis"`, role `hypothesis`, `status:
  "not-derived"` until derived. This is the hypothesis-typing precedent the
  capability generalizes from per-page candidates to per-family profiles.
- Deployed `document-ontology-boundaries`: no silent coercion (O-A01); explicit
  projection provenance (O-A04 — a projection without its declaration "is not
  applied as a valid mapping"); inference isolation (derived statements are
  labeled derived); conditional roundtrip (O-A05).
- Deployed `document-core` "Pinned profile declarations": descriptor
  `profiles[]` kind SHALL be one of `selector|geometry|carrier-inventory|adapter-manifest|alignment`
  — a closed set. A new `family` kind would be a core + validator change.
- Deployed `document-evidence`: origin typing
  (`source|extracted|inferred|manual|external`); transform records with
  `config_sha256`, pinned `dependencies`, and lineage edges; "Missing replay
  material cannot be labeled reproducible".
- The digitization route already records configs, run artifacts and replay
  material; `digitization/detect.py` is deliberately classification-free.

Binding anti-goals carried verbatim from sunset-elx: no runtime LLM in the
extraction path; no claims on BORA numbers (proxy metrics tuned on 3–11 pages,
caveats must travel); no validator changes; no implementation in this change.

## Goals / Non-Goals

Goals:

- A defined artifact and loop so family knowledge accumulates instead of being
  re-derived per document.
- Deterministic compile + typed abstain semantics, precisely specified.
- A relation between learned profiles and DSC descriptors/evidence that cannot
  violate the observation/interpretation boundary by construction.
- A held-out validation gate that must pass before anyone may even *propose*
  core expansion.

Non-Goals:

- Any core expansion in this change (no new profile kind, section, or relation
  kind; no validator change).
- Runtime learning or model inference in the extraction path.
- Accuracy or conformance claims from the BORA experiments (their caveats
  travel; the numbers are proxy metrics on 3–11 pages, tuning-set-bound).
- Choosing the first document family or carrier set (owner decision at
  implementation time, under the approval gate).

## Decisions

1. **Wrapper induction: the profile lives outside the descriptor.** A family
   profile is a standalone versioned artifact: id, version, sha256 over exact
   bytes, declared family scope, induction input digests, compiled rules,
   counterexample suite record, held-out validation record, and the caveats
   block. It never becomes descriptor vocabulary — no new `profiles[]` kind
   (closed set at HEAD), no new section, no new relation kind, mirroring the
   deployed "Profile isolation" rule (a registered profile SHALL NOT redefine
   core identity, relations, canonical form, or validity rules). *Alternative
   considered:* a new `family` profile kind — rejected: requires a core +
   validator change (binding anti-goal).

2. **Induction loop stages, each with a recorded artifact.** Observations are
   existing recorded artifacts (run directories, `content_classes` records,
   native descriptors). Discovery and model proposal run offline over recorded
   inputs only. The proposed model is recorded before compilation. The
   counterexample suite is recorded as named cases with expected outcomes.
   Compilation consumes the recorded model + recorded observations + compiler
   version. Validation reconstructs held-out editions and records measured
   agreement. Every stage's artifact names its inputs, so the chain from source
   documents to compiled rules is auditable.

3. **Deterministic compile semantics.** Rules are declarative, inspectable
   statements with declared preconditions (matchers over recorded observations)
   and effects (proposed structure). Compilation is a pure function: identical
   recorded inputs and compiler version produce byte-identical rules. The
   extraction path applies only compiled rules and performs no model, provider,
   or network inference; if no rule can fire with sufficient evidence, the
   wrapper abstains (Decision 4). A profile-derived contribution to a
   descriptor is recorded as evidence whose transform names the profile
   artifact (id + version + sha256) among its pinned `dependencies` — exactly
   the deployed "Replay material for derived observations" contract, unchanged.
   *Alternatives considered:* runtime model inference — rejected (anti-goal,
   nondeterministic); fuzzy/probabilistic rule application — rejected
   (uninspectable; compile refuses instead of approximating).

4. **Abstain semantics.** Abstention is a typed, *successful* outcome — not an
   error, and never a silent fallback. The artifact declares the profile's
   firing preconditions (family match over declared scope and source digests,
   minimum observation counts, required content classes present). When a
   precondition fails or evidence is insufficient, the wrapper emits a typed
   abstention outcome naming the unsatisfied condition and emits nothing
   profile-derived. Output produced without a firing profile is labeled
   unprofiled, so absence of profile coverage is always distinguishable from
   profile-derived structure. Precedents: `identity_anchor_missing`
   (add-anchor-derived-identity) and `evaluation-incomplete` (digitization
   evaluation): typed incompleteness instead of invented interpretation.

5. **Relation to descriptors/evidence — the observation/interpretation
   boundary.** Profile-derived structure enters a descriptor only as:
   - evidence records with transform lineage whose pinned dependencies name the
     profile artifact, and
   - annotations/records with origin `inferred`, never `source`.
   Graphic-region candidates stay typed HYPOTHESES exactly as
   `graphic-hypothesis` does today (`interpretation_status: "hypothesis"`,
   role `hypothesis`) — the profile cannot promote them to normative
   observations, because the transcript's own caveat holds: a pixel-derived
   candidate "does not establish whether it is a header, decoration, background".
   Any projection of profile knowledge onto a document is applied only with
   declared provenance (source profile version, rules, scope, losses) —
   projections without provenance are not applied (deployed O-A04); derived
   statements are labeled derived (inference isolation). Learning machinery
   itself never appears inside a descriptor: induction reads recorded
   artifacts; only its compiled, provenance-carrying outputs cross the line.

6. **Held-out editions gate, before any core expansion.** Profile acceptance
   requires reconstruction validation on editions absent from the induction
   input set, with measured agreement recorded in the artifact; acceptance on
   induction-set performance alone is refused (the BORA tuning trap is the
   named anti-pattern: metrics tuned on the same 3–11 pages say nothing about
   new editions). Core expansion is out of scope here by definition; it may
   only be proposed later as a separate owner-approved change citing a
   profile's held-out record. This operationalizes sunset-9rg's "tested on
   held-out editions BEFORE expanding DSC core".

7. **Versioning.** Profile evolution is version-bump, never mutation: a changed
   rule set yields a new version with its own digest, its own induction inputs
   and its own validation record. Consumers pin the exact version + digest they
   used, under the deployed local-registry resolution semantics ("The URI is a
   lookup hint, not identity"; no latest-version fallback).

## Risks / Trade-offs

- **Overfitting to the tuning set.** → The held-out gate is normative, and
  BORA-derived expectations are explicitly non-transferable (caveats travel
  into every artifact and report).
- **Profiles encode a family's quirks, not document semantics.** → Declared
  scope + typed abstention keep the blast radius inside the wrapper; no core
  promotion without a separate owner-gated change.
- **Deterministic compile limits expressiveness** (no learned continuous
  models). → Accepted: inspectability and reproducibility are worth more than
  power at this stage; a proposal that cannot compile deterministically is
  refused at compile time, not approximated.
- **Abstention too eager** lowers wrapper utility. → Abstention outcomes are
  recorded events, so thresholds are tuned on measured abstention evidence at
  implementation time (owner-gated), not on vibes.

## Migration Plan

1. This change lands the capability definition only. Owner approval gate
   REQUIRED before any implementation ticket is filed (pattern: sunset-rmx.1).
2. Implementation change (future): induction module over recorded artifacts +
   wrapper application + RED-first tests; its ticket carries the caveat block
   from proposal.md verbatim.
3. First family chosen by the owner with real carriers; BORA numbers are never
   cited as accuracy claims, and any measured numbers produced then are labeled
   agent-executed with their scope.
4. Core expansion, if ever justified by a held-out record: separate change,
   owner-gated.

## Open Questions

1. Artifact format details and registry location for family profiles
   (workspace-side registry vs digitization run directory). Deferred to
   implementation; both keep profiles outside descriptors, so this does not
   affect the capability's requirements.
2. What counts as an "edition" for the held-out gate on a given family (same
   title, different date? different title, same producer?). Owner decision per
   family at implementation time; the gate itself (disjointness + recorded
   measured agreement) is fixed here.
