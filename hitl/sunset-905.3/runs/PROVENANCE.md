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

---

## Update (2026-10-26): first real HUMAN baseline — reader-a

The owner completed the interactive annotator session for
`diario-de-poesia-excerpt` and returned
`runs/reader-a/diario-de-poesia-excerpt.observations.json` — the first
**human-executed** sheet (all prior sets in this directory are
agent-executed and labeled as such).

- Content: 6 pages inventoried (all image-only), 56 drawn page-relative
  regions (28 text / 12 image / 10 heading / 3 title / 2 header / 1 footer),
  elapsed 13 minutes.
- `relations`, `space`, `context`, `annotations`, `losses`,
  `uncertainties`, `notes` are empty — a single-human baseline covering the
  structure layer only.
- **Status: single-human baseline, NOT the two-independent-readers gate.**
  It supersedes the agent-executed sheets for this carrier where they
  conflict (human pass supersedes, per recorded-deviations policy) and
  serves as the reference set until reader-b returns.
- sha256: `60e0bd437953d19a7d1b14e9c5cd18c5f9fc41835cbd08ae8fceb01888fc313c`

## Update (2026-10-27): returned reader-b Diario sheet

Ingested unchanged from `../diario-de-poesia-excerpt-reader-b.observations.json`
into `reader-b/diario-de-poesia-excerpt.observations.json`.
SHA256: `8624a3518ae6d5edbcfe13c311dc3e21f245b4ad739a0464c1ccf33a0005bece`.
The loose reader-a sheet is byte-identical to the already ingested baseline
(`60e0bd437953d19a7d1b14e9c5cd18c5f9fc41835cbd08ae8fceb01888fc313c`).

Reader-b records 81 page-relative regions, all typed text, 6 page inventory
entries, 6 space entries, one context entry, and 16 elapsed minutes. Its
`prefill_provenance.order_ranks` is `derived_from_arrangement`: ranks are
not treated as independent human reading-order observations. Owner confirmed on 2026-10-27 that reader-b is a second human who worked
independently without seeing reader-a’s sheet or discussing the carrier.
The two-independent-human-readers condition is therefore met for Diario only. No source observations were normalized or corrected.

See `../agreement-matrix-diario-returned.org` for the scoped comparison and
remaining gates. Only Diario has a returned A/B pair; the native PDF, EPUB,
and financial-statement human pairs remain outstanding. The ticket remains
open pending these and the owner gate.

## Update (2026-10-27): owner authorizes regions-first type inference

Owner noted manual marking remains tedious and authorized using the regions
and inferring their types. Reader-b’s raw all-text values are retained but
not treated as deliberate human classifications for this experiment.
The assistant visually inspected all six carrier pages with numbered boxes
and produced `../inferences/diario-de-poesia-excerpt-reader-b.types.json`
and the readable `.org` companion. All 81 source boxes are preserved;
63 suggestions are clear and 18 tentative with alternatives. Source/carrier
digests bind the sidecar to the returned evidence. No reader-a labels were
transferred, but the agent had prior reader-a context: this is NOT an
independent reader run. No human acceptance is asserted. These machine
suggestions supplement, and do not replace, the human-only comparison.

## Owner scope update (2026-10-27): six returned PDF sheets

Owner accepts the six returned observations as the complete required input set for sunset-905.3. EPUB is waived for this ticket because the app does not render it. This is a scoped waiver, not EPUB conformance. The four new sheets use the same reader-a/reader-b identities as the previously confirmed independent human pair; no new reader execution was performed by the agent. Raw submissions are copied byte-for-byte.

```
ad87280135f2eb72913828ea71dd7a312d2b71d939187192f4bad50a62fc6c7a  reader-a/agentic-patterns-excerpt.observations.json
8703e6fb66566c1ee7bc2cd7b7df1d54d3cb95934a04406d51a016b9f7d1a45e  reader-b/agentic-patterns-excerpt.observations.json
594d7f7d971f33a391c4481124e2e63fd286435a7b266fcd40d12af43e8d3e0c  reader-a/bank-statement-ca-excerpt.observations.json
ccb06c3c032bc901922d476dcdd44dc853487f42f37517d07e53a61e37e9a4dc  reader-b/bank-statement-ca-excerpt.observations.json
```

These supersede the earlier statements that native-PDF and bank-statement pairs are missing. Blank types remain unclassified; derived ranks remain machine-derived; empty sections remain unknown. See ../agreement-matrix-human-returned.org for review. No broad conformance claim follows from receipt of the six sheets.
