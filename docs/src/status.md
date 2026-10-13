> *I scanned the menu options*
> *I did not have a choice*
> *I'd like to teach the world to sing*
> *But I do not have a voice*
>
> — A Sunset, PULP

# Status

**sunset** is **experimental**.

- Hosts the DSC (Document Structural Core) specification proposal.
- Executable truth: DSC 0.2 only — `spec/document-model-specodelic-v3/validator.py`
  (frozen at 0.2), `PASS 11 descriptor fixtures`.
- DSC 0.3 is a design proposal: see
  [`openspec/changes/add-dsc-03/`](../../openspec/changes/add-dsc-03/proposal.md).
  No 0.3 validator, profiles, adapters, or benchmarks exist.
- No CLI ships from this repo yet; ddl registry onboarding is tracked in
  beads (`sunset-408`).

## Deviations from the fleet standardization checklist

Recorded deviations (onboarding checklist §7 items deliberately deferred
until a CLI ships — tracked in beads `sunset-408`):

- No CI workflow files (`just ci` arrives with an implementation; the spec
  gates run via `just spec-check` for now)
- No `book.toml`/theme or book pages
- No `llms.txt` / `llm.txt`
- Not registered in ddl's registry, capability matrix, or dogfood matrix
- The research bundle's `specs/` were relocated to `openspec/` (single source
  of truth) — the recorded exception to "preserved as received" in the root
  [AGENTS.md](../../AGENTS.md)

## Acceptance gates for the 0.3 proposal

The falsifiable release gates live in the bundle's
[ACCEPTANCE.md](../../spec/document-model-specodelic-v3/ACCEPTANCE.md); the
per-capability deltas are in
[`openspec/changes/add-dsc-03/`](../../openspec/changes/add-dsc-03/proposal.md).
