# For agents: integrating with DSC 0.3

This brief is written for coding agents implementing DSC and agents running
the conformance suite. It states the integration contract precisely: what
you feed the machinery, what API surface to call, what comes back, and what
you may claim afterwards. Every claim here was verified against `dsc03`
source and against a fresh clone of this repository.

**Version scope: applies to DSC 0.3 deployed specs, 2026-10-15.** The
frozen 0.2 executable (`spec/document-model-specodelic-v3/validator.py`)
is out of scope for integration — it must keep rejecting 0.3 descriptors
and is never an integration target. See [status.md](status.md).

## Input contract: the descriptor JSON shape

Your input is a **DSC 0.3 descriptor** — a JSON document with exact
top-level arrays: `version`, `id`, `source`, `views`, `regions`,
`contents`, `relations`, `annotations`, `evidence`, `selectors`,
`interpretations`, `coverage`, `profiles`, `vocabularies`. The normative
shape is the [document-core spec](../../openspec/specs/document-core/spec.md);
the smallest descriptor the repository's own tests accept is
[`tests/tracer/fixture_minimal.json`](../../tests/tracer/fixture_minimal.json).
Build your first one with the
[tutorial](first-descriptor.md) — it walks you through the fixture field by
field.

## Validation API surface

Call the `dsc03` package (standard-library-only) from the repository root.
The three entry points, names exact:

- `dsc03.validator.load(path)` — read and parse a descriptor from disk.
- `dsc03.validator.validate(d)` — validate a parsed descriptor; returns a
  sorted list of typed reason strings, empty for valid.
- `dsc03.validator.run(path)` — `load` + `validate` with parse failures
  folded into the result as `parse_error:<detail>` reasons.

The CLI form `python3 -m dsc03.validator <path>` prints
`{"reasons": [...], "status": "valid"|"invalid"}` and exits 1 on invalid.

## Output contract: typed outcome lists

Validation output is a **list of typed reason strings** — machine-comparable
codes such as `invalid_shape`, `invalid_digest`, `duplicate_id`,
`not_nfc`, `parse_error:...`. An empty list means valid. Never branch on
exception types; branch on the reason list. (Reason codes are the
[document-core Validation outcome states](../../openspec/specs/document-core/spec.md).)

## The four reports: `dsc03.report.assess`

For a full run assessment, call
`dsc03.report.assess(descriptor, resolved_profiles, registry, enumerator=None)`.
It returns a dict with four **independent** keys — none implies another:

- `"schema"` — `{"status": "valid"|"invalid", "reasons": [...]}` from the
  validator.
- `"profiles"` — `{"status": "resolved"|"unresolved_profiles",
  "unresolved": [...]}`; resolve via `dsc03.profiles.Registry(dir)` and
  `dsc03.profiles.resolve(decl, registry)`.
- `"coverage"` — scoped coverage verification, or
  `{"status": "skipped", "reasons": [...]}` when the schema is invalid or a
  needed profile did not resolve. **`"skipped"` is not a failure** — fix the
  named cause and re-run.
- `"interpretation"` — per-annotation outcomes
  (`by_annotation`, `counts`): `supported` stays supported, `disputed`
  stays disputed, `asserted_without_evidence` is reported externally as
  `unverifiable`. Schema validity never promotes a claim.

For the resolution plumbing (`Registry`, `resolve`, enumerators) and the
real-carrier adapter calls (`adapters.describe_pdf`,
`adapters.enumerate_scopes`), follow
[integrate.md](integrate.md) Recipe 3 exactly.

## Error conditions: typed outcomes, never exceptions

For malformed input the machinery reports typed reasons instead of raising:
`validator.run` catches duplicate JSON keys (`Duplicate`), non-finite or
invalid-Unicode JSON, JSON syntax errors, and Unicode errors, and returns
them as reasons (e.g. `parse_error:Expecting value: line 1 column 1`).
Verified from a fresh clone: an empty file yields
`run(path) == ["parse_error:Expecting value: line 1 column 1 (char 0)"]`.
Treat any *unexpected* exception (outside these classes) as a machinery
bug, not a validation outcome — and remember the
[frozen 0.2 validator](../../spec/document-model-specodelic-v3/validator.py)
is exempt: it can crash on malformed relation endpoints
([baseline-limitations.md](baseline-limitations.md)) and must not be
integrated against.

## Runnable example: canonical descriptor and verified transcript

The canonical example is the tutorial's tagged descriptor block
(` ```json dsc-tutorial-descriptor `) in
[first-descriptor.md](first-descriptor.md) — write it verbatim to
`my-descriptor.json` at the repository root; do not retype or paraphrase
it. Transcript, verified verbatim from a fresh clone of this repository
(the descriptor is written from the tagged block, then validated):

```console
$ python3 -m dsc03.validator my-descriptor.json
{"reasons": [], "status": "valid"}
```

Deliberately corrupt the source digest (truncate one hex character) and the
same command reports the typed violation:

```console
$ python3 -m dsc03.validator my-descriptor.json
{"reasons": ["invalid_digest"], "status": "invalid"}
```

## Conformance boundary: what you may and may never claim

`dsc03.conformance.classify(suite)` turns an honest description of your
test suite into labels (`status`, `claims`, `missing`,
`real_carrier_conformance`, `workflow_benefit`). Suite keys (all optional):
`v02_fixtures`, `v03_schema`, `v03_profiles`, `v03_coverage`, `migration`,
`adversarial_corpus`, `real_carriers`, `independent_readers` (int),
`extractor_comparison`, `anchor_mapping_reviewed`, `first_consumer_demo`,
`native_output_baseline`, `demo_result`. Full taxonomy in
[reference.md](reference.md); the honest-claim recipe is
[integrate.md](integrate.md) Recipe 4.

You **may claim**, when the keys support it: `0.2 fixture coverage`,
`0.3 contract validation` (schema + profiles + coverage), `0.2-to-0.3
migration`.

You **may never claim** `real-carrier conformance` unless your suite
includes real carrier fixtures, the adversarial corpus, two independent
readers, a declared extractor comparison, and a reviewed anchor mapping —
otherwise `classify` reports `incomplete` and names what is missing. Passing
`python3 -B -m pytest tests/tracer -q` establishes the 0.3 contract
machinery over committed fixtures only — nothing more.

**Scripted-machinery limit:** this repository's 0.3 machinery and reviews
were agent-executed — including reviewer personas, reader annotations, and
demo time measurements (see [status.md](status.md)). Those are machinery
exercises, not conformance evidence; every recorded deviation is superseded
by a human pass. When consuming this corpus, mirror that honesty: label
your own agent-executed runs as such and let
[classify](../../dsc03/conformance.py) speak.
