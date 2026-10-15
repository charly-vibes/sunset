# Your first descriptor

This tutorial takes you from zero to a **validated DSC 0.3 descriptor** — a
file you create yourself and check with the reference validator that ships in
this repository. For what DSC is and why it looks this way, read
[What is DSC and why](what-is-dsc.md) first; this page only tells you what to
do.

## Prerequisites

- Python 3 (any recent version).
- A clone of this repository (sunset).

That is all. The `dsc03` package is standard-library-only — nothing to
install, no virtualenv needed. Run every command from the repository root.

## Step 1: Read the reference fixture

Open [`tests/tracer/fixture_minimal.json`](../../tests/tracer/fixture_minimal.json)
— the smallest descriptor the repository's own tests accept. Skim it against
this map of its top-level arrays (names are exact; the spec uses them and so
should you):

- `version`, `id`, `source` — the descriptor is `0.3`; it carries an `id`;
  and `source` names the observed document by `format`, `sha256` digest, and
  `locator`.
- `views` — named structural interpretations of the document, each with a
  `kind` (`physical`, `logical`, or `carrier`) and a `root` region. A physical
  view and a logical view of the same document coexist here; neither wins.
- `regions` — nodes inside one `view_id` each (a page, a paragraph, an
  article), tied together by `relations`.
- `contents` — the extracted observations themselves (`kind`, `value`), such
  as a run of text.
- `relations` — typed edges between regions and contents: `contains`
  (region→region), `has-content` (region→content), `realizes` (a physical
  region realizes a logical one), `precedes`, `derived-from`.
- `annotations` — claims about a target (`term`, `value`) with an explicit
  `origin` and `status`; here one is `asserted_without_evidence`, which is a
  legal, honest status.
- `evidence` — pointers tying claims back to `content_ids` and `selector_ids`
  in the source, so a reviewer can replay the observation.
- `selectors` — typed addresses into the source (`kind`, `locator`), each
  bound to an explicitly declared profile rather than assumed defaults.
- `interpretations` — named hypotheses such as a `reading-order`, kept
  separate instead of silently picking a winner.
- `coverage` — what the extractor did and did not handle (empty here).
- `profiles` — local declarations of the rules under which selectors and
  geometry are read, pinned by `version` and `sha256`.
- `vocabularies` — namespaces used by annotation terms.

Do not memorize this. Validate one, and the shape will stick.

## Step 2: Create your own descriptor

Create a file named `my-descriptor.json` in the repository root with exactly
this content (it describes a one-page document with one line of text, seen
through a physical and a logical view — same shape as the fixture, fewer
parts):

```json dsc-tutorial-descriptor
{
  "version": "0.3",
  "id": "my-first-descriptor",
  "source": {
    "format": "application/pdf",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "locator": "hello.pdf"
  },
  "views": [
    { "id": "v-phys", "kind": "physical", "root": "r-page" },
    { "id": "v-log", "kind": "logical", "root": "r-para" }
  ],
  "regions": [
    { "id": "r-page", "view_id": "v-phys", "kind": "page" },
    { "id": "r-line", "view_id": "v-phys", "kind": "line" },
    { "id": "r-para", "view_id": "v-log", "kind": "paragraph" }
  ],
  "contents": [
    { "id": "c-hello", "kind": "text", "value": "Hello, DSC" }
  ],
  "relations": [
    { "id": "rel-c", "kind": "contains", "from": "r-page", "to": "r-line" },
    { "id": "rel-hc", "kind": "has-content", "from": "r-line", "to": "c-hello" },
    { "id": "rel-rz", "kind": "realizes", "from": "r-line", "to": "r-para" },
    { "id": "rel-hc2", "kind": "has-content", "from": "r-para", "to": "c-hello" }
  ],
  "annotations": [],
  "evidence": [
    {
      "id": "e-hello",
      "origin": "source",
      "source_ref": "urn:example:hello:p1",
      "content_ids": ["c-hello"],
      "selector_ids": ["s-hello"]
    }
  ],
  "selectors": [
    {
      "id": "s-hello",
      "kind": "text-range",
      "profile_id": "p-text",
      "source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "target": "c-hello",
      "locator": "[0,5)"
    }
  ],
  "interpretations": [],
  "coverage": [],
  "profiles": [
    {
      "id": "p-text",
      "kind": "selector",
      "uri": "profiles/text-range.json",
      "version": "1",
      "sha256": "1c42da3a3e18fcf1222dc67aa6389e6cce2fe04681bb13f8d97059edd3a1813c"
    }
  ],
  "vocabularies": []
}
```

The mental model in one breath: **views** partition the document into
**regions**, regions carry **contents**, `relations` say how they fit
together, and **evidence** plus a **selector** say where every claim came
from in the source bytes. (The `sha256` values here are the well-known digest
of the empty string — a placeholder for the digest of your real document.)

## Step 3: Validate it

```console
$ python3 -m dsc03.validator my-descriptor.json
{"reasons": [], "status": "valid"}
```

Empty `reasons` means valid; the same thing from Python is
`validator.validate(validator.load("my-descriptor.json")) == []`. Every
failure is a typed reason code in that list — never a guess.

### Break it on purpose, then fix it

Delete the last character of `source.sha256` (making it 63 hex digits) and
validate again:

```console
$ python3 -m dsc03.validator my-descriptor.json
{"reasons": ["invalid_digest"], "status": "invalid"}
```

The validator does not just reject the file — it names the violation. Put the
character back and you are valid again. Malformed JSON is typed too:
`validator.run` reports a `parse_error:...` reason instead of raising at you.

## Where next

- [Adapting real carriers](integrate.md) — turn real PDF/EPUB
  extractions into descriptors like this one.
- [Reference](reference.md) (in progress) — index of specs, machinery, and
  gates.
- The normative source of truth lives in
  [the deployed capability specs](../../openspec/specs/).
