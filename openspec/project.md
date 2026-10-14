# Project Context

## Purpose

`sunset` hosts the **DSC (Document Structural Core)** specification for
document descriptors: multiple structural views, source-addressable selectors,
explicit interpretation provenance, and honest extraction coverage.

Current executable truth is the **DSC 0.2** baseline, implemented by
`spec/document-model-specodelic-v3/validator.py` (reference validator, frozen
at 0.2). The **DSC 0.3** machinery is implemented in the `dsc03/` package
(archived OpenSpec change `add-dsc-03`, deployed to the deployed specs
2026-10-15); no real-carrier conformance is claimed, and agent-executed
review deviations are recorded in `docs/src/status.md`.

## Tech Stack

- Markdown specifications (OpenSpec standard: `openspec/specs/<capability>/spec.md`)
- Reference validator: Python 3 (`validator.py`, stdlib only)
- `bd` for issue tracking; `.org` notes; fleet conventions per dulce-de-leche

## Project Conventions

### Code Style
- Requirements are normative (EARS: SHALL) with at least one `#### Scenario:` each.
- Version scoping is explicit: deployed specs under `openspec/specs/` carry
  both the **0.2 baseline** and the **deployed 0.3 updates** (from archived
  change `openspec/changes/archive/2026-10-14-add-dsc-03/`); no other active
  deltas exist.
- The specodelic-format research bundle (`spec/document-model-specodelic-v3/`)
  is provenance for these specs; its `specs/` were converted to OpenSpec format
  and are NOT duplicated here.

### Testing Strategy
- `python3 spec/document-model-specodelic-v3/validator.py test` must keep
  reporting `PASS 11 descriptor fixtures`.
- `openspec validate --specs --strict` must pass (7 capabilities).
- Property traces (which fixture exercises which requirement) live in the
  scenario text, mirroring the bundle's Properties tables.
- `python3 -B -m unittest discover -s tests -v` exercises actual OpenSpec
  composition in an isolated temporary workspace. Changed baseline rules
  must be replaced, not retained beside contradictory additions.
- Full 0.3 machinery suite: `just spec-check` (pytest over `tests/tracer/`,
  144 tests) plus the frozen-0.2 sanity check.
- The deployed 0.3 specs supersede conflicting details in the immutable
  research draft; rationale is in
  `openspec/changes/archive/2026-10-14-add-dsc-03/design.md`. Specification
  checks and the scripted 0.3 suite do not establish real-carrier
  conformance; labels come only from `dsc03/conformance.py`.
