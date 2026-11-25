# Tasks

## 1. Replay digest-equality (RED first)

- [ ] 1.1 RED `tests/tracer/test_evidence_replay.py`: tamper descriptor content after anchoring (selector `source_sha256` no longer equals descriptor digest) → `replay` returns `version_mismatch` with detail naming selector id, pinned digest, current digest; observation dict is empty — revised text is never read by the selector grammar.
- [ ] 1.2 GREEN `dsc03/evidence.py`: digest-equality precondition at `replay` entry, before selector resolution/application; internal selectors only (external keeps its pinned-external-digest rule).

## 2. Anchor scheme version

- [ ] 2.1 RED `tests/tracer/test_evidence_replay.py`: replay with a selector profile lacking `anchor_scheme_version` → profile resolution refuses; no selector application, no `replayed`.
- [ ] 2.2 GREEN `dsc03/profiles.py`: required `anchor_scheme_version` on text-range/anchor selector profiles; refusal reason names the missing field; no default version.

## 3. Digest-equality enforcement breadth

- [ ] 3.1 RED `tests/test_substrate_gates.py`: validator/resolve path refuses an internal selector whose `source_sha256` differs from the descriptor source digest (build-time counterpart to the replay precondition).
- [ ] 3.2 GREEN: align `dsc03/validator.py` / resolve enforcement with the spec SHALL; identical digest-equal inputs unchanged.

## 4. Conformance corpus

- [ ] 4.1 Update the conformance corpus (`tests/test_substrate_gates.py` fixtures) with a `version_mismatch` case and a refused profile case; both validators pass; existing `replayed` cases byte-identical for digest-equal descriptors.
- [ ] 4.2 Docs: `dsc03/evidence.py` header/docstring lists `version_mismatch` among statuses; design.md "no ambiguous" ruling remains the record.
