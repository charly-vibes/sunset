"""Contract tests for the qwen-assisted review checker (owner-approved
2026-11-11 session: Lane 2 triage + Lane 1 draft-assist).

Hard honesty boundaries, derived from the recorded review contract:

- the checker is ENGINEERING-ONLY triage and DRAFT prefill; it never
  produces reviewed references and never resolves unknowns,
- off-vocabulary model output is refused, typed, never coerced,
- a region the checker cannot judge gets NO draft and counts as
  unknown in triage (no silent resolution),
- merging drafts into the SPA may only fill regions the human has NOT
  already ruled; a human verdict always wins.

The model call itself is a subprocess boundary; these tests cover the
pure parsing/merging/ranking logic only.
"""

import json

import pytest

from digitization.drafts import parse_drafts
from digitization.triage import (
    VOCAB,
    claims_digest,
    parse_triage,
    rank_pages,
    score_page,
)


def _page_record():
    return {
        "page": 1,
        "unavailable": None,
        "width": 820,
        "height": 1132,
        "regions": [
            {"id": "page-1-det-1", "rect_px": [10, 20, 300, 40], "expected": None},
            {"id": "page-1-det-2", "rect_px": [10, 80, 200, 30], "expected": None},
        ],
    }


# ---------------------------------------------------------------------------
# triage: claims digest
# ---------------------------------------------------------------------------


def test_claims_digest_is_compact_and_ids_stable():
    digest = claims_digest(_page_record())
    assert "page-1-det-1" in digest and "page-1-det-2" in digest
    assert "[10,20,300,40]" in digest
    assert len(digest) <= 2400, "digest must stay bounded for token cost"


def test_claims_digest_skips_unmapped_regions():
    page = _page_record()
    page["regions"][0]["rect_px"] = None  # unknown frame: no claim to check
    digest = claims_digest(page)
    assert "page-1-det-1" not in digest
    assert "page-1-det-2" in digest


# ---------------------------------------------------------------------------
# triage: typed parsing of model output
# ---------------------------------------------------------------------------


def test_parse_triage_accepts_vocabulary_and_counts():
    raw = json.dumps({
        "regions": {
            "page-1-det-1": {"verdict": "agree", "note": "box matches headline"},
            "page-1-det-2": {"verdict": "differ", "note": "rect off by a line"},
        },
        "page_difficulty": "moderate",
    })
    parsed = parse_triage(raw)
    assert parsed["regions"]["page-1-det-1"]["verdict"] == "agree"
    assert parsed["page_difficulty"] == "moderate"


def test_parse_triage_refuses_off_vocabulary_verdicts():
    raw = json.dumps({
        "regions": {"page-1-det-1": {"verdict": "winner", "note": ""}},
        "page_difficulty": "easy",
    })
    with pytest.raises(ValueError, match="vocabulary"):
        parse_triage(raw)


def test_parse_triage_refuses_bad_difficulty_and_json():
    bad_difficulty = json.dumps({"regions": {}, "page_difficulty": "trivial"})
    with pytest.raises(ValueError, match="difficulty"):
        parse_triage(bad_difficulty)
    with pytest.raises(ValueError, match="JSON"):
        parse_triage("not json at all")


def test_score_page_counts_omitted_regions_as_unknown():
    raw = json.dumps({
        "regions": {
            "page-1-det-1": {"verdict": "agree", "note": ""},
            # det-2 omitted: the checker could not judge it
        },
        "page_difficulty": "hard",
    })
    parsed = parse_triage(raw)
    scored = score_page(parsed, [r["id"] for r in _page_record()["regions"]])
    assert scored == {"agree": 1, "differ": 0, "unknown": 1}
    assert VOCAB == ("agree", "differ")  # checker never says unknown; absence is unknown


def test_rank_pages_orders_by_differ_then_unknown_then_page():
    summaries = [
        {"page": 3, "score": {"agree": 9, "differ": 0, "unknown": 0}},
        {"page": 1, "score": {"agree": 5, "differ": 4, "unknown": 1}},
        {"page": 2, "score": {"agree": 6, "differ": 4, "unknown": 3}},
    ]
    ranked = rank_pages(summaries)
    assert [s["page"] for s in ranked] == [2, 1, 3]


# ---------------------------------------------------------------------------
# drafts: typed parsing; omission is allowed, invention is not
# ---------------------------------------------------------------------------


def test_parse_drafts_keeps_confident_and_drops_missing():
    raw = json.dumps({
        "drafts": {
            "page-1-det-1": {"verdict": "agree", "note": "clean text block"},
            # det-2 omitted: no draft for what the checker cannot judge
        },
    })
    drafts = parse_drafts(raw)
    assert drafts["page-1-det-1"]["verdict"] == "agree"
    assert "page-1-det-2" not in drafts


def test_parse_drafts_refuses_unknown_and_off_vocabulary():
    raw = json.dumps({
        "drafts": {"page-1-det-1": {"verdict": "unknown", "note": ""}},
    })
    with pytest.raises(ValueError, match="vocabulary"):
        parse_drafts(raw)
    raw2 = json.dumps({
        "drafts": {"page-1-det-1": {"verdict": "roughly-agree", "note": ""}},
    })
    with pytest.raises(ValueError, match="vocabulary"):
        parse_drafts(raw2)


# ---------------------------------------------------------------------------
# (SPA-side mergeDrafts is node-tested in test_visual_review_spa.py —
#  the merge runs in the browser against SPA state, not in python.)
# ---------------------------------------------------------------------------
