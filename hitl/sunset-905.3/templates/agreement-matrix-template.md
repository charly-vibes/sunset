# Agreement matrix — sunset-905.3 (orchestrator fills; readers do NOT touch)

One row per observable comparison across both readers' sheets. Classify every
cell; never elect a silent winner.

Legend: A = reader-a value, B = reader-b value. Agreement classes:

| Class | Meaning |
|-------|---------|
| AGREE | A == B (byte/semantically equal) |
| COMPATIBLE | A != B but both defensible (record both) |
| UNKNOWN | one or both said "unknown" |
| LOSS | observable flagged unrepresentable by one side |
| DISAGREE | conflicting observations, both asserted with evidence — retained, adjudication belongs to the human owner gate |

| Carrier | Observable | A | B | Class | Owner ruling |
|---------|-----------|---|---|-------|--------------|
| | | | | | |

## Per-carrier roll-up

| Carrier | observables | AGREE | COMPATIBLE | UNKNOWN | LOSS | DISAGREE |
|---------|-------------|-------|------------|---------|------|----------|
| diario-de-poesia-excerpt | | | | | | |
| agentic-patterns-excerpt | | | | | | |
| sunset-carrier-sample | | | | | | |
| bank-statement-ca-excerpt | | | | | | |

## Gate checklist (human owner)

- [ ] Both sheets received, sha256 recorded, elapsed minutes recorded
- [ ] Every DISAGREE row has an explicit owner ruling or is left retained-with-attribution
- [ ] Every LOSS entry survives into the published matrix (no silent drop)
- [ ] No `general-conformant` claim derived from this run alone
- [ ] Recorded-deviations note: agent-executed runs are superseded by this human pass
