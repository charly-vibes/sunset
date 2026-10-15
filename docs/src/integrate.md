# Integrate an implementation with DSC

You have a document-extraction implementation and have already built and
validated a descriptor by hand ([your first descriptor](first-descriptor.md)).
This page gives you the four recipes for the next steps: turn real extractions
into descriptors, run the conformance suite against yourself, read the outcome
reports, and claim only what you can honestly claim. For what DSC is and why,
read [what-is-dsc.md](what-is-dsc.md); for the full machinery index, see
[reference.md](reference.md).

Run every command and script from the repository root of a fresh clone.

## Recipe 1: Adapt a real carrier into a 0.3 descriptor

The `dsc03.adapters` module turns the committed real carriers under
`fixtures/carriers/` into complete 0.3 descriptors. It only ever reads real
carrier bytes — synthetic, hand-built descriptors do not count here.

First install its one dependency (the rest of `dsc03` is standard-library
only, but the adapters read PDF bytes through pymupdf):

```console
$ python3 -m pip install pymupdf
```

Then run this script (save it as `adapt_pdf.py` or paste it into a REPL):

```python
from pathlib import Path

from dsc03 import adapters

CARRIER = Path("fixtures/carriers/agentic-patterns-excerpt.pdf")
OUT = Path("adapted")  # adapter artifacts land here

desc = adapters.describe_pdf(CARRIER, OUT)

print(desc["version"], desc["source"]["format"], desc["source"]["sha256"][:16])
print(sorted(p.name for p in OUT.iterdir()))
for decl in desc["profiles"]:
    print(decl["id"], decl["kind"], "v" + decl["version"], decl["sha256"][:16])
print(sorted({entry["feature"] for entry in desc["coverage"]}))
print(len(desc["annotations"]), "annotations preserved from the source")
```

Expected output (hash prefixes may differ only if the fixture ever changes —
they should not):

```console
$ python3 adapt_pdf.py
0.3 application/pdf 3b2425e5faeb373b
['inventory.json', 'manifest.json']
p-inv carrier-inventory v1 334cb4581cbefe61
p-man adapter-manifest v1 88b829b3443275b3
['pdf:annotations', 'pdf:attachments', 'pdf:glyphs', 'pdf:images', 'pdf:vectors']
2 annotations preserved from the source
```

What happened, and what to demand of your own adapter:

- **Inputs.** `describe_pdf(source_path, out_dir, page_texts=None,
  desc_suffix="")` requires real carrier bytes at `source_path`. Pointing it
  at anything you have not screened for personal data is your responsibility —
  see the PII note below.
- **Artifacts.** It writes `inventory.json` (the complete feature inventory
  for the source format) and `manifest.json` (the features this adapter run
  supports) under `out_dir`, and pins both in the descriptor's `profiles`
  declarations with `kind`, `version`, and `sha256`. Nothing is asserted about
  bytes the artifacts were not pinned to.
- **`page_texts`.** An optional `{page_number: text}` override for the
  per-page text contents — one snapshot per pinned extractor, the
  first-consumer-demo pattern. Coverage, inventory, annotations, and evidence
  still come from the real carrier bytes; only the text-observation provenance
  changes to your named extractor. Leave it out and pymupdf's own extraction
  is recorded.
- **`desc_suffix`.** Disambiguates the descriptor `id` when you adapt the
  same carrier more than once (one run per extractor, for example).
- **Preserving source observations.** Your descriptor must keep what the
  carrier actually contains: per-page regions plus text evidence, source
  annotations bound to evidence, and scoped coverage over the full independent
  inventory — glyphs/images/vectors/annotations/attachments for PDF,
  manifest/spine/navigation/resources for EPUB — with every scope enumerated
  from the actual bytes (page counts from the PDF structure, archive members
  from the ZIP central directory). Where the adapter observes but cannot
  extract (image pixels, vector geometry), the coverage disposition says
  `approximated` with a reason, never `preserved`.

For EPUB carriers the same shape applies with
`describe_epub(source_path, out_dir)`:

```python
from pathlib import Path

from dsc03 import adapters

desc = adapters.describe_epub(
    Path("fixtures/carriers/sunset-carrier-sample.epub"), Path("adapted-epub")
)
print(sorted({entry["feature"] for entry in desc["coverage"]}))
# ['epub:manifest', 'epub:navigation', 'epub:resources', 'epub:spine']
print(len(desc["coverage"]))
# 11 — every non-directory ZIP member is enumerated and covered individually
```

**PII screening note.** The carriers in `fixtures/carriers/` were screened and
redacted (see
[`fixtures/carriers/MANIFEST.org`](../../fixtures/carriers/MANIFEST.org)).
Run the adapters on committed fixtures freely; before pointing them at any
other file, run the same screening step over full text, metadata, annotation
contents, and embedded files.

## Recipe 2: Run the conformance suite against your implementation

To check your implementation (or this repository's) against the 0.3 contract,
run the tracer test suite:

```console
$ python3 -B -m pytest tests/tracer -q
...................................................................... [100%]
143 passed
```

Which test file covers which capability area:

| Test file | Capability area |
|---|---|
| `test_tracer_validate.py`, `test_negative_core.py` | document-core schema validation (typed reasons, negative fixtures) |
| `test_profile_resolution.py`, `test_profile_grammar.py` | profile artifacts (pinning, resolution, selector/geometry grammar) |
| `test_evidence_replay.py`, `test_evidence_lineage.py` | evidence links and transform chains |
| `test_coverage.py` | carrier-inventory/adapter-manifest grammar, scoped coverage dispositions |
| `test_reports.py` | the four outcome reports |
| `test_migrate.py` | 0.2-to-0.3 migration |
| `test_frozen_02_regression.py` | the frozen 0.2 validator rejects 0.3 |
| `test_e2e_walk.py` | end-to-end tracer path over one descriptor |
| `test_adapters.py` | real-carrier adapters (`dsc03.adapters`) |
| `test_conformance_corpus.py` | adversarial corpus, independent readers |
| `test_first_consumer_demo.py` | first-consumer demonstration workflow |
| `test_conformance_labels.py` | honest label classification (`dsc03.conformance`) |
| `test_ontology_boundaries.py` | ontology boundary projection evaluator |

What a passing run does **not** entitle you to claim: it validates the 0.3
contract machinery and the adapters over the committed fixtures — nothing
more. It is not real-carrier conformance, not reader independence, and not a
workflow-benefit demonstration. Recipe 4 tells you how to label that honestly.

## Recipe 3: Read the four reports

To evaluate one descriptor run, use `dsc03.report.assess(descriptor,
resolved_profiles, registry, enumerator=None)`. It produces four **separate**
reports; none of them implies the others:

1. **schema** (`validator_reasons` under the hood) — does the descriptor
   satisfy the 0.3 document-core schema?
2. **profiles** — did every declared profile resolve against your local
   registry, by pinned `(kind, version, sha256)` identity?
3. **coverage** — does the scoped coverage hold against the inventory and the
   actual source enumeration? (Skipped — not failed — when the schema is
   invalid or a needed profile did not resolve.)
4. **interpretation** (`interpret` under the hood) — per-annotation outcomes:
   `supported` stays supported, `disputed` stays disputed, and
   `asserted_without_evidence` is reported as `unverifiable` externally.
   Schema validity never promotes a claim.

Resolve profiles through a registry rooted where the adapter wrote its
artifacts, and pass an enumerator that reads the carrier's real bytes:

```python
from pathlib import Path

from dsc03 import adapters, profiles, report

CARRIER = Path("fixtures/carriers/bank-statement-ca-excerpt.pdf")
OUT = Path("adapted")

desc = adapters.describe_pdf(CARRIER, OUT, desc_suffix="-run1")

registry = profiles.Registry(OUT)  # artifacts were written under OUT
resolved = {p["id"]: profiles.resolve(p, registry) for p in desc["profiles"]}

data = CARRIER.read_bytes()
enumerated = lambda fmt, kind: adapters.enumerate_scopes(fmt, data, kind)

reports = report.assess(desc, resolved, registry, enumerated)

print(reports["schema"]["status"])            # valid
print(reports["profiles"]["status"])          # resolved
print(reports["coverage"]["summaries"])       # one least-preserving summary per feature
print(reports["coverage"]["source_coverage"]) # overall disposition
print(reports["interpretation"]["counts"])    # supported / disputed / unverifiable
```

To read a failure, look at the named report only. A one-character digest
corruption shows exactly how the reports separate:

```python
broken = dict(desc)
source = dict(broken["source"])
source["sha256"] = source["sha256"][:-1]  # 63 hex digits: invalid
broken["source"] = source

reports = report.assess(broken, resolved, registry, enumerated)
print(reports["schema"]["status"])    # invalid — reasons: ['invalid_digest']
print(reports["coverage"])            # skipped, reason schema_invalid, unexamined
print(reports["interpretation"]["counts"])  # unchanged: interpretation is independent
```

The same reading rule applies throughout: `coverage.status == "skipped"` is
not a coverage failure — fix the schema or the unresolved profile named in the
`profiles` report, then re-run.

## Recipe 4: Classify honestly

To state what your test suite actually established, describe it as a suite
dictionary and let `dsc03.conformance.classify(suite)` produce the labels.
Suite keys (all optional): `v02_fixtures`, `v03_schema`, `v03_profiles`,
`v03_coverage`, `migration`, `adversarial_corpus`, `real_carriers`,
`independent_readers` (int), `extractor_comparison`,
`anchor_mapping_reviewed`, `first_consumer_demo`, `native_output_baseline`,
and `demo_result` (`{functional_gates_passed, review_time_delta}`).

The repository's own tracer suite, classified honestly, is *incomplete*:

```python
from dsc03 import conformance

suite = {
    "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
    "v03_coverage": True, "migration": True,
}
print(conformance.classify(suite))
# {'status': 'incomplete',
#  'claims': ['0.2 fixture coverage', '0.3 contract validation',
#             '0.2-to-0.3 migration'],
#  'missing': ['real PDF/EPUB carrier fixtures'],
#  'real_carrier_conformance': False,
#  'workflow_benefit': 'unproven'}
```

A suite that closes every gap earns the complete label — and you can see how
narrowly scoped even that label is:

```python
from dsc03 import conformance

full = {
    "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
    "v03_coverage": True, "migration": True, "real_carriers": True,
    "adversarial_corpus": True, "independent_readers": 2,
    "extractor_comparison": True, "anchor_mapping_reviewed": True,
}
print(conformance.classify(full)["claims"])
# ['0.2 fixture coverage', '0.3 contract validation', '0.2-to-0.3 migration',
#  'real-carrier conformance']
```

Honest-claiming rules, encoded in the labels:

- **Labels are scoped.** `real-carrier conformance` appears only when real
  carriers, an adversarial corpus, at least two independent readers, a
  declared extractor comparison, and a reviewed anchor mapping are all
  present. Nothing else — not the tracer suite, not a validated descriptor,
  not a passing schema run — supports that claim.
- **Workflow benefit stays `unproven`** without the first-consumer
  demonstration plus a native-output baseline. Even then, traceability is
  only *demonstrated* (never proven), and speed is claimed only if review
  time did not increase.
- **Scripted machinery alone never claims real-carrier conformance.** This
  repository's own machinery was agent-executed; the recorded deviations are
  listed in [status.md](status.md) — a human pass supersedes them.

## Background

For the history behind this machinery — how the tracer bullet reached the
first-consumer demonstration — see
[tracer-bullet.org](tracer-bullet.org) and
[first-consumer-demo.org](first-consumer-demo.org). They are background, not
required reading for any recipe above.
