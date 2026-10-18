# Provenance — sunset-905.3 agent-executed reader-sheet ingest

**Owner ruling (b), 2026-10-18**: the two reader sheet sets returned via
`~/cotorreo/` are ingested here as a labeled **agent-executed agreement run**.
They do **not** satisfy the two-independent-human-readers gate of
sunset-905.3; per the recorded-deviations policy a human pass supersedes
them. No conformance claim derives from this run alone.

## What was ingested

| Reader | Source (cotorreo) | Returned | Sheets | Notes |
|--------|-------------------|----------|--------|-------|
| `reader-claude` | `raw/_conversations/claude/cad1063c-32de-40be-8f76-d2d2abb17926/artifacts/reader-claude.zip` (2026-10-16) | 4 sheets + notes.md | yes | full deviation record in `reader-claude/notes.md` |
| `reader-grok` | `raw/_conversations/grok/bdf8e4c6-89fd-4ca9-954b-cee6acfa1fe6/artifacts/` (2026-10-16) | 4 sheets + truncated-digest manifest (`source-manifest.json`) | yes | no notes.md was returned |

A third set (`reader-mistral`, `raw/_conversations/mistral-work/42213cbc-…`)
was **not ingested**: its bundle copy lacked `sunset-carrier-sample.epub`
(sheet derived from the sidecar JSON only) and no carrier digest could be
verified (`sha256sum` broken in that environment). It remains retrievable
from cotorreo if the owner wants it compared.

## Sheet digests (sha256, as ingested)

```
9fca591d16a7ea68f735a6d9703345a675e53a5dd233a958f94e256c4d8e8bc3  reader-claude/bank-statement-ca-excerpt.observations.json
a2d92da50b67790e49e061b331470aee5f1122d049051f298e76af72b864708f  reader-claude/agentic-patterns-excerpt.observations.json
1cadacb365b9620dbc31c7a607e162f0eb0ca294c4a17bc379fab1fad3a3e2c1  reader-claude/diario-de-poesia-excerpt.observations.json
812e96c848f979fb5f10860b98837988e61cc3a1ab9f0af0f19b6f2a3ea92866  reader-claude/sunset-carrier-sample.observations.json
4344e8bba539c880b2e4887ab3b55e33c96e429176f717dd1db785cc82622fce  reader-grok/bank-statement-ca-excerpt.observations.json
c769dad495218ca1d47cfb5e768de23e5790338c4f94b71bd541f476ff09c392  reader-grok/agentic-patterns-excerpt.observations.json
765a94b1b5785791d0e26e1cedf4134744e86011c14f2d3fe7942581d29f9adc  reader-grok/diario-de-poesia-excerpt.observations.json
41d3fecc3a717c4b60abfa89a91faaf093612140062894b020069beaa40764b2  reader-grok/sunset-carrier-sample.observations.json
```

The `reader-grok` digests match the first 16 hex characters of its returned
`source-manifest.json` (the grok platform truncates); `reader-claude`
checksummed its own copies against the bundle's `SHA256SUMS.txt` (recorded
in its notes).

## Recorded deviations (both readers are AI models, not humans)

- **reader-claude** (see `reader-claude/notes.md`): rendered PDF pages to
  PNG and viewed them; read EPUB XHTML/OPF directly (no reflowing viewer);
  **read the shipped reader-A annotation texts before writing sheets** —
  not independent of the shipped annotations (recorded per-field in its
  `uncertainties`); `elapsed_minutes: null`; never tested text selection.
- **reader-grok**: no deviation notes were returned; method inside the
  sheets cites evidence per entry but viewer usage is unrecorded. Treated
  as agent-executed with unknown method detail.

Gate checklist consequence: the two items "sha256 recorded" and "sheets
received" are met for this agent run; the human-gate items (independent
human readers, owner rulings on DISAGREE rows) remain **open**.
