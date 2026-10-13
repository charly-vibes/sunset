> *Nothing gold can stay*
> — Robert Frost

# sunset

[![tracked with wai](https://img.shields.io/badge/tracked%20with-wai-blue)](https://github.com/charly-vibes/wai)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> **Why:** document extractors claim structural completeness they cannot
> prove — merged reading orders, silently dropped layout, unattributed text
> transformations. sunset hosts the **DSC 0.3 (Document Structural Core)**
> specification proposal, which keeps multiple structural views,
> source-addressable selectors, explicit interpretation provenance, and honest
> extraction coverage — uncertainty preserved, never merged away.
> **Status:** [experimental](docs/src/status.md) · spec proposal, no implementation yet · [Bundle](spec/document-model-specodelic-v3/README.md)

`sunset` is the home of the **DSC 0.3 specification proposal** in the
[charly-vibes](https://github.com/charly-vibes) tool fleet. The bundle landed
here from the specodelic v3 research pass (`document-model-specodelic-v3`)
and is preserved verbatim under [`spec/`](spec/document-model-specodelic-v3/).

## What's in the bundle

- [`CONTRACT.md`](spec/document-model-specodelic-v3/CONTRACT.md) — proposed 0.3 normative wire contract (**design, not implemented**)
- [`CONTRACT-0.2.md`](spec/document-model-specodelic-v3/CONTRACT-0.2.md) — executable 0.2 predecessor contract
- [`ACCEPTANCE.md`](spec/document-model-specodelic-v3/ACCEPTANCE.md) — falsifiable requirements and release gates
- [`ONTOLOGY-BOUNDARIES.md`](spec/document-model-specodelic-v3/ONTOLOGY-BOUNDARIES.md) — guaranteed expressivity, gap registry, extension rules
- `fixtures/` — 0.2 descriptor fixtures (valid + invalid)
- [`validator.py`](spec/document-model-specodelic-v3/validator.py) — reference validator, **deliberately frozen at 0.2**

## Capability specs (OpenSpec)

The bundle's capability specs live **once**, in OpenSpec standard form:

- [`openspec/specs/`](openspec/) — six 0.2-baseline capability specs (deployed truth, validated by `validator.py`)
- [`openspec/changes/add-dsc-03/`](openspec/changes/add-dsc-03/proposal.md) — the DSC 0.3 design proposal as spec deltas (design-only)

The bundle's original `specs/` were converted into these and removed from the bundle — no duplicates.

## Current executable truth

```bash
python3 spec/document-model-specodelic-v3/validator.py test
# → PASS 11 descriptor fixtures (0.2 only — this is not PDF/EPUB extraction)
```

Do not invoke it on 0.3 descriptors and call them valid; it correctly rejects
the new version. See the bundle's [README](spec/document-model-specodelic-v3/README.md)
for the full read order and scope.

## Roadmap

The 0.3 validator, selector profiles, manifest grammar, migrated fixtures,
PDF/EPUB adapters, and cross-reader benchmark are all unimplemented. If
sunset grows an implementation, it follows the
[dulce-de-leche onboarding checklist](https://github.com/charly-vibes/dulce-de-leche/blob/main/docs/standardization.md):
three CI workflow files, `book.toml` + theme, five book pages, `llms.txt`,
`versions.ddl.toml`, a ddl registry row, and a dogfood-matrix entry.

## Fleet

Every repo in the fleet carries the `charly-vibes` + `dulce-de-leche` GitHub
topics — browse the whole set at
[topic:charly-vibes topic:dulce-de-leche](https://github.com/search?q=topic%3Acharly-vibes+topic%3Adulce-de-leche&type=repositories).
One command installs and updates every tool: [dulce-de-leche (ddl)](https://github.com/charly-vibes/dulce-de-leche).

## License

Apache-2.0 — see [LICENSE](LICENSE).
