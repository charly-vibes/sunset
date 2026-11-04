# Tasks: distinguish-native-extraction-outcomes

## 1. Prerequisites

- [ ] 1.1 Deploy pending `add-native-pdf-extraction` deltas (archive that
      change) so this change's base requirements exist in
      `openspec/specs/document-adapters/spec.md`
- [x] 1.2 Land beads `sunset-9lp` corpus verification; paste the measured
      fixture → outcome table into design.md

## 2. Outcome computation

- [ ] 2.1 Add outcome classifier in `digitization/native.py`: pure function
      over per-page retention results returning `text-complete`,
      `text-with-gaps`, or `no-text-read`; approximated features never
      downgrade, unexamined/failed regions do
- [ ] 2.2 Unit tests: logo-only page stays `text-complete`; one textless page
      among text pages yields `text-with-gaps`; all-textless selection yields
      `no-text-read` (red → green per beads TDD policy)

## 3. Manifest and CLI contract

- [ ] 3.1 Write outcome vocabulary version into native run manifests
- [ ] 3.2 Map exit codes in `digitization/__main__.py`: 0 for
      `text-complete`, 2 for `text-with-gaps` and `no-text-read`;
      `visual_completeness` never drives exit codes
- [ ] 3.3 `inspect`/`replay` report `unsupported-version` for manifests
      carrying only the legacy `partial` status (exit 4), never guessing
      semantics from coverage rows
- [ ] 3.4 Update recorded-run fixtures and expected JSON that embed
      `partial` so `just spec-check` stays green

## 4. Docs and migration

- [ ] 4.1 Update `docs/src/digitization.org` "Exit codes and refusals": new
      outcomes, unchanged coarse exit codes, legacy-manifest behavior
- [ ] 4.2 Migration note for scripts keying on the literal status `partial`
      (parse `status` field, not exit code)
- [ ] 4.3 Document the `--pages` convention (native: optional, defaults to
      all pages; recorded run: required) in the "Exit codes and refusals"
      section, closing the decision deferred from the CLI-defect ticket
