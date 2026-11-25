---
id: document.adapters.layer
kind: intent
statement: "WHEN existing human region observation sheets are imported into DSC, THE human-sheet adapter SHALL preserve every attributed region or refuse explicitly, without modifying source sheets or requiring DSC core wire changes."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| source_immutable | invariant | `Import does not alter source sheets and requires no DSC core wire changes` | [[document.adapters.layer]] |
| total_accounting | invariant | `Every input region is preserved with pinned source/sheet provenance or accounted for by an explicit typed unresolved/refusal result` | [[document.adapters.layer]] |
| sheet_scoped_ids | invariant | `Local IDs are scoped to the originating sheet so identical local IDs from different sheets remain distinct` | [[document.adapters.layer]] |
| no_inferred_judgment | invariant | `Blank types, machine-inferred types and derived order never become independent human judgments` | [[document.adapters.layer]] |
| declared_frames | invariant | `Resolvable boxes use a declared coordinate profile and a validated DSC selector; digest mismatch, invalid box or missing frame yields typed refusal or unresolved, never guessed geometry` | [[document.adapters.layer]] |
| real_browser_gate | invariant | `Acceptance of the attributed import journey SHALL execute an actual browser and SHALL fail when the browser runtime is unavailable; modeled interaction alone does not satisfy it` | [[document.adapters.layer]] |

## Model

### States
- `sheets_received`
- `validated`
- `imported`
- `partially_refused`
- `unsupported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| check_frames | sheets_received | validated | source/sheet provenance pinned and coordinate frames classifiable [[document.adapters.layer.source_immutable]] [[document.adapters.layer.declared_frames]] |
| import_all | validated | imported | every region preserved with attribution; sheet-scoped IDs recorded [[document.adapters.layer.total_accounting]] [[document.adapters.layer.sheet_scoped_ids]] |
| import_with_refusals | validated | partially_refused | each unresolved region returns a typed result with its input region reference [[document.adapters.layer.total_accounting]] [[document.adapters.layer.declared_frames]] |
| reject_sheet | validated | unsupported | source digest mismatch or missing required frame with classified reason [[document.adapters.layer.declared_frames]] |
| judge_human_only | imported | imported | blank, inferred or derived values are never stored as human judgments [[document.adapters.layer.no_inferred_judgment]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| corpus_preserved | unit | [[document.adapters.layer.total_accounting]] | `six_accepted_sheets_203_regions()` | `all 203 regions retain sheet attribution, source page and original geometry provenance` |
| id_collision | unit | [[document.adapters.layer.sheet_scoped_ids]] | `same_local_id_two_sheets()` | `IDs remain distinct across sheets` |
| typed_refusal | unit | [[document.adapters.layer.declared_frames]] | `mismatched_digest_and_invalid_box_fixtures()` | `typed refusal/unresolved with input region reference; no geometry guessed` |
| sheets_unchanged | unit | [[document.adapters.layer.source_immutable]] | `frozen_sheet_bytes()` | `sha256(sheets_before) == sha256(sheets_after)` |
| no_machine_humanization | unit | [[document.adapters.layer.no_inferred_judgment]] | `blank_and_inferred_type_rows()` | `no independent human judgment created` |
| browser_execution_required | unit | [[document.adapters.layer.real_browser_gate]] | `journey_acceptance_without_browser_runtime()` | `acceptance fails when browser runtime unavailable; modeled interaction alone insufficient` |
