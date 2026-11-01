> *I scanned the menu options*
> *I did not have a choice*
> *I'd like to teach the world to sing*
> *But I do not have a voice*
>
> — A Sunset, PULP

# sunset

[![tracked with wai](https://img.shields.io/badge/tracked%20with-wai-blue)](https://github.com/charly-vibes/wai)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> **Why:** turn PDFs into searchable text with verifiable source references,
> so extracted information can be checked, corrected and reused.
> **Status:** experimental. Native PDF extraction exists as a Python adapter;
> the one-command native workflow retains word locations and supports offline
> inspection and replay. OCR for scanned pages remains separate work.

Sunset is developing a local document extraction tool backed by **DSC
(Document Structural Core)**, its format for retaining source locations,
producer identity, transformations, disagreements and omissions. This repository
contains the DSC specifications, Python adapters and validation machinery,
and an experimental recorded-input digitization command.

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
[native-PDF proposal](openspec/changes/add-native-pdf-extraction/proposal.md)
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

- [`openspec/specs/`](openspec/) → the seven deployed capabilities, including 0.3 requirements (validated by `dsc03/`)
- [`archived add-dsc-03`](openspec/changes/archive/2026-10-14-add-dsc-03/proposal.md) — the deployed DSC 0.3 change

The bundle's original `specs/` were converted into these and removed from the bundle — no duplicates.

The deployed 0.3 requirements supersede conflicting details in the preserved research
draft. [Review resolutions](openspec/changes/archive/2026-10-14-add-dsc-03/design.md) explain the
explicit profile bindings, exact Unicode text, scoped coverage and content
lineage. Capability requirements remain solely in OpenSpec.

## Current executable truth

```bash
python3 spec/document-model-specodelic-v3/validator.py test
# → PASS 11 descriptor fixtures (0.2 only — this is not PDF/EPUB extraction)
python3 -B -m pytest tests -q          # 0.3 machinery + substrate gates
just spec-check                        # all gates: openspec strict, spk lint,
                                       # full suite, frozen 0.2 validator
```

Do not invoke it on 0.3 descriptors and call them valid; it correctly rejects
the new version. See the bundle's [README](spec/document-model-specodelic-v3/README.md)
for the full read order and scope.

The frozen baseline has [known validation limitations](docs/src/baseline-limitations.md),
including an uncaught exception for an array-valued relation endpoint. Eleven
passing fixtures do not imply total malformed-input handling.

Run `just spec-check` for strict OpenSpec validation, isolated proposal
composition and frozen baseline fixtures. The composition check does not
validate 0.3 descriptors or execute its acceptance scenarios.

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

## License

Apache-2.0 — see [LICENSE](LICENSE).
