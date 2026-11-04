# Distinguish native extraction outcomes

## Why

Every committed carrier PDF currently returns the same `partial` status with
exit 2 from the native route, because any image/vector page marks the run
`approximated`. A clean text page with a logo and a scanned page with no text
read are indistinguishable at the status and exit-code level; the real
distinctions live only in per-feature coverage rows. Scripts driving the
first-consumer workflow cannot tell "fine, plus a logo" from "nothing was
read", which undermines measured false-positive/negative accounting.

Provenance: converged finding of two independent reviews —
`claude~b1e3330e` sunset-actionables.md B1 and `chatgpt~6aea991d` capability
gaps S3 residual — grounded against HEAD `37bf0bb` on 2026-11-04.

## What Changes

- Native run outcomes become exactly one of `text-complete`, `text-with-gaps`,
  `no-text-read`, computed from per-page text retention rather than the
  presence of any approximated feature.
- Exit-code contract: 0 for `text-complete`; 2 for `text-with-gaps` and
  `no-text-read`; the outcome field, not the exit code, carries the
  distinction.
- `visual_completeness: not-established` stays an independent field and never
  drives exit codes.
- Run manifests declare an outcome vocabulary version; unsupported versions
  are reported explicitly (`unsupported-version`), never guessed from
  coverage rows.

## Impact

- Affected specs: `document-adapters` (adds outcome requirements alongside the
  pending `add-native-pdf-extraction` deltas, which must deploy first).
- Affected code: `digitization/native.py` (outcome computation),
  `digitization/__main__.py` (exit mapping), manifest writer/reader.
- Affected docs: `docs/src/digitization.org` "Exit codes and refusals".
- Sequencing: blocked by corpus verification (beads `sunset-9lp`) and by
  deployment of `add-native-pdf-extraction` (beads parent `sunset-3yv`).
