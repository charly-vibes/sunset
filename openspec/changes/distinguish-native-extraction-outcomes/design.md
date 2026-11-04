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

## Measured baseline (from sunset-9lp — placeholder until filled)

| Fixture | Status today | Coverage distinctions visible |
|---|---|---|
| (pending corpus re-run) | | |

## Risks

- Recorded-run fixtures embedding `partial` in expected JSON need updating in
  the same change to keep `just spec-check` green.
- Downstream scripts keying on exit 2 keep working; scripts keying on the
  literal status `partial` break — the migration note in tasks.md covers
  them.
