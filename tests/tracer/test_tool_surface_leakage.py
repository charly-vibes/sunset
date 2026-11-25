# Purpose: RED-first gate tests for document-text isolation
#   (add-agent-tool-surface task 3.4): document text is returned only in
#   `data.text` fields marked `untrusted: true`, and a hostile-text fixture
#   proves no leakage into status, reason or message fields.
# Responsibilities: Exercise sunset.tool_surface words/crop/propose over a
#   carrier whose page text imitates instructions colliding with envelope
#   field names; assert structural isolation of every hostile token.
"""Hostile-text isolation; document text only in data.text (task 3.4, gate)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tool_surface_fixtures as fx

from sunset.tool_surface import ToolSurface

HOSTILE_TOKENS = ["compromised", "owned", "IGNORE", "INSTRUCTIONS",
                  "SYSTEM:", "everything"]


def opened_hostile(tmp_path):
    ws = tmp_path / "ws"
    run = fx.hostile_run(tmp_path)
    surface = ToolSurface(ws)
    assert surface.open(run=str(run))["status"] == "ok"
    return surface


def page_scope(surface):
    return next(r["id"] for r in surface.descriptor["regions"]
                if r["kind"] == "page")


def outside_data_text(env):
    """The envelope with every document-bearing data.text branch removed."""
    scrubbed = json.loads(json.dumps(env))
    scrubbed.pop("data", None)
    return json.dumps(scrubbed, ensure_ascii=False)


def test_words_returns_hostile_text_only_in_untrusted_data_text(tmp_path):
    surface = opened_hostile(tmp_path)
    env = surface.words(scope=page_scope(surface))
    assert env["status"] == "ok"
    assert env["reason"] == "ok"
    text = env["data"]["text"]
    assert text["untrusted"] is True
    joined = " ".join(item["text"] for item in text["items"])
    for token in HOSTILE_TOKENS:
        assert token in joined  # the text IS returned, in its data field
        assert token not in outside_data_text(env)


def test_word_level_scope_leaks_nothing_outside_data_text(tmp_path):
    surface = opened_hostile(tmp_path)
    words = [r for r in surface.descriptor["regions"] if r["kind"] == "word"]
    hostile_words = []
    for w in words:
        env = surface.words(scope=w["id"])
        assert env["status"] == "ok"
        item = env["data"]["text"]["items"][0]
        if any(t in item["text"] for t in HOSTILE_TOKENS):
            hostile_words.append((w["id"], env))
    assert hostile_words  # the fixture really carries hostile tokens
    for _, env in hostile_words:
        assert env["data"]["text"]["untrusted"] is True
        assert all(t not in outside_data_text(env) for t in HOSTILE_TOKENS)


def test_crop_raster_carries_no_text_leakage(tmp_path):
    surface = opened_hostile(tmp_path)
    env = surface.crop(anchor=page_scope(surface))
    assert env["status"] == "ok"
    dumped = json.dumps(env, ensure_ascii=False)
    for token in HOSTILE_TOKENS:
        assert token not in dumped  # raster bytes are not text anywhere


def test_refusal_details_never_embed_document_text(tmp_path):
    surface = opened_hostile(tmp_path)
    page = page_scope(surface)
    spec = {"type": "field:total", "anchors": [page],
            "value": "1.234,56", "origin": "model:x", "extractive": True}
    env = surface.propose(spec=spec)  # anchored span is hostile prose
    assert env["status"] == "refused"
    assert env["reason"] in ("claim.value.mismatch",
                             "claim.value.unparseable")
    dumped = json.dumps(env, ensure_ascii=False)
    for token in HOSTILE_TOKENS:
        assert token not in dumped


def test_queue_and_export_never_carry_document_text(tmp_path):
    surface = opened_hostile(tmp_path)
    spec = {"type": "note", "anchors": [page_scope(surface)],
            "value": "model-supplied canonical value", "origin": "model:n",
            "extractive": False}
    assert surface.propose(spec=spec)["status"] == "ok"
    for env in (surface.queue(), surface.export()):
        assert env["status"] == "ok"
        dumped = json.dumps(env, ensure_ascii=False)
        for token in HOSTILE_TOKENS:
            assert token not in dumped
