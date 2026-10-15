> *I scanned the menu options*
> *I did not have a choice*
> *I'd like to teach the world to sing*
> *But I do not have a voice*
>
> — A Sunset, PULP

# sunset

[![tracked with wai](https://img.shields.io/badge/tracked%20with-wai-blue)](https://github.com/charly-vibes/wai)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> **Why:** exchange document observations without losing where they came from,
> how they changed, where interpretations disagree, or what extraction omitted.
> sunset hosts the **DSC (Document Structural Core)** specification corpus:
> a deterministic, carrier-independent **document-structure interchange
> substrate** with explicit evidence, scoped loss and honest partiality —
> native PDF, EPUB, scanned PDF and structured carriers are first-class;
> extraction reconciliation (historical periodicals) is the **first
> consumer**, not the definition.
> **Status:** [experimental](docs/src/status.md) · 0.3 machinery implemented, substrate gates in progress · [Conformance matrix](docs/src/conformance-matrix.md) · [Bundle](spec/document-model-specodelic-v3/README.md)

`sunset` is the home of the **DSC specification corpus** in the
[charly-vibes](https://github.com/charly-vibes) tool fleet: an executable
**0.2 baseline** plus the **0.3 design proposal**. The research bundle landed
here from the specodelic v3 pass (`document-model-specodelic-v3`) and is
preserved as received under [`spec/`](spec/document-model-specodelic-v3/) —
except its `specs/`, which were converted to the OpenSpec tree and removed
from the bundle (see below).

## Who it is for

The initial consumer is a reviewer reconciling extraction of historical
periodicals: locating disputed text on a page, retaining competing reading
orders, and finding unexamined material. The proposed benefit is preserving
these distinctions across tools; improved OCR accuracy or reduced review time
has not been demonstrated.

The [first-consumer acceptance gate](openspec/changes/add-dsc-03/specs/document-conformance/spec.md#requirement-first-consumer-demonstration)
requires one real issue, two extractors and a reviewing consumer, with source
traceability, disagreement/loss retention, review effort and representation
overhead measured against native extractor outputs. Passing that narrow demo
does **not** establish full 0.3 or substrate conformance.

## Purpose, consumers, non-goals

**Normative purpose.** DSC is a deterministic, extensible
structural-description substrate: source observation, logical structure and
semantic interpretation stay separately addressable; evidence and loss are
always scoped; domain extensions never redefine core meaning.

**Consumers.** Extraction-review workflows are one consumer. Others the
substrate must serve equally: any tool that needs deterministic,
carrier-independent document structure with provenance (indexers, comparators,
debuggers, archival pipelines).

**Current capabilities (honest).** The deployed 0.3 machinery validates
0.3 descriptors, resolves pinned profiles, replays evidence transforms,
verifies scoped coverage, and adapts real PDF/EPUB carriers
([conformance matrix](docs/src/conformance-matrix.md)). The substrate gates
(restoring-document-substrate) run deterministic per-carrier oracles and
categorical law checks over committed screened fixtures — machinery-level
evidence only. **Real-carrier conformance and cross-tool interchange
conformance are NOT claimed.**

**Non-goals.** No universal ontology; no lossless conversion promise; no OCR
engine, PDF/EPUB parser product, CLI, or categorical runtime; PDF and EPUB
representations are not assumed isomorphic; evidence never implies truth.

## What's in the bundle

- [`CONTRACT.md`](spec/document-model-specodelic-v3/CONTRACT.md) — preserved earlier 0.3 wire proposal (**design, not implemented**)
- [`CONTRACT-0.2.md`](spec/document-model-specodelic-v3/CONTRACT-0.2.md) — executable 0.2 predecessor contract
- [`ACCEPTANCE.md`](spec/document-model-specodelic-v3/ACCEPTANCE.md) — original acceptance cases, supplemented by active OpenSpec deltas
- [`ONTOLOGY-BOUNDARIES.md`](spec/document-model-specodelic-v3/ONTOLOGY-BOUNDARIES.md) — guaranteed expressivity, gap registry, extension rules
- `fixtures/` — 0.2 descriptor fixtures (valid + invalid)
- [`validator.py`](spec/document-model-specodelic-v3/validator.py) — reference validator, **deliberately frozen at 0.2**

## Capability specs (OpenSpec)

The bundle's capability specs live **once**, in OpenSpec standard form:

- [`openspec/specs/`](openspec/) → the six 0.2-baseline capability specs (deployed truth, validated by `validator.py`)
- [`openspec/changes/add-dsc-03/`](openspec/changes/add-dsc-03/proposal.md) — the DSC 0.3 design proposal as spec deltas (design-only)

The bundle's original `specs/` were converted into these and removed from the bundle — no duplicates.

The active 0.3 deltas supersede conflicting details in the preserved research
draft. [Review resolutions](openspec/changes/add-dsc-03/design.md) explain the
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
