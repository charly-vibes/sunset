## Context

Existing commands already return stable JSON with documented exit codes (0, 2, 3, 4, 5) and `provider_calls`. The new surface generalizes that idea: one outcome envelope, one reason-code vocabulary, one set of core functions.

## Goals / Non-Goals

Goals: a model can complete the document-to-verified-claims loop using only typed calls; no ambiguity about what is data and what is status; idempotent, resumable use.

Non-goals: authentication and multi-tenant serving; a hosted service; a GUI.

## Decisions

1. **Envelope.** `{status, reason, data, cursor?, provider_calls}`. `status` is from a closed vocabulary; `reason` is a stable code; `data` holds payloads.
2. **Read tools** (`open`, `words`, `crop`, `zoom_*`, `queue`) never mutate; **write tools** (`propose`, `decide`) are idempotent through claim ids.
3. **Addresses are anchors.** Scope arguments are ids from the identity profile; page indexes and labels are not accepted as addresses.
4. **Text is data.** Document text appears only under `data.text` fields, with an `untrusted: true` marker; no document text in `status`, `reason` or messages. Tool descriptions tell the model to treat these fields as data.
5. **Bounds.** Default page size and byte limits; cursors encode scope, offset and run digest so they are deterministic and refuse stale runs.
6. **Parity.** One core, n adapters. A conformance test runs the same script through every exposed adapter and compares outputs. The CLI adapter is phase 1; MCP is phase 2, built only when a model harness needs it (Necessity cuts in PROPOSAL-SET.md) — the parity requirement keeps any future MCP adapter from drifting.
7. **Export.** Contains claim, status, checks passed, anchors, coverage of the scope, and the run semantic digest. It never contains `rejected` claims.
8. **Packaging.** `pyproject.toml` moves from `package = false` to a build backend with a `sunset` console script — only after the AGPL review gate (below) passes.

## Risks / Trade-offs

- Marking text untrusted does not stop a model from following it. Mitigation: structural separation plus verifiers that never read model text as instructions; this is defence in depth, not a guarantee.
- Two adapters can drift. Mitigation: parity test in the gate.
- AGPL exposure begins at distribution (linking PyMuPDF into an installable wheel), not at repo-internal use. Mitigation: legal review task before any release; the repo-internal tool path is unaffected.

## Open Questions

1. Is MCP the first-class adapter or a thin layer over the CLI?
2. Which PyMuPDF licensing route does the project intend (AGPL-3.0 obligations accepted, or commercial)? Blocks packaging.
   **Ruled (owner, 2026-11-24, via sunset-gpd gate G4): AGPL-3.0 obligations accepted for repo-internal use; distribution stays out of scope.** Task 5.2 (packaging) remains gated on an explicit future licensing decision before any release.
