# Change: Typed agent tool surface with CLI/MCP parity

## Why

For models to use Sunset reliably it must present a small, typed, stable surface instead of a Python module run from a checkout. Today the CLI exposes six operations (`run`, `inspect`, `resume`, `replay`, `evaluate`, `native` in `digitization/__main__.py`) with positional page lists and file paths, and has no way for a model to read a scope, submit claims or fetch the queue. Document text is also untrusted input: a tool that returns page text next to instructions or status fields invites prompt injection.

Packaging partially exists at HEAD: `pyproject.toml` pins the runtime (`name = sunset`, `PyMuPDF==1.28.2`) with `package = false` and no console script — an installable entry point still needs a build decision.

## What Changes

- Define a tool surface with CLI parity first (`open`, `words`, `crop`, `zoom_in`, `zoom_out`, `propose`, `queue`, `decide`, `export`); the MCP adapter is phase 2, gated on a model harness needing it. The parity requirement governs every exposed adapter, so an MCP adapter can be added later without spec change.
- Every response is typed, with stable reason codes, and never an exception.
- Scopes and claims are addressed by anchor-derived ids, not labels or indexes.
- Document text is returned only in dedicated data fields.
- Responses are size-bounded with deterministic cursors.
- `export` returns only claims that satisfy the autonomy gate or a human accept, together with the checks passed and coverage.

## Impact

- Affected specs: new capability `document-agent-interface` (all requirements ADDED).
- Depends on all adopted changes in this set; delivered last.
- Affected code: new `sunset/` entry package with `cli` and `mcp` adapters over the same core functions; `digitization/__main__.py` retained for existing commands; `pyproject.toml` gains the build/entry-point decision.
- **Legal gate:** the PyMuPDF licence (AGPL-3.0, or commercial from Artifex) versus this repository's Apache-2.0 licence is a required review item before any release; no packaging change is merged until resolved. Not legal advice — owner decision required.
