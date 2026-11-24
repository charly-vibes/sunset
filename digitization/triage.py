"""Lane 2 triage: qwen3.8-flash pre-screens digitization runs so the human
review walk can be prioritized (owner-approved 2026-11-11).

Engineering-only by construction: the output is a walk-order suggestion
with per-region agree/differ flags and unknown = regions the checker
could not judge. It carries NO quality conclusions and never produces
reviewed references. Model output outside the typed vocabulary is
refused, never coerced. Raw model responses are kept for provenance.
"""

import argparse
import base64
import json
import pathlib
import subprocess
import tempfile

from dsc03.visual.review import build_descriptor_review_bundle

PROVIDER = "qwen-token-plan-individual"
MODEL = "qwen3.8-flash"
VOCAB = ("agree", "differ")
DIFFICULTY = ("easy", "moderate", "hard")
DIGEST_MAX_CHARS = 2400

_PROMPT = """You audit OCR-based structure extraction on a scanned newspaper page.
The attached image is the pinned page render. Below are claimed regions (id + pixel rect).
For EACH region judge: "agree" = the rect covers a coherent real ink/visual block; \
"differ" = the rect misses, misplaces or over-covers ink, or is not a real block.
If you cannot judge a region, OMIT it — never guess.
Reply with ONLY minified JSON, no markdown fences:
{{"regions": {{"<id>": {{"verdict": "agree|differ", "note": "max 12 words"}}}}, \
"page_difficulty": "easy|moderate|hard", "difficulty_reason": "max 15 words"}}
Claims: {claims}"""


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def claims_digest(page, max_chars=DIGEST_MAX_CHARS):
    claims = [
        {"id": r["id"], "rect": r["rect_px"]}
        for r in (page.get("regions") or [])
        if r.get("rect_px")
    ]
    return json.dumps(claims, separators=(",", ":"))[:max_chars]


def parse_triage(raw):
    _require(raw.lstrip().startswith("{"), "checker returned non-JSON output")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"checker returned invalid JSON: {e}") from e
    for verdict in (e.get("verdict") for e in (data.get("regions") or {}).values()):
        _require(verdict in VOCAB, f"checker verdict {verdict!r} outside the {VOCAB} vocabulary")
    _require(data.get("page_difficulty") in DIFFICULTY,
             "checker page_difficulty outside the easy/moderate/hard vocabulary")
    return data


def score_page(parsed, region_ids):
    regions = parsed.get("regions") or {}
    counts = {"agree": 0, "differ": 0, "unknown": 0}
    for rid in region_ids:
        entry = regions.get(rid)
        counts[entry["verdict"] if entry else "unknown"] += 1
    return counts


def rank_pages(summaries):
    return sorted(summaries, key=lambda s: (-s["score"]["differ"],
                                            -s["score"]["unknown"], s["page"]))


def _run_pi(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=600)


def call_model(image_path, prompt):
    argv = ["pi", "--no-session", "--no-tools",
            "--provider", PROVIDER, "--model", MODEL,
            "-p", prompt, f"@{image_path}"]
    done = _run_pi(argv)
    _require(done.returncode == 0, f"pi call failed: {done.stderr[-400:]}")
    return done.stdout


def _decode_image(page, workdir):
    uri = page.get("image") or ""
    _require(uri.startswith("data:image/"), f"page {page.get('page')} has no pinned render")
    payload = base64.b64decode(uri.split(",", 1)[1])
    path = pathlib.Path(workdir) / f"page-{page['page']}.png"
    path.write_bytes(payload)
    return path


def triage_page(page, workdir):
    raw = call_model(_decode_image(page, workdir),
                     _PROMPT.format(claims=claims_digest(page)))
    return raw, parse_triage(raw)


def _summary_line(s):
    sc = s["score"]
    return (f"| {s['page']} | {sc['agree']} | {sc['differ']} | {sc['unknown']} "
            f"| {s['parsed']['page_difficulty']} | {s['parsed'].get('difficulty_reason', '')} |")


def _write_report(out_dir, summaries, ranked):
    lines = ["* qwen3.8-flash triage — ENGINEERING-ONLY, agent-executed",
             "Walk-order suggestion only. NO quality conclusions; unknown = unjudged.",
             f"| page | agree | differ | unknown | difficulty | reason |",
             "|-+-+-+-+-+|"]
    lines += [_summary_line(s) for s in sorted(summaries, key=lambda s: s["page"])]
    lines.append("\nRanked walk order: " +
                 ", ".join(f"page {s['page']}" for s in ranked))
    (out_dir / "triage.org").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="digitization run output dir")
    parser.add_argument("--out", required=True, help="report output dir")
    args = parser.parse_args(argv)
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    descriptor = pathlib.Path(args.run) / "descriptor.json"
    with tempfile.TemporaryDirectory() as tmp:
        record = build_descriptor_review_bundle(descriptor, pathlib.Path(tmp) / "bundle.html")
        pages = record["carriers"][0]["pages"]
        summaries = []
        for page in pages:
            if page["unavailable"]:
                print(f"page {page['page']}: unavailable ({page['unavailable']}) — skipped")
                continue
            raw, parsed = triage_page(page, tmp)
            (out_dir / f"raw-page-{page['page']}.txt").write_text(raw, encoding="utf-8")
            ids = [r["id"] for r in page["regions"] if r.get("rect_px")]
            summaries.append({"page": page["page"], "parsed": parsed,
                              "score": score_page(parsed, ids)})
            sc = summaries[-1]["score"]
            print(f"page {page['page']}: {sc} ({parsed['page_difficulty']})")
    ranked = rank_pages(summaries)
    _write_report(out_dir, summaries, ranked)
    print("walk order: " + ", ".join(str(s["page"]) for s in ranked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
