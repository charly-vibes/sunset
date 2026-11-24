> *I scanned the menu options*
> *I did not have a choice*
> *I'd like to teach the world to sing*
> *But I do not have a voice*
>
> — A Sunset, PULP

# sunset

[![tracked with wai](https://img.shields.io/badge/tracked%20with-wai-blue)](https://github.com/charly-vibes/wai)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> A local document extraction tool: PDFs → searchable text with verifiable
> source references — for people building searchable archives or extracting
> information from documents who must check every result against its page.
>
> **Why:** turn PDFs into searchable text with verifiable source references,
> so extracted information can be checked, corrected and reused.
> **Status:** [experimental](docs/src/status.md) · native PDF extraction exists as a
> Python adapter; the one-command native workflow retains word locations and
> supports offline inspection and replay; OCR for scanned pages remains separate
> work · [Motivation & design](docs/src/what-is-dsc.md)

Sunset is developing a local document extraction tool backed by **DSC
(Document Structural Core)**, its format for retaining source locations,
producer identity, transformations, disagreements and omissions. This repository
contains the DSC specifications, Python adapters and validation machinery,
and an experimental recorded-input digitization command.

## When to use

Use sunset when:

- You need PDF text you can **verify against the page** — every word and line
  keeps its source location, and a finished run can be inspected or replayed
  offline against retained artifacts.
- You need extraction honesty: each run reports exactly one outcome
  (`text-complete` / `text-with-gaps` / `no-text-read`), so gaps are explicit
  rather than silently dropped.
- You are building DSC-based consumers (indexers, comparators, archival
  pipelines) that keep source observations, structure and interpretation
  separately addressable.

Use something else instead:

- You just need plain text out of a PDF and do not need source locations,
  integrity inspection or replay — use [`pdftotext`
  (poppler)](https://poppler.freedesktop.org/) or
  [PyMuPDF](https://pymupdf.readthedocs.io/) directly.
- You want a knowledge graph over your documents — use
  [bajan](https://github.com/charly-vibes/bajan) instead; sunset stores
  extraction evidence, not a graph.

**Assumption sunset makes:** the PDF carries an embedded text layer. The native
route reads embedded text only — no OCR, no model, no network service — and
makes no claim about scanned pages, lossless conversion, or that retained
evidence establishes truth.

## Install

No published package exists today — no wheel or sdist, no prebuilt release
binaries. **Without a source checkout you cannot install sunset yet**; this is
the recorded [distribution deviation](docs/src/status.md#deviations-from-the-fleet-standardization-checklist).
The supported install is from source:

```sh
git clone https://github.com/charly-vibes/sunset && cd sunset
uv sync
```

`uv sync` populates `.venv` from `uv.lock` (Python ≥ 3.11, PyMuPDF 1.28.2,
mirrored in [requirements-native.txt](requirements-native.txt)). Without uv,
any Python 3 with `pytest` and `PyMuPDF==1.28.2` works
(`python3 -m pip install -r requirements-native.txt`); run commands from the
repository root.

## Quick start

Extract a PDF's embedded text with source mappings (from the repository root;
the output directory must not already exist):

```sh
uv run python -m digitization native --source input.pdf --output native-run
# → {"manifest": ".../native-run/manifest.json", "provider_calls": 0,
#    "reason": "native-extraction-text-complete", "status": "text-complete"}
# → exit 0
```

`native-run/` holds the retained run: `manifest.json`, `descriptor.json`,
`raw.txt`, `search.txt`, `word-map.json`, `line-map.json`, `page-map.json`.
Exit `2` (`text-with-gaps` or `no-text-read`) means some or all selected pages
contributed no text — inspect the report; exit `3` refuses invalid input, `4`
an unsupported manifest version, `5` an integrity failure.

Check the run without re-extracting:

```sh
uv run python -m digitization inspect --run native-run --json
# → {"mode": "native", "status": "text-complete", "extractor": {"id": "pymupdf", ...}}
# → exit 0
```

## Common workflows

1. **Extract a text PDF with word/line source mappings** —
   `uv run python -m digitization native --source in.pdf --output run-1` →
   outcome JSON plus the retained artifacts above; exit 0, or 2 when gaps or
   textless pages are reported.
2. **Verify a retained run against its artifacts** —
   `uv run python -m digitization inspect --run run-1` → human report; exit 0
   for intact runs, including gap-bearing runs. No re-extraction.
3. **Copy a run offline with verification** —
   `uv run python -m digitization replay --run run-1 --output replayed-run` →
   verified copy including `replay-report.json`; exit 0. No re-extraction.

## Commands

| Command | What it does | When |
|---|---|---|
| `native --source S --output O [--pages 1,2]` | Native extraction of embedded text with word/line maps | First run over a text PDF |
| `inspect --run R [--json]` | Verifies retained artifacts and reports status, source, text, selectors, usage | After any run, before trusting it |
| `resume --run R` | Verifies and reports retained native status without mutation or extraction | Re-entering a native run |
| `replay --run R --output O` | Verifies and copies a run offline (adds `replay-report.json`) | Archiving or moving a run |
| `run --source S --pages P --config C --output O` | Recorded-input digitization of supplied observations | Review loops with derived configs (`--cache`, `--fresh`, `--select` available) |
| `evaluate --baseline B --candidate C --reference R --policy P --output O` | Measured comparison of two runs against a reference | Comparing an extraction candidate |

`--pages` takes comma-separated one-based PDF indices; `native` defaults to all
pages. Full flags, exit codes and refusals:
[digitization reference](docs/src/digitization.org).

## FAQ

### Which DSC versions are implemented?
DSC 0.3 is the deployed capability set: the `dsc03/` machinery, requirements in
[`openspec/specs/`](openspec/), exercised by `tests/tracer/` and the
[conformance matrix](docs/src/conformance-matrix.md). The reference validator
`spec/document-model-specodelic-v3/validator.py` is deliberately frozen at DSC
0.2.

### Why does the frozen 0.2 validator reject my 0.3 descriptor?
By design. It is frozen at 0.2 and correctly rejects 0.3 descriptors rather
than mis-validating them — do not invoke it on 0.3 descriptors or call the
result valid. 0.3 validation lives in the `dsc03` machinery and its tests. The
validator's `PASS 11 descriptor fixtures` covers 0.2 descriptors only — it is
not PDF/EPUB extraction — and the frozen baseline has
[known validation limitations](docs/src/baseline-limitations.md), including an
uncaught exception for an array-valued relation endpoint.

### Does it OCR scanned pages?
No. The native route reads embedded text only; an image-only PDF reports
`no-text-read`. OCR for scanned pages is separate, unshipped work. Recorded OCR
configs over rasterized pages and the `just ocr-review` loop exist for review;
they measure discrepancies and do not establish transcription accuracy or
visual completeness.

### Does it use the network or send my documents anywhere?
No. Native extraction, inspection, resume and replay are local and offline:
they invoke no OCR engine, model or network service and report
`provider_calls: 0`.

### Is there a pip package or prebuilt binary?
Not today. Sunset ships as Python source in this repository; a user without a
source checkout cannot install it. This is the recorded
[distribution deviation](docs/src/status.md#deviations-from-the-fleet-standardization-checklist),
and install-from-source above is the only supported install path.

### What does it write or modify?
Only the `--output` run directory you name, which must not already exist; a
nonempty output directory is never overwritten. Nothing else on disk is
touched, and nothing leaves the machine.

## Development

Repository development happens from a source checkout:

```sh
uv sync            # interpreter + pinned runtime (.venv); override with SUNSET_PYTHON=...
just spec-check    # all gates: openspec strict, spk lint, tracer suite,
                   # frozen 0.2 validator, pinned openspec 1.x strict
```

- `uv run python -B -m pytest tests -q` — 0.3 machinery + substrate gates
  (the tracer suite; not real-carrier conformance).
- `python3 spec/document-model-specodelic-v3/validator.py test` — the frozen
  0.2 reference validator → `PASS 11 descriptor fixtures (0.2 only — this is
  not PDF/EPUB extraction)`.
- `just visual-review [port]` — human visual-review SPA over recorded
  calibration examples (side-by-side + overlay of claimed regions against
  pinned renders; output is gitignored).
- `just digitization-review <source> <output> [port] [pages]` — recorded
  digitization of a native-text PDF plus its review bundle →
  `<output>/review.html`.
- `just ocr-review <source> <output> [port] [pages] [dpi]` — OCR ground-truth
  loop: rasterize, OCR the raster with pinned tesseract, measure IoU + text
  similarity against native truth; eval exit 2 = measured discrepancies
  (expected — that is the finding).

Do not invoke the frozen validator on 0.3 descriptors and call them valid; it
correctly rejects the new version. See the bundle's
[README](spec/document-model-specodelic-v3/README.md) for the full read order
and scope. Run `just spec-check` for strict OpenSpec validation, isolated
proposal composition and frozen baseline fixtures; the composition check does
not validate 0.3 descriptors or execute its acceptance scenarios.

## Who it is for

People building searchable archives or extracting information from documents
need to verify results against the original pages. The first practical baseline
is a PDF with embedded text: extract it locally, retain page and word locations,
and inspect any passage against its source. Scanned historical periodicals are
a more demanding consumer, extending that baseline with OCR and structural review.

The intended journey is **PDF → searchable text with source mappings → inspection**.
Later interpretations, such as court or case-number fields, can cite supporting
passages without replacing the original text. Domain-field extraction is outside
the initial native-text workflow.

## Purpose, consumers, non-goals

DSC keeps source observations, logical structure and semantic interpretation
separately addressable. It supports the extraction tool and other consumers
such as indexers, comparators and archival pipelines. Existing deployed
requirements remain authoritative; the
[native-PDF change record](openspec/changes/archive/2026-11-04-add-native-pdf-extraction/proposal.md)
records the design source for the implemented local workflow.

| Available now | Planned baseline |
|---|---|
| Python PDF/EPUB adapters; local native PDF extraction with word/line mappings, integrity inspection and offline replay | OCR for scanned pages and visual completeness |
| DSC 0.3 validation, selectors, evidence transforms and coverage checks | General cross-tool conformance and installable packaging |
| Recorded-input digitization, inspection, caching and offline replay | OCR and visual completeness for scanned pages |

See the [digitization reference](docs/src/digitization.org) for current commands
and [status](docs/src/status.md) for limitations. The native route requires Python
3 and PyMuPDF 1.28.2 (see [requirements-native.txt](requirements-native.txt));
it does not invoke OCR or network services. Improved OCR accuracy, reduced human review
time and general cross-tool interchange conformance have not been demonstrated.
Conformance labels remain scoped by `dsc03/conformance.py`.

Sunset reuses extraction engines. It does not promise lossless conversion,
a universal ontology, or that evidence establishes truth. Native PDF extraction
does not require OCR; scanned pages need a separate recognition route. EPUB
support remains part of DSC and the adapter machinery.

## What's in the bundle

- [`CONTRACT.md`](spec/document-model-specodelic-v3/CONTRACT.md) — preserved earlier 0.3 wire proposal (**design, not implemented**)
- [`CONTRACT-0.2.md`](spec/document-model-specodelic-v3/CONTRACT-0.2.md) — executable 0.2 predecessor contract
- [`ACCEPTANCE.md`](spec/document-model-specodelic-v3/ACCEPTANCE.md) — original acceptance cases, supplemented by active OpenSpec deltas
- [`ONTOLOGY-BOUNDARIES.md`](spec/document-model-specodelic-v3/ONTOLOGY-BOUNDARIES.md) — guaranteed expressivity, gap registry, extension rules
- `fixtures/` — 0.2 descriptor fixtures (valid + invalid)
- [`validator.py`](spec/document-model-specodelic-v3/validator.py) — reference validator, **deliberately frozen at 0.2**

## Capability specs (OpenSpec)

The bundle's capability specs live **once**, in OpenSpec standard form:

- [`openspec/specs/`](openspec/) → the eight deployed capabilities, including 0.3 requirements (validated by `dsc03/`)
- [`archived add-dsc-03`](openspec/changes/archive/2026-10-14-add-dsc-03/proposal.md) — the deployed DSC 0.3 change

The bundle's original `specs/` were converted into these and removed from the bundle — no duplicates.

The deployed 0.3 requirements supersede conflicting details in the preserved research
draft. [Review resolutions](openspec/changes/archive/2026-10-14-add-dsc-03/design.md) explain the
explicit profile bindings, exact Unicode text, scoped coverage and content
lineage. Capability requirements remain solely in OpenSpec.

## Roadmap

The native-PDF baseline is implemented and tracked by `sunset-jbb`; it is independent of the scanned Diario OCR pilot and its approval gates. OCR and visual completeness remain future work.

Implemented: the 0.3 validator, selector profiles, manifest grammar, migrated
fixtures, PDF/EPUB adapters, cross-reader benchmark and conformance labels
(`dsc03/`), plus the substrate gate harness (`dsc03/substrate/`,
`tests/substrate/`). Open: deploying the three grounded changes
(substrate → composition semantics → Lens debugger); wiring the substrate
purpose/categorical-model deltas into the deployed specs once their gate
evidence is reviewed. Everything still follows the
[dulce-de-leche onboarding checklist](https://github.com/charly-vibes/dulce-de-leche/blob/main/docs/standardization.md)
for any shipped-tool step: three CI workflow files, `book.toml` + theme, five
book pages, `llms.txt`, `versions.ddl.toml`, a ddl registry row, and a
dogfood-matrix entry.

## Fleet

Every repo in the fleet carries the `charly-vibes` + `dulce-de-leche` GitHub
topics — browse the whole set at
[topic:charly-vibes topic:dulce-de-leche](https://github.com/search?q=topic%3Acharly-vibes+topic%3Adulce-de-leche&type=repositories).
One command installs and updates every tool: [dulce-de-leche (ddl)](https://github.com/charly-vibes/dulce-de-leche).

## Docs, status and license

- Documentation entry point: [What is DSC and why](docs/src/what-is-dsc.md)
- Command reference and exit codes: [digitization reference](docs/src/digitization.org)
- Limitations, deviations and maturity: [status](docs/src/status.md), including
  the [known frozen-baseline limitations](docs/src/baseline-limitations.md)
  and the fleet-standardization
  [deviation record](docs/src/status.md#deviations-from-the-fleet-standardization-checklist)

## License

Apache-2.0 — see [LICENSE](LICENSE).
