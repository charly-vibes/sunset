# Design: distinguish-native-extraction-outcomes

## Context

`digitization/__main__.py` maps a single `partial` status to exit 2
(`code = 2 if result['status'] == 'partial' else 0`). The discriminating
information already exists in coverage rows
(`unexamined` / `unsupported` / `approximated`) and
`visual_completeness: not-established` is hard-set for every run. The pending
`add-native-pdf-extraction` requirement "Native extraction partiality and
failures" requires textless pages to remain explicitly unresolved but does not
define a script-consumable outcome vocabulary.

## Goals

- Outcome classification is a pure function of per-page retention results —
  no new extraction behavior.
- Scripts get a three-way distinction without breaking the coarse exit-code
  contract that recorded-run tooling already relies on.

## Decisions

1. **Status names.** `text-complete` / `text-with-gaps` / `no-text-read`.
   Chosen over `complete-text`/`text-with-nontext-content`/`no-text-read`
   (review wording) for verb-last consistency with existing statuses
   (`measured`, `partial`, `stopped-with-unresolved-work`).
2. **Exit codes stay coarse.** Both gap-bearing outcomes map to exit 2; the
   JSON `status` field carries the distinction. Rationale: exit codes are
   consumed by shell scripts that today treat 2 as "inspect the report";
   introducing a third code would silently reclassify `no-text-read` for
   existing callers. Revisit only if telemetry shows conflation.
3. **Versioning.** Add the outcome value to the manifest's existing version
   guard rather than a new field name: manifests carrying only the legacy
   `partial` status keep replaying via the existing `unsupported-version`
   path (exit 4) already implemented for resume. New manifests are written
   with the new vocabulary; `inspect`/`replay` reject old ones explicitly
   instead of guessing semantics from coverage rows.
4. **Non-text content never downgrades.** Approximated images/vectors/
   annotations appear only in coverage rows; they cannot lower
   `text-complete` to a gap outcome. Unexamined or failed regions can.
5. **Interplay with `sunset-1uv`.** The aligner-failure fix (page-level
   unexamined scope) feeds `text-with-gaps`; both changes agree that
   tool-internal failures are never `invalid-input`.
6. **`--pages` convention.** Resolved here rather than left deferred from
   the CLI-defect ticket: `native` keeps optional `--pages` (default all
   pages), while recorded `run` keeps it required — a recorded run must
   prove which selection produced it; a fresh extraction has a natural
   whole-document default. Documented via tasks 4.3; no code change.
7. **Sequencing.** Deploy after `add-native-pdf-extraction` archives (its
   deltas are the base text this change extends) and after beads `sunset-9lp`
   supplies the measured per-fixture outcome table recorded below.

## Measured baseline (from sunset-9lp — filled 2026-11-05)

Measured over all 11 committed carriers (`fixtures/carriers/*.pdf`) with
`.venv/bin/python -B -m digitization native --source <pdf> --output <tmp>`,
base commit `37bf0bb` + proposal commit `bfc16ba`. Outcome column is the
proposed vocabulary applied mechanically (glyphs `approximated` never
downgrades; glyph rows `unexamined` do; empty contents ⇒ `no-text-read`).

| Fixture | Exit today | Status today | Glyph rows | Approximated non-text | Text contents | Proposed outcome |
|---|---|---|---|---|---|---|
| accounting-made-simple-excerpt | 2 | `partial` | 5×`preserved`, **1×`unexamined`** | 2 img, 6 vec | 10 entries | `text-with-gaps` |
| agentic-patterns-excerpt | 2 | `partial` | 6×`preserved` | 1 vec | 12 entries | `text-complete` |
| bank-statement-ca-excerpt | 2 | `partial` | 1×`preserved` | 1 vec | 2 entries | `text-complete` |
| bank-transfer-redacted | 2 | `partial` | 1×`preserved` | 1 img, 1 vec | 2 entries | `text-complete` |
| budgeting-basics-excerpt | 2 | `partial` | 3×`preserved` | 3 img, 3 vec | 6 entries | `text-complete` |
| cta-cte-propietario-redacted | 2 | `partial` | 2×`preserved` | 2 img, 2 vec | 4 entries | `text-complete` |
| diario-de-poesia-excerpt | 2 | `partial` | 6×`unexamined` | 6 img, 1 vec | **0** | `no-text-read` |
| estado-deuda-abl-redacted | 2 | `partial` | 1×`preserved` | 1 img, 1 vec | 2 entries | `text-complete` |
| invoice-arca-redacted | 2 | `partial` | 3×`preserved` | 3 img | 6 entries | `text-complete` |
| lab-result-redacted | 2 | `partial` | 6×`unexamined` | 6 img, 1 vec | **0** | `no-text-read` |
| resumen-periodical-excerpt | **3** | `invalid-input` | — (no manifest written) | — | — | outside vocabulary (`invalid-input`) |

Re-measured after sunset-1uv (2026-11-04, aligner failures become page-level
unexamined scopes): the resumen row now exits **2** with
`native-extraction-text-with-gaps` — page 1 glyph row `unexamined`
(`native word alignment failed; glyphs unexamined`), pages 2–6 `preserved`,
manifest written, inspect exit 0. The `invalid-input` row above is the
historical 9lp measurement at base `37bf0bb` and no longer reproduces.

Measured findings (denominators for the outcome split):

1. **Collapse confirmed**: 10/11 fixtures return byte-identical
   `status: partial` / `reason: native-extraction-partial` / exit 2. The
   review claim was accurate per-document, not just in aggregate.
2. **The three-way split exists today, only in coverage rows**: of the 10
   `partial`s, 7 are clean-text-plus-non-text (would be `text-complete`),
   1 has a glyph row `unexamined` despite text elsewhere (`text-with-gaps`),
   and 2 read zero text — scan and rasterized carriers whose glyph rows are
   all `unexamined` (`no-text-read`, 20% of the partial population). The
   `preserved` vs `unexamined` glyph row is the discriminator; no other
   signal distinguishes them.
3. **`visual_completeness` is uniformly `not-established`** across all 10
   manifests — consistent with it staying an independent field that never
   drives exit codes.
4. **Exit 3 (`invalid-input`) writes no manifest**: resumen-periodical fails
   pre-manifest ("native extractor word does not align with raw text on
   page 1"), emitting only an error JSON on stdout. Scripts therefore face
   three observable shapes today — manifest+exit 2, no-manifest+exit 3 — and
   the outcome field must exist only in the manifest shape. *(Superseded for
   resumen by sunset-1uv: aligner failures are page-level unexamined scopes
   inside a manifest-bearing partial run; see the re-measured row above.)*
5. **Contents are page-unanchored** (`id`/`kind`/`value` only): per-page text
   retention is NOT derivable from `contents`; it must come from glyph/coverage
   rows scoped per page. The classifier in task 2.1 must key on glyph-row
   scope, not on contents page anchors.

## Risks

- Recorded-run fixtures embedding `partial` in expected JSON need updating in
  the same change to keep `just spec-check` green.
- Downstream scripts keying on exit 2 keep working; scripts keying on the
  literal status `partial` break — the migration note in tasks.md covers
  them.
