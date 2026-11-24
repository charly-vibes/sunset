# Tasks: Document-family profile induction

Proposal-only change. Every task below stays unticked until the owner
approval gate (0.1) passes; no implementation exists in this change.

## 0. Owner gate (blocks all implementation)

- [ ] 0.1 Owner approves this proposal; only then may an implementation ticket be filed (pattern: sunset-rmx.1)
- [ ] 0.2 Implementation ticket carries the caveat block (proposal.md, Anti-goals item 2: proxy metrics, 3–11 BORA pages, no LLM evaluation executed, internal ownership checks) verbatim

## 1. Profile artifact and induction loop (RED-first)

- [ ] 1.1 RED: compiling the same recorded inputs with the same compiler version twice yields byte-identical rules
- [ ] 1.2 RED: profile artifact declares id, version, sha256 over exact bytes, family scope, induction input digests, compiled rules, counterexample record, held-out validation record, caveats; a missing field is a typed refusal
- [ ] 1.3 Each loop stage (observe → discover → propose → counterexample-test → compile → validate) records its inputs; discovery and proposal consume recorded artifacts only
- [ ] 1.4 Profile evolution is version-bump: a changed rule set produces a new version with its own digest and validation record, never a mutation of an existing one

## 2. Wrapper application (RED-first)

- [ ] 2.1 RED: a profile-derived contribution to a descriptor is an evidence record whose transform names the profile id + version + sha256 among its pinned dependencies, with origin `inferred`
- [ ] 2.2 RED: failing a declared precondition or insufficient evidence yields a typed abstention outcome naming the unsatisfied condition, and nothing profile-derived is emitted
- [ ] 2.3 Output produced without a firing profile is labeled unprofiled (absence of profile coverage distinguishable from profile-derived structure)
- [ ] 2.4 RED: profile-derived graphic-region candidates keep `interpretation_status: "hypothesis"` and are never emitted as source observations or promoted by the profile
- [ ] 2.5 RED: a projection of profile knowledge without declared provenance is not applied (typed refusal, per O-A04)

## 3. Gates

- [ ] 3.1 RED: acceptance without a held-out validation record is refused; induction-set performance alone never justifies acceptance
- [ ] 3.2 Held-out editions are disjoint from induction inputs (checked, not asserted) and reconstruction agreement is measured and recorded in the artifact
- [ ] 3.3 RED: an unresolved counterexample keeps the profile rejected
- [ ] 3.4 RED: applying a compiled profile performs zero model/provider/network calls in the profile-application step (recorded, testable)

## 4. Honesty

- [ ] 4.1 Caveats travel: the artifact and every report citing profile-derived measurements carry the induction-declared caveats
- [ ] 4.2 Any measured number is labeled agent-executed with its scope; BORA numbers are never cited as accuracy or conformance claims
- [ ] 4.3 Core expansion appears in no task: promoting any profile-derived mechanism into normative DSC core requires a separate owner-approved change citing a held-out record
