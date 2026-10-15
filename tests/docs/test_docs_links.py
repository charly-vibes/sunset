"""Acceptance check for sunset-msj.1: link integrity of the explanation page.

Every markdown link in docs/src/what-is-dsc.md must resolve to an existing
repo file. Fails (page missing) until the page is written — RED phase of the
brief's red/green sequence.
"""

from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE = REPO_ROOT / "docs" / "src" / "what-is-dsc.md"

# [text](target) — inline links only; skips images (![...]) via the (?<!) guard.
LINK_RE = re.compile(r"(?<!\!)\[[^\]]+\]\(([^)\s]+)\)")


def test_explanation_page_exists() -> None:
    assert PAGE.is_file(), f"missing explanation page: {PAGE}"


# Forward-path targets that do not exist yet by design (built in later
# tickets). The page must link them anyway, marked "(in progress)", so the
# forward path stays stable.
# sunset-msj.2 shipped the tutorial, so first-descriptor.md left this set and
# is now resolved as a real target by test_all_markdown_links_resolve.
# sunset-msj.4 shipped the reference index, so reference.md left this set too
# and is now resolved as a real target by test_all_markdown_links_resolve.
EXPECTED_IN_PROGRESS: set[str] = set()


def _link_targets(md_text: str) -> list[str]:
    return LINK_RE.findall(md_text)


def _file_part(target: str) -> str:
    """Drop any #fragment before resolving to a file on disk."""
    return target.split("#", 1)[0]


def test_in_progress_forward_links_are_marked() -> None:
    """Declared in-progress targets must be labelled '(in progress)' in prose."""
    text = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
    for target in EXPECTED_IN_PROGRESS:
        idx = text.find(f"]({target})")
        assert idx != -1, f"missing forward link to {target}"
        window = text[idx : idx + 120]
        assert "(in progress)" in window, (
            f"forward link to {target} must carry '(in progress)' wording"
        )


def test_all_markdown_links_resolve() -> None:
    assert PAGE.is_file(), "page missing; cannot check links"
    broken = []
    for raw in _link_targets(PAGE.read_text(encoding="utf-8")):
        if raw.startswith(("http://", "https://", "mailto:")):
            continue  # external links are out of scope for this check
        target = _file_part(raw)
        if not target:
            continue  # pure-fragment link within the page
        if target in EXPECTED_IN_PROGRESS:
            continue  # declared in-progress forward path (see above)
        resolved = (PAGE.parent / target).resolve()
        if not resolved.exists():
            broken.append(raw)
    assert not broken, f"broken relative link targets: {broken}"


LLMS_TXT = REPO_ROOT / "llms.txt"


def test_llms_txt_links_resolve() -> None:
    """Every relative markdown link in llms.txt resolves to a repo file.

    llms.txt sits at the repository root, so link targets are resolved
    against the repo root (not docs/src/). External http(s) links are
    skipped, as in the docs link checks above. Fails until llms.txt is
    written (sunset-msj.5 green phase).
    """
    assert LLMS_TXT.is_file(), f"missing llms.txt: {LLMS_TXT}"
    broken = []
    for raw in _link_targets(LLMS_TXT.read_text(encoding="utf-8")):
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        target = _file_part(raw)
        if not target:
            continue
        resolved = (REPO_ROOT / target).resolve()
        if not resolved.exists():
            broken.append(raw)
    assert not broken, f"broken relative link targets in llms.txt: {broken}"


@pytest.mark.parametrize(
    "target",
    ["first-descriptor.md", "reference.md"],
)
def test_forward_links_present(target: str) -> None:
    """The 'where next' path must point at the tutorial and reference pages."""
    assert PAGE.is_file(), "page missing; cannot check forward links"
    assert target in _link_targets(PAGE.read_text(encoding="utf-8")), (
        f"expected forward link to {target} in the explanation page"
    )
