"""Lane 1 draft-assist: qwen3.8-flash pre-drafts review verdicts for a
digitization run; the human verifies each draft in the review SPA
(owner-approved 2026-11-11, amending re-entry condition (a): references
become "LLM-drafted, human-verified", with the human walk as the
measured verification cost).

Honesty boundaries:

- the checker may only draft agree/differ; every region it cannot judge
  is OMITTED (no draft, no silent resolution),
- output outside the typed vocabulary is refused, never coerced,
- the human verdict always wins: the SPA merge never overwrites a ruled
  region, and provenance lives in the note prefix,
- drafts confer NO reference status on their own.
"""

import argparse
import json
import pathlib
import tempfile

from dsc03.visual.review import build_descriptor_review_bundle

from digitization.triage import (
    PROVIDER,
    VOCAB,
    _decode_image,
    _require,
    _run_pi,
    claims_digest,
)

DRAFT_PREFIX = "[qwen3.8 draft] "

_PROMPT = """You pre-draft review verdicts for OCR structure claims on a scanned newspaper page render.
For each claimed region you are CONFIDENT about: "agree" = rect covers a coherent real ink/visual block; \
"differ" = rect misses, misplaces or over-covers ink.
OMIT every region you are not confident about — a human verifies each draft and must never be anchored on guesses.
Notes: max 12 words, what the human should double-check.
Reply with ONLY minified JSON, no markdown fences:
{{"drafts": {{"<id>": {{"verdict": "agree|differ", "note": "..."}}}}}}
Claims: {claims}"""


def parse_drafts(raw):
    _require(raw.lstrip().startswith("{"), "checker returned non-JSON output")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"checker returned invalid JSON: {e}") from e
    drafts = {}
    for rid, entry in (data.get("drafts") or {}).items():
        _require(entry.get("verdict") in VOCAB,
                 f"checker draft verdict {entry.get('verdict')!r} outside the {VOCAB} vocabulary")
        drafts[rid] = {"verdict": entry["verdict"], "note": entry.get("note", "")}
    return drafts


def _call_drafts(page, workdir):
    return _run_pi(["pi", "--no-session", "--no-tools",
                    "--provider", PROVIDER, "--model", "qwen3.8-flash",
                    "-p", _PROMPT.format(claims=claims_digest(page)),
                    f"@{_decode_image(page, workdir)}"])


def _parse_or_none(pnum, attempt, done):
    if done.returncode != 0:
        print(f"page {pnum}: pi call failed (attempt {attempt})")
        return None
    try:
        return parse_drafts(done.stdout)
    except ValueError as e:
        print(f"page {pnum}: attempt {attempt} refused — {e}")
        return None


def _draft_one(page, workdir, out_dir):
    # bounded retry: one refusal gets exactly one retry; every raw response
    # is kept on disk so a refusal is always inspectable, never silent
    for attempt in (1, 2):
        done = _call_drafts(page, workdir)
        suffix = ["", "-retry2"][attempt - 1]
        name = f"raw-drafts-page-{page['page']}{suffix}.txt"
        (pathlib.Path(out_dir) / name).write_text(done.stdout, encoding="utf-8")
        parsed = _parse_or_none(page["page"], attempt, done)
        if parsed is not None:
            return parsed, False
    return {}, True


def _existing(out, wanted):
    # incremental rerun: --pages N merges into an existing drafts.json
    if not (out.exists() and wanted):
        return {}
    try:
        return json.loads(out.read_text(encoding="utf-8")).get("pages", {})
    except (OSError, json.JSONDecodeError):
        return {}


def _skip(page, wanted):
    if page["unavailable"]:
        return "unavailable"
    if wanted and str(page["page"]) not in wanted:
        return "filtered"
    return ""


def _page_filter(args):
    if not args.pages:
        return None
    return set(args.pages.split(","))


def _write_payload(out, pages_out):
    payload = {"model": "qwen3.8-flash", "prefix": DRAFT_PREFIX, "pages": pages_out,
               "no_draft_pages": sorted(p for p, d in pages_out.items() if not d)}
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="digitization run output dir")
    parser.add_argument("--out", required=True, help="drafts.json output path")
    parser.add_argument("--pages", default="", help="comma list to redo; default all")
    args = parser.parse_args(argv)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wanted = _page_filter(args)
    pages_out = _existing(out, wanted)
    descriptor = pathlib.Path(args.run) / "descriptor.json"
    with tempfile.TemporaryDirectory() as tmp:
        record = build_descriptor_review_bundle(descriptor, pathlib.Path(tmp) / "bundle.html")
        for page in record["carriers"][0]["pages"]:
            reason = _skip(page, wanted)
            if reason:
                print(f"page {page['page']}: {reason} — no drafts")
                continue
            drafts, _refused = _draft_one(page, tmp, out.parent)
            pages_out[str(page["page"])] = drafts
            print(f"page {page['page']}: {len(drafts)} drafts")
    _write_payload(out, pages_out)
    print(f"wrote {out} ({sum(len(v) for v in pages_out.values())} drafts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
