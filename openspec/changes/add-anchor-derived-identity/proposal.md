# Change: Anchor-derived record identity, canonical set order, and exact quantized geometry

## Why

DSC 0.3 identifies records by producer-local labels (`pg3`, `native-page-4`, `txt1`, `an3-…`). Labels are positional, so the same observation gets different ids across runs, page selections and operand orders. Verified at HEAD, 2026-11-24:

- `dsc03/substrate/assembly.py::compose` keeps "left operand's items first" (line 29), so canonical bytes depend on operand order and assembly cannot be commutative.
- `digitization/native.py::_descriptor` re-associates annotations to pages by string-prefix matching on ids (`an{page}-`, lines 150-151).
- `dsc03/compare.py` refuses edition matching by title/filename (`no_edition_guess`) and probes declared identity only for transformations (`probe_identity`); there is no record-identity convention to inherit — identity by anchor must be built.
- `dsc03/substrate/space.py` declares tolerance 0 only "for this fixture family" where positions are integers (line 47); native output carries 17-digit float boxes (e.g. `247.86300659179688` in `line-map.json`), so the exact-transform claim cannot carry to real PDFs.

Parallel model workers, order-independent merging, and deterministic replay all need identity that is a function of *what was observed and where*, not of the order the producer happened to emit it.

## What Changes

- Add an optional **identity profile** (pinned like selector/geometry profiles) under which record ids are digests of their anchor tuple.
- Under that profile, set-like sections serialize in ascending id order; sequence meaning is carried only by explicit relations.
- Under that profile, geometry is integer-valued in a declared quantum with a declared rounding rule; quantization is recorded as an explicit transform.
- Migration from label ids emits a recorded old→new table as evidence.
- No existing descriptor becomes invalid. Label-id descriptors remain valid without the profile; the profile is opt-in per descriptor.

## Impact

- Affected specs: new capability `document-identity` (all requirements ADDED); task 1.1 audits deployed `document-core` and `document-evidence` for array-position reliance — any resulting MODIFIED delta is a follow-up, not guessed here.
- Affected code: `dsc03/validator.py`, `dsc03/canonical.py` (both readers), `dsc03/migrate.py`, `dsc03/substrate/assembly.py`, `digitization/native.py`.
- The frozen 0.2 validator is untouched.
- Blocks: `add-scale-complete-regions`, `add-claim-verification-ladder`; unblocks the join-law tasks in `define-document-composition-semantics`.
- No conformance label changes. Results are machinery-level and agent-executed.
