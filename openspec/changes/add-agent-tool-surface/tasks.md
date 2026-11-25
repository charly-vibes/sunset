## 1. Legal gate (blocks packaging, not development)

- [x] 1.1 Record the owner's PyMuPDF licensing decision (AGPL-3.0 vs commercial) in design.md; do not merge any packaging change before it

## 2. Core and envelope

- [x] 2.1 Envelope `{status, reason, data, cursor?, provider_calls}` with closed status vocabulary and stable reason codes
- [x] 2.2 RED: unknown scope returns typed refusal, never an exception

## 3. Tools

- [x] 3.1 Read tools: `open`, `words`, `crop`, `zoom_in`, `zoom_out`, `queue` — never mutate
- [x] 3.2 RED: write tools idempotent through claim ids (`propose`, `decide`)
- [x] 3.3 RED: label or index addresses refused; anchor ids only
- [x] 3.4 RED: document text only in `data.text` with `untrusted: true`; hostile-text fixture asserts no leakage into status/reason/messages
- [x] 3.5 RED: size bounds and deterministic cursors; stale run digest refused

## 4. Export

- [x] 4.1 RED: export excludes unaudited types and rejected claims; includes checks passed, anchors, coverage, run digest

## 5. Adapters and packaging

- [x] 5.1 RED: parity script produces identical outcomes through every exposed adapter (phase 1: CLI)
- [x] 5.2 pyproject build decision and `sunset` console script (after task 1.1)
- [x] 5.3 Gate: parity + leakage + idempotence tests wired into `just` targets
- [ ] 5.4 Deferred (phase 2): MCP adapter — only when a model harness needs it; parity requirement already covers it
