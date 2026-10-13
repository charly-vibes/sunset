# Project Context

## Purpose

`sunset` hosts the **DSC (Document Structural Core)** specification for
document descriptors: multiple structural views, source-addressable selectors,
explicit interpretation provenance, and honest extraction coverage.

Current executable truth is the **DSC 0.2** baseline, implemented by
`spec/document-model-specodelic-v3/validator.py` (reference validator, frozen
at 0.2). The **DSC 0.3** contract is a design proposal tracked as the OpenSpec
change `add-dsc-03` — never described as implemented.

## Tech Stack

- Markdown specifications (OpenSpec standard: `openspec/specs/<capability>/spec.md`)
- Reference validator: Python 3 (`validator.py`, stdlib only)
- `bd` for issue tracking; `.org` notes; fleet conventions per dulce-de-leche

## Project Conventions

### Code Style
- Requirements are normative (EARS: SHALL) with at least one `#### Scenario:` each.
- Version scoping is explicit: deployed specs under `openspec/specs/` describe
  the **0.2 baseline**; 0.3 rules live only in `openspec/changes/add-dsc-03/`.
- The specodelic-format research bundle (`spec/document-model-specodelic-v3/`)
  is provenance for these specs; its `specs/` were converted to OpenSpec format
  and are NOT duplicated here.

### Testing Strategy
- `python3 spec/document-model-specodelic-v3/validator.py test` must keep
  reporting `PASS 11 descriptor fixtures`.
- `openspec validate --specs --strict` and
  `openspec validate add-dsc-03 --strict` must pass.
- Property traces (which fixture exercises which requirement) live in the
  scenario text, mirroring the bundle's Properties tables.
- `python3 -B -m unittest discover -s tests -v` exercises actual OpenSpec
  composition in an isolated temporary workspace. Changed baseline rules
  must be replaced, not retained beside contradictory additions.
- Active 0.3 capability deltas supersede conflicting details in the immutable
  research draft; rationale is in `changes/add-dsc-03/design.md`. Specification
  checks do not establish 0.3 descriptor or real-carrier conformance.
