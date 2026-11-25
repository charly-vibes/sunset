# Purpose: RED-first tests for bounded deterministic responses
#   (add-agent-tool-surface task 3.5): declared size bounds, cursors that
#   encode scope + offset + run digest, and refusal of stale-run cursors.
# Responsibilities: Exercise sunset.tool_surface pagination and cursor
#   validation; cursors must be byte-deterministic for identical inputs.
"""Size bounds, deterministic cursors, stale-digest refusal (task 3.5)."""
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tool_surface_fixtures as fx

from sunset.tool_surface import MAX_PAGE_WORDS, ToolSurface


def opened(tmp_path):
    ws = tmp_path / "ws"
    run = fx.plain_run(tmp_path)
    surface = ToolSurface(ws)
    assert surface.open(run=str(run))["status"] == "ok"
    return surface


def page_scope(surface, page_index):
    return next(r["id"] for r in surface.descriptor["regions"]
                if r["kind"] == "page"
                and re.fullmatch(rf"page:{page_index}", r["anchor"]["locator_path"]))


def decode_cursor(cursor):
    return json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))


# -- pagination and bounds ---------------------------------------------------------

def test_words_paginates_with_cursor_until_exhausted(tmp_path):
    surface = opened(tmp_path)
    p2 = page_scope(surface, 2)
    seen = []
    env = surface.words(scope=p2, page_size=5)
    while True:
        assert env["status"] == "ok", env
        seen.extend(env["data"]["text"]["items"])
        cursor = env.get("cursor")
        if cursor is None:
            break
        env = surface.words(scope=p2, cursor=cursor)
    assert len(seen) == 12  # every word returned exactly once
    assert len({i["region_id"] for i in seen}) == 12


def test_cursor_is_deterministic_for_identical_calls(tmp_path):
    surface = opened(tmp_path)
    p2 = page_scope(surface, 2)
    a = surface.words(scope=p2, page_size=5)
    b = surface.words(scope=p2, page_size=5)
    assert a["cursor"] == b["cursor"]
    decoded = decode_cursor(a["cursor"])
    assert decoded["tool"] == "words"
    assert decoded["scope"] == p2
    assert decoded["offset"] == 5
    assert decoded["run"] == surface.run_digest


def test_page_size_bounds_are_enforced(tmp_path):
    surface = opened(tmp_path)
    p2 = page_scope(surface, 2)
    for bad in (0, -1, MAX_PAGE_WORDS + 1, 10 ** 6):
        env = surface.words(scope=p2, page_size=bad)
        assert env["status"] == "refused", bad
        assert env["reason"] == "bounds.exceeded", (bad, env)
    ok = surface.words(scope=p2, page_size=MAX_PAGE_WORDS)
    assert ok["status"] == "ok"


# -- cursor validation ---------------------------------------------------------------

def test_malformed_and_mismatched_cursors_are_refused(tmp_path):
    surface = opened(tmp_path)
    p2 = page_scope(surface, 2)
    cursor = surface.words(scope=p2, page_size=5)["cursor"]

    def encoded(payload):
        return base64.urlsafe_b64encode(
            json.dumps(payload).encode()).decode("ascii")

    other_page = page_scope(surface, 1)
    bads = [
        "not-a-cursor",
        encoded({"v": 1, "tool": "words", "scope": other_page,
                 "offset": 5, "run": surface.run_digest}),  # scope mismatch
        encoded({"v": 1, "tool": "crop", "scope": p2,
                 "offset": 5, "run": surface.run_digest}),  # tool mismatch
        encoded({"v": 1, "tool": "words", "scope": p2,
                 "offset": -1, "run": surface.run_digest}),  # bad offset
        encoded({"v": 2, "tool": "words", "scope": p2,
                 "offset": 5, "run": surface.run_digest}),  # bad version
    ]
    for bad in bads:
        env = surface.words(scope=p2, cursor=bad)
        assert env["status"] == "refused", bad
        assert env["reason"] == "cursor.invalid", (bad, env)


def test_cursor_from_another_run_digest_is_refused_as_stale(tmp_path):
    surface = opened(tmp_path)
    p2 = page_scope(surface, 2)
    original_digest = surface.run_digest
    cursor = surface.words(scope=p2, page_size=5)["cursor"]
    other_run = fx.build_run(tmp_path, "plain-other",
                             ["SOMETHING ELSE ENTIRELY"])
    env = surface.open(run=str(other_run))  # rebinds the session
    assert env["status"] == "ok"
    assert env["data"]["run_digest"] != original_digest
    stale = surface.words(scope=p2, cursor=cursor)
    assert stale["status"] == "refused"
    assert stale["reason"] == "cursor.stale"


def test_cursor_survives_session_reopen_on_the_same_run(tmp_path):
    ws = tmp_path / "ws"
    run = fx.plain_run(tmp_path)
    first = ToolSurface(ws)
    first.open(run=str(run))
    p2 = page_scope(first, 2)
    cursor = first.words(scope=p2, page_size=5)["cursor"]
    second = ToolSurface(ws)
    second.open(run=str(run))
    env = second.words(scope=p2, cursor=cursor, page_size=5)
    assert env["status"] == "ok"  # deterministic digest: not stale
    assert len(env["data"]["text"]["items"]) == 5


# -- render bounds -------------------------------------------------------------------

def test_crop_refuses_renders_beyond_the_pixel_budget(tmp_path):
    surface = opened(tmp_path)
    page = page_scope(surface, 1)
    env = surface.crop(anchor=page, dpi=2400)  # 400x200pt -> 13333x6667 px
    assert env["status"] == "refused"
    assert env["reason"] == "bounds.exceeded"
