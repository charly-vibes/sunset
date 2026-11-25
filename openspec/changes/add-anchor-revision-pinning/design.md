# Design: Anchor revision pinning

## Context

`dsc03/evidence.py::replay` resolves an evidence record's bound selectors,
looks up the pinned profile, and applies the profile-declared text-range
grammar to the current descriptor content. It returns `replayed` whenever
application succeeds — with no comparison of the selector's pinned
`source_sha256` against the descriptor it is being applied to. The spec
(requirement "Selector source digest pinning") already mandates
digest equality, but that is enforced only at validation/build time; replay
itself performs no check, so a descriptor revised after anchoring replays
against new content and reports `replayed`.

## Where the check lives

1. **Replay entry — `dsc03/evidence.py::replay`.** Before resolving or
   applying any selector, for each internal selector (`kind != external`)
   compare `selector["source_sha256"]` to the descriptor source digest.
   Unequal → outcome `version_mismatch` with detail naming the selector id,
   pinned digest and current digest. No selector application runs; the
   revised content is never read by the selector grammar. External selectors
   keep their own pinned-external-digest rule (unchanged here).
2. **Profile schema — `dsc03/profiles.py`.** Selector profiles for
   text-range/anchor kinds gain a required `anchor_scheme_version` field
   (declared scheme version, e.g. `1`). Profile resolution refuses a profile
   without it — same refusal style as the existing required profile fields;
   no fallback, no default version.
3. **Spec enforcement — `openspec/specs/document-evidence/spec.md`**
   ("Selector source digest pinning", ~line 147). The delta makes the
   digest-equality SHALL also bind at replay entry, and adds the
   `anchor_scheme_version` requirement, so both layers state the same law.

## Why no `ambiguous` status

S1's vocabulary includes `ambiguous`. At replay it is unreachable and would be
dead vocabulary: text-range application under a pinned profile is
deterministic — same grammar, same offsets, same input value always yields the
same span or a typed failure (`invalid_selector`). Ambiguity in the S1 sense
lives in projection comparison (two descriptors mapping to one projection) and
locator resolution (one locator naming several targets); both are owned by
other capabilities and are out of scope here. Adding an `ambiguous` replay
status would invite silent use as a catch-all — the opposite of typed
outcomes. Ruled: no `ambiguous` status in this change.

## Zero-call replay compatibility

`replay` keeps its signature and return contract (`(status, detail)`). Existing
statuses (`replayed`, `dangling_reference`, `unsupported_profile`,
`invalid_selector`, `unreplayable`, `replay_mismatch`, `lineage_cycle`) are
unchanged and continue to fire in the same situations for digest-equal
descriptors. The only behavioral delta is on descriptors whose digest differs
from a selector's pin: previously `replayed` (wrongly), now
`version_mismatch`. Call sites that switch on status already handle unknown
statuses as failures by contract, and the conformance corpus gains the new
outcome explicitly, so no caller is silently broken.

## Risks / Trade-offs

- Descriptors legitimately re-anchored after revision will now fail replay
  with `version_mismatch` instead of `replayed`. Mitigation: that is the
  honest outcome; re-anchoring must produce selectors pinned to the new
  digest (new selector ids), making the revision explicit.
- A profile field addition could reject legacy pinned profiles. Mitigation:
  profiles are pinned by digest in run configuration; adding
  `anchor_scheme_version` is part of pinning a new profile, and the refusal
  reason names the missing field.

## Rationale summary

Rule-of-5 found a silent false-accept class (cross-revision replay). S1 asks
for explicit version-mismatch on revision change. The narrowest honest fix is
one precondition at the replay entry plus one pinned profile field — no new
statuses beyond what the law requires, no touching of projection or locator
semantics.
