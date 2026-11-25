# Purpose: RED-first tests for the six read tools (add-agent-tool-surface
#   task 3.1): open, words, crop, zoom_in, zoom_out, queue — every one a pure
#   read that never mutates the session claims or the run artifacts.
# Responsibilities: Exercise sunset.tool_surface against real synthetic
#   carriers; assert observed read outcomes and the non-mutation invariant.
"""Read tools on synthetic carriers; reads never mutate (task 3.1)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tool_surface_fixtures as fx

from sunset.tool_surface import ToolSurface


def opened(tmp_path):
    ws = tmp_path / "ws"
    run = fx.plain_run(tmp_path)
    surface = ToolSurface(ws)
    env = surface.open(run=str(run))
    assert env["status"] == "ok", env
    regions = surface.descriptor["regions"]
    pages = [r for r in regions if r["kind"] == "page"]
    words = [r for r in regions if r["kind"] == "word"]
    return surface, run, sorted(pages, key=lambda r: r["id"]), words


def page_scope(surface, page_index):
    """The descriptor page region id for the given 1-based carrier page."""
    for region in surface.descriptor["regions"]:
        if region["kind"] != "page":
            continue
        locator = region["anchor"]["locator_path"]
        if re.fullmatch(rf"page:{page_index}", locator):
            return region["id"]
    raise AssertionError("page region not found")


def session_bytes(surface):
    return surface.session_path.read_bytes()


# -- open -------------------------------------------------------------------------

def test_open_is_idempotent_on_the_same_run(tmp_path):
    surface, run, _, _ = opened(tmp_path)
    again = surface.open(run=str(run))
    assert again["status"] == "ok"
    assert again["data"]["run_digest"] == surface.run_digest


# -- words ------------------------------------------------------------------------

def test_words_returns_page_text_marked_untrusted(tmp_path):
    surface, _, pages, _ = opened(tmp_path)
    env = surface.words(scope=page_scope(surface, 1))
    assert env["status"] == "ok", env
    assert env["reason"] == "ok"
    text = env["data"]["text"]
    assert text["untrusted"] is True
    joined = " ".join(item["text"] for item in text["items"])
    assert "TOTAL" in joined and "1.234,56" in joined
    assert "FECHA" in joined  # both fixture lines live on page 1
    assert "WORD01" not in joined  # page-2 pagination text does not leak


def test_words_of_a_word_scope_returns_exactly_that_word(tmp_path):
    surface, _, _, words = opened(tmp_path)
    env = surface.words(scope=words[0]["id"])
    assert env["status"] == "ok", env
    items = env["data"]["text"]["items"]
    assert len(items) == 1
    assert items[0]["region_id"] == words[0]["id"]


def test_words_descends_into_child_scopes(tmp_path):
    surface, _, _, _ = opened(tmp_path)
    p1 = page_scope(surface, 1)
    env = surface.words(scope=p1)
    word_ids = {i["region_id"] for i in env["data"]["text"]["items"]}
    env_line = surface.words(scope=next(
        r["id"] for r in surface.descriptor["regions"]
        if r["kind"] == "line"
        and r["anchor"]["locator_path"].startswith("page:1/")))
    assert {i["region_id"] for i in env_line["data"]["text"]["items"]} <= word_ids


# -- crop -------------------------------------------------------------------------

def test_crop_returns_pinned_reference_and_render(tmp_path):
    surface, _, _, words = opened(tmp_path)
    env = surface.crop(anchor=words[0]["id"])
    assert env["status"] == "ok", env
    data = env["data"]
    assert data["crop_reference"]["digest"].startswith("crop:")
    assert data["render"]["png_base64"]
    assert data["render"]["meta"]["dpi"] == 72


def test_crop_of_page_scope_renders_whole_page(tmp_path):
    surface, _, _, _ = opened(tmp_path)
    env = surface.crop(anchor=page_scope(surface, 1))
    assert env["status"] == "ok", env
    assert env["data"]["render"]["png_base64"].startswith("iVBOR")


# -- zoom ladder ------------------------------------------------------------------

def test_zoom_in_restricts_and_zoom_out_climbs(tmp_path):
    surface, _, _, words = opened(tmp_path)
    word = words[0]["id"]
    down = surface.zoom_in(scope=word)
    assert down["status"] == "ok", down
    assert word in down["data"]["region_ids"]
    up = surface.zoom_out(scope=word)
    assert up["status"] == "ok", up
    parents = [p["id"] for p in up["data"]["parents"]]
    assert parents and word not in parents


def test_zoom_out_from_the_root_is_refused(tmp_path):
    surface, _, _, _ = opened(tmp_path)
    docs = [r["id"] for r in surface.descriptor["regions"]
            if r["kind"] == "document"]
    env = surface.zoom_out(scope=docs[0])
    assert env["status"] == "refused"
    assert env["reason"] == "scope.no-parent"


# -- queue ------------------------------------------------------------------------

def test_queue_is_empty_before_any_claim(tmp_path):
    surface, _, _, _ = opened(tmp_path)
    env = surface.queue()
    assert env["status"] == "ok", env
    assert env["data"]["items"] == []


def test_queue_lists_unverified_claims_after_propose(tmp_path):
    surface, _, pages, _ = opened(tmp_path)
    p3 = page_scope(surface, 3)
    spec = {"type": "field:total", "anchors": [p3], "value": "9.999,00",
            "origin": "model:g", "extractive": False}
    assert surface.propose(spec=spec)["status"] == "ok"
    env = surface.queue()
    assert env["status"] == "ok", env
    assert [i["claim_id"] for i in env["data"]["items"]] != []
    assert all(i["status"] in ("unverified", "conflicted")
               for i in env["data"]["items"])


# -- reads never mutate ------------------------------------------------------------

def test_read_tools_leave_session_and_run_untouched(tmp_path):
    surface, run, pages, words = opened(tmp_path)
    p3 = page_scope(surface, 3)
    spec = {"type": "field:total", "anchors": [p3], "value": "1.234,56",
            "origin": "model:t", "extractive": False}
    assert surface.propose(spec=spec)["status"] == "ok"
    claims_before = fx.canonical(surface.claims)
    before_session = session_bytes(surface)
    before_descriptor = (Path(run) / "descriptor.json").read_bytes()
    page1 = page_scope(surface, 1)
    reads = [
        surface.words(scope=page1),
        surface.words(scope=words[0]["id"]),
        surface.crop(anchor=words[0]["id"]),
        surface.zoom_in(scope=page1),
        surface.zoom_out(scope=page1),
        surface.queue(),
        surface.export(),
    ]
    assert all(env["status"] == "ok" for env in reads), reads
    assert session_bytes(surface) == before_session
    assert (Path(run) / "descriptor.json").read_bytes() == before_descriptor
    assert fx.canonical(surface.claims) == claims_before


# -- ro5u review round (2026-11-25): boundary hardening ---------------------------

def test_crop_of_a_lean_page_frame_is_a_typed_refusal(tmp_path):
    # EDGE-001: a geometry frame without cropbox/source_dimensions must yield
    # crop.geometry-missing, never internal.error (ro5u review 2026-11-25).
    surface, _, pages, _ = opened(tmp_path)
    page_id = page_scope(surface, 1)
    region = next(r for r in surface.descriptor["regions"] if r["id"] == page_id)
    region.pop("geometry", None)
    surface._frames = {"page-1-pt": {"name": "page-1-pt"}}
    env = surface.crop(anchor=page_id)
    assert env["status"] == "refused", env
    assert env["reason"] == "crop.geometry-missing", env


def test_open_source_reextracts_an_incomplete_run_dir(tmp_path, monkeypatch):
    # EDGE-002: a runs/<digest16> dir without manifest.json is an interrupted
    # extract; open(source=...) must rebuild it, not refuse permanently.
    import hashlib
    import digitization.native as native
    carrier = fx.make_text_carrier(tmp_path / "inc.pdf", ["REEXTRACT 1"])
    data = carrier.read_bytes()
    ws = tmp_path / "ws"
    target = ws / "runs" / hashlib.sha256(data).hexdigest()[:16]
    target.mkdir(parents=True)  # partial: no manifest
    real = native.extract
    calls = []

    def recording_extract(src, dst):
        calls.append(str(dst))
        return real(src, dst)

    monkeypatch.setattr(native, "extract", recording_extract)
    surface = ToolSurface(ws)
    env = surface.open(source=str(carrier))
    assert env["status"] == "ok", env
    assert calls, "incomplete run dir must be re-extracted"


def test_corrupt_claims_payload_resets_cleanly(tmp_path):
    # CORR-001: a session file with a non-list claims payload must reset the
    # session instead of leaking TypeErrors into later tool calls.
    surface, run, _, _ = opened(tmp_path)
    payload = {"version": 1, "run": str(run),
               "run_digest": surface.run_digest, "claims": "not-a-list"}
    surface.session_path.write_bytes(fx.canonical(payload).encode("utf-8"))
    fresh = ToolSurface(surface.workspace)  # _load_session restore path
    assert fresh.claims == []
    assert fresh.queue()["status"] == "ok"
    again = fresh.open(run=str(run))  # open() same-digest restore path
    assert again["status"] == "ok", again
    assert fresh.claims == []
