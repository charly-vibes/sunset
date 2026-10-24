"""Contract tests for the sunset-905.3 reader observation SPA.

The SPA (hitl/sunset-905.3/templates/observations-spa.html) is the reader-
facing form that replaces hand-edited JSON observation sheets. It must:

- exist in both the repo templates/ and the bundle templates/ copies,
- be fully self-contained (works offline over file://),
- never phone home or reference external resources,
- emit the exact observations-template.json schema (same keys, same
  context kinds, same rotation/column vocabularies),
- record reader identity and elapsed time per carrier.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPO_SPA = REPO / "hitl" / "sunset-905.3" / "templates" / "observations-spa.html"
BUNDLE_SPA = REPO / "hitl" / "sunset-905.3" / "bundle" / "templates" / "observations-spa.html"

TEMPLATE = json.loads(
    (REPO / "hitl" / "sunset-905.3" / "templates" / "observations-template.json").read_text()
)

CONTEXT_KINDS = {
    "publication_date",
    "publisher_or_source",
    "author_or_attribution",
    "quoted_material",
}
ROTATIONS = {"0", "90", "180", "270", "unknown"}
COLUMN_VALUES = {"single", "two", "multi", "unknown"}
ANNOTATION_TYPES = {
    "Highlight",
    "Text",
    "StrikeOut",
    "FreeText",
    "Underline",
    "Square",
    "Ink",
    "other",
}
CONTEXT_STATUSES = {"observed", "observed_absent", "unknown"}
CARRIERS = [
    "diario-de-poesia-excerpt",
    "agentic-patterns-excerpt",
    "sunset-carrier-sample",
    "bank-statement-ca-excerpt",
]


def _spa() -> str:
    return REPO_SPA.read_text()


def test_spa_exists_in_repo_and_bundle() -> None:
    assert REPO_SPA.is_file(), f"missing {REPO_SPA}"
    assert BUNDLE_SPA.is_file(), f"missing {BUNDLE_SPA}"
    assert REPO_SPA.read_bytes() == BUNDLE_SPA.read_bytes(), (
        "repo and bundle SPA copies have drifted apart"
    )


def test_spa_is_selfcontained_no_external_resources() -> None:
    html = _spa()
    # No network fetches or external references of any kind. localhost is
    # allowed: the documented last-resort troubleshooting step serves the
    # bundle from the reader's own machine (python3 -m http.server).
    for pattern in ("<script src", "<link ", "<img ", "fetch(", "XMLHttpRequest",
                    "sendBeacon", "import "):
        assert pattern not in html, f"SPA must be offline-only: found {pattern!r}"
    assert not re.search(r"https://(?!localhost)", html), "non-local https reference"
    assert not re.search(r"http://(?!localhost)", html), "non-local http reference"


def test_spa_emits_every_template_key() -> None:
    html = _spa()
    for key in TEMPLATE:
        assert key in html, f"template key {key!r} missing from SPA"


def test_spa_emits_schema_vocabularies() -> None:
    html = _spa()
    for kind in CONTEXT_KINDS:
        assert kind in html, f"context kind {kind!r} missing"
    for rot in ROTATIONS:
        assert rot in html, f"rotation value {rot!r} missing"
    for col in COLUMN_VALUES:
        assert col in html, f"column value {col!r} missing"
    for ann in ANNOTATION_TYPES:
        assert ann in html, f"annotation type {ann!r} missing"
    for status in CONTEXT_STATUSES:
        assert status in html, f"context status {status!r} missing"


def test_spa_offers_all_carriers() -> None:
    html = _spa()
    for carrier in CARRIERS:
        assert carrier in html, f"carrier {carrier!r} not offered by SPA"


def test_spa_supports_reader_ids_and_timing() -> None:
    html = _spa()
    assert "reader-a" in html and "reader-b" in html, "reader ids missing"
    assert "elapsed_minutes" in html, "elapsed timing missing"


def test_spa_serializes_unknown_as_schema_expects() -> None:
    """Tri-state booleans must serialize null for unknown; text unknowns stay
    the literal string 'unknown'."""
    html = _spa()
    assert "null" in html, "tri-state unknown must serialize as null"
    assert re.search(r"['\"]unknown['\"]", html), "text fields must offer 'unknown'"


def test_spa_documents_no_winner_election_and_unknown_is_an_answer() -> None:
    html = _spa()
    assert "unknown" in html
    # The ground rules must reach the reader through the UI itself.
    assert re.search(r"[Dd]o not resolve", html), "no-smoothing rule missing"
    assert re.search(r"[Ss]topwatch", html), "timing instruction missing"


def test_spa_is_a_guided_wizard_with_embedded_instructions() -> None:
    """The SPA must be self-explanatory: steps and CTAs embedded, no external
    README required."""
    html = _spa()
    # Step-by-step flow with navigation CTAs.
    assert re.search(r"Next\b", html), "wizard Next CTA missing"
    assert re.search(r"Back\b", html), "wizard Back CTA missing"
    # The reader must be told, in the UI, to open the carrier in a viewer.
    assert re.search(r"Open the carrier in a normal (PDF|viewer)", html), (
        "carrier-viewing instruction missing"
    )
    # The per-section field guidance must be embedded, not referenced.
    for guidance in (
        "nothing selectable",
        "continuation: a sentence or flow",
        "you looked and it is not there",
        "Do not add your own",
        "image content",
    ):
        assert guidance in html, f"embedded guidance missing: {guidance!r}"
    # Return instructions must be embedded too.
    assert re.search(r"zip", html.lower()), "zip-and-return instruction missing"
    assert re.search(r"Do not commit", html), "no-commit instruction missing"
    # Multi-carrier progress must be visible.
    assert re.search(r"carrier 1 of 4|Next carrier", html), "carrier progress missing"


def test_spa_embeds_the_carrier_viewer() -> None:
    """The carriers to check must be viewable inside the SPA itself (native
    browser PDF rendering), with a same-folder fallback and an EPUB note."""
    html = _spa()
    # The viewer points at the bundle-relative carriers directory.
    assert re.search(r"\.\./carriers/", html), "embedded carrier path missing"
    assert re.search(r'el\("object"', html), "embedded viewer element missing"
    # Graceful fallback when a browser refuses to render the file inline:
    # a direct new-tab link first, then the local-server last resort.
    assert re.search(r"Open in new tab", html), "new-tab fallback link missing"
    assert re.search(r"target=\"_blank\"", html), "new-tab link missing"
    assert re.search(r"http\.server", html), "local-server troubleshooting recipe missing"
    assert re.search(r"does not display|If the carrier does not", html), (
        "viewer fallback instruction missing"
    )
    # EPUB cannot render natively in browsers — the reader must be told.
    assert re.search(r"EPUB reader|EPUB cannot", html), "EPUB viewing note missing"
    # Using the built-in viewer must be explicitly allowed by the rules.
    assert re.search(r"built-in viewer[^<]*counts as", html), (
        "viewer-is-a-normal-viewer clarification missing"
    )
