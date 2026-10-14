"""Acceptance check for sunset-msj.2: the tutorial's embedded descriptor is valid.

Single source of truth rule: `docs/src/first-descriptor.md` embeds the tutorial
descriptor as a fenced ```json block whose info string contains the tag
`dsc-tutorial-descriptor` (e.g. ```json dsc-tutorial-descriptor). Exactly one
such block must exist; this test parses it with the real dsc03 validator
(loads — which also rejects duplicate JSON keys — then validates) and asserts
the typed outcome is the empty reason list, i.e. valid.

Other fenced json blocks in the page (deliberate-failure demos) are ignored:
they are invalid on purpose and are not tagged.

RED phase of the brief's red/green sequence: fails (page missing) until the
tutorial is written.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import validator

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE = REPO_ROOT / "docs" / "src" / "first-descriptor.md"

TAG = "dsc-tutorial-descriptor"
# ```json dsc-tutorial-descriptor\n ... ``` — info string, then body.
FENCE_RE = re.compile(r"^```([^\n]*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def _json_blocks(md_text: str) -> list[tuple[str, str]]:
    """(info string, body) for every fenced block whose info starts with json."""
    out = []
    for info, body in FENCE_RE.findall(md_text):
        if info.strip().split(" ")[0] == "json":
            out.append((info.strip(), body))
    return out


def test_tutorial_page_exists() -> None:
    assert PAGE.is_file(), f"missing tutorial page: {PAGE}"


def test_exactly_one_tagged_descriptor_block() -> None:
    assert PAGE.is_file(), "page missing; cannot extract blocks"
    tagged = [(info, body) for info, body in _json_blocks(PAGE.read_text(encoding="utf-8")) if TAG in info]
    assert len(tagged) == 1, (
        f"expected exactly one ```json block tagged '{TAG}' in {PAGE}, found {len(tagged)}"
    )


def test_tutorial_descriptor_validates_empty_reasons() -> None:
    assert PAGE.is_file(), "page missing; cannot validate descriptor"
    tagged = [(info, body) for info, body in _json_blocks(PAGE.read_text(encoding="utf-8")) if TAG in info]
    assert len(tagged) == 1, "tagged descriptor block missing"
    d = validator.loads(tagged[0][1])
    assert validator.validate(d) == [], "embedded tutorial descriptor must validate clean"


def test_tutorial_links_back_to_explanation_page() -> None:
    assert PAGE.is_file(), "page missing; cannot check links"
    assert "what-is-dsc.md" in PAGE.read_text(encoding="utf-8"), (
        "tutorial must link back to what-is-dsc.md for orientation"
    )
