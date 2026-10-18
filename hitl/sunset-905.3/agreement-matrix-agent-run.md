# Agreement matrix — sunset-905.3 agent-executed run (grok × claude)

**Status: AGENT-EXECUTED — does NOT satisfy the two-human-readers gate.**
Owner ruling (b), 2026-10-18: reader-grok and reader-claude sheets (returned
via cotorreo) ingested and compared as a labeled agent-executed agreement
exercise. Per the recorded-deviations policy a human pass supersedes this
run; no conformance claim derives from it. See `runs/PROVENANCE.md`.

Legend: **A** = reader-grok value, **B** = reader-claude value.

| Class | Meaning |
|-------|---------|
| AGREE | A == B (semantically equal) |
| COMPATIBLE | A != B but both defensible (both recorded) |
| UNKNOWN | one or both said "unknown" / did not record |
| LOSS | observable flagged unrepresentable by one side |
| DISAGREE | conflicting observations, both asserted with evidence — retained, adjudication belongs to the human owner gate |

## diario-de-poesia-excerpt

| Observable | A (reader-grok) | B (reader-claude) | Class | Owner ruling |
|-----------|-----------------|-------------------|-------|--------------|
| Page count | 6 pages | 6 pages | AGREE | — |
| `page_inventory[*].image_only` | `true` ×6 (asserted) | `"unknown"` ×6 (never tested selection) | UNKNOWN | — |
| Cover: "Segunda Edición", "Invierno de 1986" | observed, p1 | observed, p1 | AGREE | — |
| Continuation cover → Editorial ("Sigue en pág. 2") | p1 → p2, quoted fragments | p1 → p2, quoted fragments | AGREE | — |
| Continuation "Concursos" → absent pages | "page not present" | pp. 37, 34 (named targets) | COMPATIBLE | — |
| Reference "Entre las páginas 11 y 23…" | p1 → pp. 11–23 (absent) | p1 → pp. 11–23 (absent) | AGREE | — |
| Sumario → folio references (3, 4, 18, 35) | not recorded | recorded with folio mapping | UNKNOWN | — |
| Structure granularity | 5 coarse labels | 11 fine-grained labels, superset | COMPATIBLE | — |
| Page 4 content | "continuation of Ginsberg reportaje + photos/columns" | "4/POESIA NORTEAMERICANA — Sudario Blanco (poem, trad. Stupía)" | DISAGREE | retained |
| Pages 5–6 content | "further interior (poetry/dossier)" | "18/DOSSIER JUANELE", "35/AGENDA" (identified) | COMPATIBLE | — |
| `space[*].rotation` | 0 ×6 | 0 ×6 | AGREE | — |
| `space[*].columns` | multi ×6 | multi ×6 | AGREE | — |
| `reading_order_ambiguous` p3 | `false` | `true` | DISAGREE | retained |
| `reading_order_ambiguous` p1, p2, p5, p6 | `true` | `true` | AGREE | — |
| `publication_date` | "Invierno de 1986 (Segunda Edición); Año 1 · Número 1" | "Invierno de 1986" (+ Junio 1986 colophon kept as uncertainty) | COMPATIBLE | — |
| `publisher_or_source` | Juegos & Co. S.R.L. | Juegos & Co. S.R.L. + AHIRA scan watermark | COMPATIBLE | — |
| `author_or_attribution` | Director Daniel Samoilovich; Dir. Arte Juan P. Renzi | same | AGREE | — |
| `quoted_material` | Cummings (cover); Ginsberg material | Cummings (cover); Ginsberg poem/speech | AGREE | — |
| Annotations visible in carrier | none observed (0) | Text@p1 + Square@p1 | DISAGREE | retained |
| `losses` recorded | 3 entries | 5 entries (superset incl. scan quality) | COMPATIBLE | — |

## agentic-patterns-excerpt

| Observable | A (reader-grok) | B (reader-claude) | Class | Owner ruling |
|-----------|-----------------|-------------------|-------|--------------|
| Page count | 6 pages | 6 pages | AGREE | — |
| `page_inventory[*].image_only` | `false` ×6 (native text) | `"unknown"` ×6 | UNKNOWN | — |
| Title + subtitle | "Agentic Patterns" + subtitle | same | AGREE | — |
| TOC chapter rows (Foundations … Advanced Agents) | enumerated row-by-row | same chapters, grouped entry | COMPATIBLE | — |
| TOC page-break continuations (p1→2→3→4) | not recorded | recorded, quoted breakpoints | UNKNOWN | — |
| References pages (folios 350, 399) | entries 2–30 / ~12–36 | same + p6 starts mid-URL of item 12 | COMPATIBLE | — |
| Continuity of pp. 5–6 with the TOC | flagged uncertain (fragments?) | flagged uncertain (continuation 5→6) | COMPATIBLE | — |
| `space[*]` | rot 0 / single / unambiguous ×6 | same ×6 | AGREE | — |
| `context` (all 4 kinds) | unknown / observed_absent | unknown / observed_absent | AGREE | — |
| Annotations visible in carrier | none observed (0) | Text@p1 + Highlight@p1 | DISAGREE | retained |
| `losses` recorded | 1 entry | 3 entries (superset) | COMPATIBLE | — |

## sunset-carrier-sample

| Observable | A (reader-grok) | B (reader-claude) | Class | Owner ruling |
|-----------|-----------------|-------------------|-------|--------------|
| Spine: 2 chapters; nav not in spine | 2 spine items + nav in structure | 2 spine items + nav listed as non-spine page | COMPATIBLE | — |
| Chapter titles | "Chapter 1: Sample Observations", "Chapter 2: More Observations" | same | AGREE | — |
| nav.xhtml → chapter references | recorded | recorded | AGREE | — |
| Continuation ch1 → ch2 | not recorded | recorded | UNKNOWN | — |
| `publication_date` | 2026-10-14 (`dcterms:modified` in package, observed) | unknown (observed_absent) | DISAGREE | retained |
| `publisher_or_source` | "Sunset fixture generator (creator)" | publisher unknown; author = Sunset fixture generator | COMPATIBLE | — |
| `author_or_attribution` | Sunset fixture generator | Sunset fixture generator | AGREE | — |
| `quoted_material` | none (observed_absent) | none (observed_absent) | AGREE | — |
| Annotations (3: Highlight p1, Text p1, Highlight p2) | recorded | recorded (anchoring uncertain, sidecar-derived) | AGREE | — |
| `space[*]` | rot 0 / single / unambiguous | unknown / unknown / unambiguous | UNKNOWN | — |
| `page_inventory[*].image_only` | `false` ×2 | `false` ×2 | AGREE | — |
| `losses` recorded | 2 entries | 3 entries (superset) | COMPATIBLE | — |

## bank-statement-ca-excerpt

| Observable | A (reader-grok) | B (reader-claude) | Class | Owner ruling |
|-----------|-----------------|-------------------|-------|--------------|
| Single page | 1 page | 1 page | AGREE | — |
| `page_inventory[1].image_only` | `false` | `"unknown"` | UNKNOWN | — |
| Three content lines (header / Caja de Ahorro ARS / SALDO ANTERIOR 1.234,56) | observed | observed | AGREE | — |
| Relations | none | none | AGREE | — |
| `space[1]` | rot 0 / single / unambiguous | rot 0 / single / unambiguous | AGREE | — |
| `publication_date` | 21/09/2017 | 21/09/2017 (+ day/month/year reasoning) | AGREE | — |
| `publisher_or_source` | Banco Mock | Banco Mock | AGREE | — |
| `author_or_attribution` | unknown (observed_absent) | unknown (observed_absent) | AGREE | — |
| `quoted_material` | none (observed_absent) | none (observed_absent) | AGREE | — |
| Annotations visible in carrier | 1 Highlight@p1 (unsure whether embedded) | 2: Text@p1 + Highlight@p1 | DISAGREE | retained |
| Number format "1.234,56" (es-AR; currency?) | not flagged | flagged as uncertainty (currency unknown) | UNKNOWN | — |
| `losses` recorded | 1 entry | 3 entries (superset) | COMPATIBLE | — |

## Per-carrier roll-up

| Carrier | observables | AGREE | COMPATIBLE | UNKNOWN | LOSS | DISAGREE |
|---------|-------------|-------|------------|---------|------|----------|
| diario-de-poesia-excerpt | 20 | 9 | 6 | 2 | 0 | 3 |
| agentic-patterns-excerpt | 11 | 4 | 4 | 2 | 0 | 1 |
| sunset-carrier-sample | 12 | 6 | 3 | 2 | 0 | 1 |
| bank-statement-ca-excerpt | 12 | 8 | 1 | 2 | 0 | 1 |
| **total** | **55** | **27** | **14** | **8** | **0** | **6** |

## Cross-run observations (agent-orchestrator, retained not resolved)

- All 6 DISAGREE rows share one pattern: **reader-grok asserted facts
  reader-claude recorded as unknown or absent** (page-4 content, p3 reading
  order, carrier annotations, EPUB metadata date, bank annotations).
  Reader-claude's method notes (no selection test, viewer-less EPUB read)
  plausibly explain the UNKNOWN skew; reader-grok returned no method notes,
  so its assertions cannot be cross-checked. Adjudication is left to the
  human owner gate.
- The two annotation DISAGREE rows are conformance-relevant: reader-claude
  saw the shipped reader-A/B annotation layers in page renders; reader-grok
  recorded none. The carriers DO carry annotations (they were shipped in),
  so this is a candidate extractor-risk finding — retained, not elected.
- LOSS count is 0 because both readers recorded losses as free-form
  entries (counts compared under COMPATIBLE); no observable was flagged
  unrepresentable by exactly one side.
- reader-claude declared itself not independent of the shipped annotation
  texts (read them via a PDF library); rows touching those annotations are
  marked in its `uncertainties` and inherit that caveat.

## Gate checklist (human owner)

- [x] Both sheet sets received, sha256 recorded (`runs/PROVENANCE.md`)
- [ ] **Two independent HUMAN readers** — NOT satisfied by this run; open
- [ ] Every DISAGREE row has an explicit owner ruling (6 rows retained-with-attribution)
- [x] Every LOSS entry survives into the published matrix (none dropped)
- [x] No `general-conformant` claim derived from this run alone
- [x] Recorded-deviations note: agent-executed runs are superseded by a human pass
