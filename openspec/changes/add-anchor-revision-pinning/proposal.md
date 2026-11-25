# Change: Anchor revision pinning — `version_mismatch` on cross-revision replay

## Why

Rule-of-5 review of `dsc03/evidence.py::replay` found that evidence replay never
compares a selector's pinned `source_sha256` against the current descriptor
source digest: when descriptor content changed since anchoring, replay still
applies the stored text-range grammar to the *revised* text and returns
`replayed`. That is silent cross-revision reinterpretation of evidence — the
replayed observation is no longer the observation that was anchored.

The Bajan capability-gap audit (S1, `bajan_sunset_reusable_capability_gaps.md`)
requires outcome vocabulary `resolved / ambiguous / unavailable` with an
explicit version-mismatch signal on revision change. This change implements the
version-mismatch half of S1 for evidence replay; the `ambiguous` replay status
is explicitly ruled out (see design — text-range application is deterministic,
so ambiguity cannot arise at replay, only in projection comparison and locator
resolution, which this change does not touch).

## What Changes

- Add a `version_mismatch` outcome to selector replay: emitted when a
  selector's pinned `source_sha256` differs from the current descriptor source
  digest, INSTEAD of replaying — revised content is never silently
  reinterpreted.
- Require text-range/anchor selector profiles to declare an
  `anchor_scheme_version`; a profile without it is refused at profile
  resolution.
- Enforce digest equality in replay entry (`dsc03/evidence.py::replay`) as a
  precondition before any selector application; the existing validator
  (`spec.md` "Selector source digest pinning") keeps build-time enforcement.
- Zero call-site changes: `replayed` stays the outcome for digest-equal
  descriptors; existing conformance behavior is unchanged except for the new
  honest outcome on tampered descriptors.

## Impact

- Affected specs: capability `document-evidence` — requirement
  "Selector outcome codes" MODIFIED (adds `version_mismatch`); one requirement
  ADDED (anchor scheme version + replay digest-equality precondition).
- Affected code: `dsc03/evidence.py` (replay entry), `dsc03/profiles.py`
  (selector profile schema gains `anchor_scheme_version`),
  `tests/tracer/test_evidence_replay.py`, `tests/test_substrate_gates.py`
  (conformance gate for the corpus).
- No new core relation kind; no wire-format change — `version_mismatch` is a
  new value of the existing typed outcome.
- Out of scope: `ambiguous` replay status (unreachable; see design.md),
  projection comparison, locator resolution.
