# Purpose: Slice-4 Part A tests for the document structural debugger's
#   accessibility / keyboard / interaction surface (sunset-xx7.4,
#   add-document-structural-debugger).
# Responsibilities: Assert a modeled keyboard-only selection flow reaches
#   every inspectable detail (region -> loci -> evidence -> diagnostic) with
#   no pointer input; assert all statuses are text tokens, never color-only;
#   assert offline operation (no socket/network use, deterministic outputs);
#   assert PDF loci survive a modeled rotation only via an explicit remap
#   (identity never silently mutated) and EPUB CFI identity persists after a
#   modeled viewport reflow; assert malformed descriptors/locators produce
#   classified diagnostics and never crash or silently pass; record one honest
#   wall-time measurement of inspection over a pinned carrier fixture in the
#   output with NO performance-win claims.
# Rationale: document-debugger spec deltas (keyboard_navigation,
#   pdf_epub_no_ocr, typed_diagnostics, read_only). Pure test work over the
#   shipped dsc03.inspect / dsc03.locators / dsc03.adapters surfaces; no edits
#   to openspec/ trees, no OCR, no network, no performance claims.
"""Debugger a11y/keyboard/interaction tests (sunset-xx7.4 Part A)."""
import dataclasses
import hashlib
import json
import socket
import sys
import time
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import adapters
from dsc03 import inspect as dbg
from dsc03 import locators
from dsc03 import validator

CARRIERS = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"
PDF = CARRIERS / "accounting-made-simple-excerpt.pdf"
EPUB = CARRIERS / "sunset-carrier-sample.epub"
PINNED_FIXTURE = Path(__file__).parent / "fixture_minimal.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _selector_profile(desc, profile_id, uri):
    desc["profiles"].append(
        {"id": profile_id, "kind": "selector", "uri": uri, "version": "1",
         "sha256": sha(json.dumps({"uri": uri}, sort_keys=True).encode())}
    )


def _geometry_profile(desc, profile_id, uri):
    desc["profiles"].append(
        {"id": profile_id, "kind": "geometry", "uri": uri,
         "version": "1", "sha256": sha(uri.encode())}
    )


def _pdf_descriptor(tmp_path):
    """Pinned real-carrier PDF descriptor with one selector-pinned region."""
    desc = adapters.describe_pdf(PDF, Path(tmp_path))
    _selector_profile(desc, "p-sel", "pdf-selectors.json")
    _geometry_profile(desc, "p-geo", "geometry-page-pt.json")
    for r in desc["regions"]:
        if r["id"] == "pg2":
            r["geometry"] = {"profile_id": "p-geo", "space": "page-pt",
                             "x": 36, "y": 72, "width": 180, "height": 40}
    desc["selectors"].append({
        "id": "sel-p1", "kind": "pdf-area", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "pg2",
        "locator": "page:2 rect:36,72,180,40",
    })
    assert validator.validate(desc) == []
    return desc


def keyboard_only_selection_flow(index, start_view_id):
    """Modeled keyboard-only navigation over the inspection index.

    Every step consumes ONLY text tokens already present in the index
    (ids, statuses, reasons): containment order plays the role of Tab
    traversal, Enter plays the role of inspect. No coordinate, hit-test or
    pointer input exists anywhere in this function's inputs or decisions —
    that structural absence is part of what the a11y tests assert.
    """
    steps = []
    containment = index.containment(start_view_id)
    root = index.views[start_view_id]["root"]
    ring = [root]
    i = 0
    while i < len(ring):  # Tab-order traversal over containment tree
        region_id = ring[i]
        steps.append(("focus", region_id))
        ring.extend(containment.get(region_id, ()))
        i += 1
    for step in steps:
        if step[0] != "focus":
            continue
        region_id = step[1]
        selection = locators.resolve(index, region_id)
        # Enter: inspect the focused node. The outcome is a text status, and
        # every inspectable detail is reachable through text only.
        steps.append(("status", selection.status))
        if selection.status == "resolved":
            for locus in selection.loci:
                steps.append(("locus", locus.value, locus.domain))
            for evidence_id in selection.evidence_ids:
                steps.append(("evidence", evidence_id))
    return steps


# -- (1) keyboard-only flow reaches every inspectable detail ----------------------
def test_keyboard_only_flow_reaches_region_loci_evidence_diagnostic(tmp_path):
    """The modeled keyboard-only flow walks containment order (Tab), resolves
    each region (Enter), and reaches loci -> evidence -> diagnostics for every
    inspectable detail without any pointer/coordinate input."""
    desc = _pdf_descriptor(tmp_path)
    index = dbg.build_index(desc)
    view_id = desc["views"][0]["id"]
    root = index.views[view_id]["root"]

    steps = keyboard_only_selection_flow(index, view_id)

    # The whole containment tree was traversed by keyboard alone.
    reachable = {s[1] for s in steps if s[0] == "focus"}
    assert root in reachable
    containment = index.containment(view_id)
    expected = {root}
    frontier = [root]
    while frontier:
        cur = frontier.pop()
        kids = containment.get(cur, ())
        expected.update(kids)
        frontier.extend(kids)
    assert reachable == expected  # every region is keyboard-focusable

    # Every region produced an explicit text status (nothing pointer-gated).
    statuses = [s[1] for s in steps if s[0] == "status"]
    assert len(statuses) == len(reachable)
    assert all(s in ("resolved", "missing", "ambiguous", "unsupported")
               for s in statuses)

    # The selector-pinned region reaches the FULL chain: loci -> evidence.
    chain_loci = [tok for kind, *tok in steps if kind == "locus"]
    chain_evidence = [tok[0] for kind, *tok in steps if kind == "evidence"]
    assert ("page:2 rect:36,72,180,40", "pdf-fixed-coordinate") in [
        tuple(t) for t in chain_loci]
    assert "ev-txt2" in chain_evidence
    assert all(e in index.evidence for e in chain_evidence)

    # Diagnostics close the chain: typed categories, text rule ids, witnesses.
    diagnostics = dbg.diagnose(index, [])
    assert diagnostics, "inspection must terminate in a typed diagnostic"
    for d in diagnostics:
        assert d.category in dbg.CATEGORIES
        assert d.rule_id and isinstance(d.rule_id, str)
        assert d.witness is None or isinstance(d.witness, str)


# -- (2) non-color status labels ---------------------------------------------------
def test_status_labels_are_text_tokens_never_color_only(tmp_path):
    """All user-facing statuses on the interaction surface are text tokens
    ('resolved', 'missing', 'violated', ...) with stable rule ids and reasons;
    no ANSI color escapes appear anywhere in the rendered outputs."""
    desc = _pdf_descriptor(tmp_path)
    index = dbg.build_index(desc)

    resolved = locators.resolve(index, "pg2")
    missing = locators.resolve(index, "no-such-region")
    for sel in (resolved, missing):
        assert sel.status.isalnum() or all(
            part.isalnum() for part in sel.status.split("_"))
        if sel.status != "resolved":
            assert sel.reason, "non-resolved states carry a text reason"

    bad_scheme, bad_reason = locators.classify_locator("not-a-real-scheme:1")
    assert bad_scheme is None
    assert isinstance(bad_reason, str) and bad_reason

    for d in dbg.diagnose(index, []):
        blob = json.dumps(dataclasses.asdict(d))
        assert "\x1b[" not in blob, "no ANSI color escapes in diagnostics"
    for sel in (resolved, missing):
        blob = json.dumps(dataclasses.asdict(sel))
        assert "\x1b[" not in blob, "no ANSI color escapes in selections"


# -- (3) offline operation: no network, deterministic outputs ----------------------
def test_offline_operation_no_socket_deterministic_outputs(tmp_path, monkeypatch):
    """The inspection surface runs with every socket constructor forbidden and
    yields byte-identical results across two runs (no network, no clocks in
    the output)."""
    def _no_network(*args, **kwargs):
        raise AssertionError("network access attempted during offline run")

    monkeypatch.setattr(socket, "socket", _no_network)
    monkeypatch.setattr(socket, "create_connection", _no_network)
    monkeypatch.setattr(socket, "getaddrinfo", _no_network)

    desc = _pdf_descriptor(tmp_path)
    path = tmp_path / "offline.json"
    path.write_text(json.dumps(desc, sort_keys=True), encoding="utf-8")

    runs = [dbg.inspect(path) for _ in range(2)]
    for r in runs:
        assert r.unchanged_bytes
    digests = [
        sha(json.dumps(
            [dataclasses.asdict(d) for d in r.diagnostics],
            sort_keys=True).encode())
        for r in runs
    ]
    assert digests[0] == digests[1], "offline inspection is deterministic"
    assert runs[0].descriptor_sha256 == runs[1].descriptor_sha256

    # Static belt-and-braces: no network modules imported by the shipped layer.
    for mod in (dbg, locators):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for needle in ("import socket", "import urllib", "import http",
                       "import requests", "urlopen"):
            assert needle not in src


# -- (4) PDF rotation: explicit remap, never silent mutation ------------------------
def test_pdf_loci_survive_modeled_rotation_with_explicit_remap(tmp_path):
    """A modeled 90-degree page rotation changes nothing in the stored
    fixed-coordinate identity (Locus is frozen); any rotated-rect view must be
    computed by an explicit remap, never by mutating the locus."""
    desc = _pdf_descriptor(tmp_path)
    index = dbg.build_index(desc)
    before = locators.resolve(index, "pg2")
    assert before.status == "resolved"
    locus = before.loci[0]
    assert locus.domain == "pdf-fixed-coordinate"
    assert locus.rect == (36, 72, 180, 40)
    assert locus.display_rect is None

    # Identity cannot be silently mutated even by accident: frozen dataclass.
    try:
        locus.rect = (0, 0, 0, 0)
        raised = False
    except dataclasses.FrozenInstanceError:
        raised = True
    assert raised, "Locus identity must resist silent mutation"

    def rotate90(rect, page_w, page_h):
        """The ONLY rotation path: an explicit, pure coordinate remap."""
        x, y, w, h = rect
        return (page_h - (y + h), x, h, w)

    page_w, page_h = 612, 792  # modeled letter page box, declared explicitly
    rotated = rotate90(locus.rect, page_w, page_h)
    assert rotated == (680, 36, 40, 180)
    rotated_locus = locators.Locus(
        domain=locus.domain, kind=locus.kind, value=locus.value,
        page=locus.page, rect=rotated)
    display = locators.to_display(rotated_locus, zoom=1.0)
    assert display == rotated  # display derivation is explicit and on demand

    # After the modeled rotation, re-resolution yields the identical intrinsic
    # loci: rotation is a view transform, identity is the fixed-coordinate
    # domain and it survives unchanged (pdf_epub_no_ocr shape).
    after = locators.resolve(index, "pg2")
    assert after.loci == before.loci
    assert after.loci[0].rect == (36, 72, 180, 40)


# -- (5) EPUB reflow: CFI identity persists ----------------------------------------
def test_epub_cfi_identity_persists_after_modeled_reflow(tmp_path):
    """After a modeled viewport reflow (new transient geometry), the EPUB CFI
    selection identity is unchanged; viewport locators never become loci."""
    sidecar = json.loads(
        (CARRIERS / "sunset-carrier-sample-annotations.json").read_bytes())
    cfi = next(a["target"] for a in sidecar["annotations"] if a["id"] == "a1")

    desc = adapters.describe_epub(EPUB, Path(tmp_path))
    _selector_profile(desc, "p-sel", "epub-selectors.json")
    desc["regions"].append({"id": "r-ch1", "view_id": "v-main",
                            "kind": "chapter"})
    desc["selectors"].append({
        "id": "sel-a1", "kind": "epub-fragment", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "r-ch1",
        "locator": cfi,
    })
    index = dbg.build_index(desc)
    before = locators.resolve(index, "r-ch1")
    assert before.status == "resolved"
    assert [l.value for l in before.loci] == [cfi]
    assert all(l.domain == "epub-stable-selector" for l in before.loci)

    # Modeled reflow: the reader reports new viewport geometry for the region.
    desc["selectors"].append({
        "id": "sel-a1-vp", "kind": "epub-fragment", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "r-ch1",
        "locator": "viewport rect:0,0,320,640 zoom:1.5",
    })
    index = dbg.build_index(desc)
    after = locators.resolve(index, "r-ch1")
    assert after.status == "resolved"
    assert [l.value for l in after.loci] == [cfi], \
        "CFI identity persists across reflow"
    assert not any(l.domain == "viewport" for l in after.loci), \
        "transient viewport geometry never becomes persistent identity"


# -- (6a) malformed locators: classified, never crash -------------------------------
def test_malformed_locators_classified_never_crash(tmp_path):
    """Malformed locator inputs (empty, unknown scheme, viewport-transient,
    non-string, absent key) are classified with explicit reasons; resolve()
    reports unsupported/missing states and never raises or silently passes."""
    for bad in ("", "   ", "garbage", "page:zz rect:nope", 12345, None):
        scheme, reason = locators.classify_locator(bad)
        assert scheme is None
        assert isinstance(reason, str) and reason, \
            f"malformed locator {bad!r} gets a classified reason"

    desc = _pdf_descriptor(tmp_path)
    desc["regions"].append({"id": "pg-bad", "view_id": desc["views"][0]["id"],
                            "kind": "page"})
    desc["selectors"].extend([
        {"id": "sel-none", "kind": "pdf-area", "profile_id": "p-sel",
         "source_sha256": desc["source"]["sha256"], "target": "pg-bad",
         "locator": None},
        {"id": "sel-nokey", "kind": "pdf-area", "profile_id": "p-sel",
         "source_sha256": desc["source"]["sha256"], "target": "pg-bad"},
        {"id": "sel-vp", "kind": "pdf-area", "profile_id": "p-sel",
         "source_sha256": desc["source"]["sha256"], "target": "pg-bad",
         "locator": "viewport rect:0,0,10,10"},
        {"id": "sel-vp2", "kind": "pdf-area", "profile_id": "p-sel",
         "source_sha256": desc["source"]["sha256"], "target": "pg2",
         "locator": "viewport rect:0,0,10,10"},
    ])
    index = dbg.build_index(desc)
    sel = locators.resolve(index, "pg-bad")  # must not raise
    assert sel.status == "unsupported"
    assert sel.reason, "unsupported selection carries a classified reason"
    for marker in ("non-string locator: NoneType",
                   "viewport coordinates are transient"):
        assert marker in sel.reason, \
            f"classified reason missing marker: {marker}"
    assert not sel.loci

    # Mixed case: usable selector keeps the target resolvable, but the
    # malformed selectors' classified reasons are surfaced, not dropped.
    mixed = locators.resolve(index, "pg2")
    assert mixed.status == "resolved"
    assert any(l.value == "page:2 rect:36,72,180,40" for l in mixed.loci)
    assert mixed.reason, "mixed malformed selectors are surfaced, not silent"
    assert "sel-vp2" in mixed.reason and "viewport" in mixed.reason


# -- (6b) malformed descriptors: classified diagnostics, never crash ----------------
def test_malformed_descriptor_classified_never_crash(tmp_path):
    """A parseable-JSON file that is not a 0.3 descriptor yields the classified
    violated diagnostic dsc03.invalid_shape — not a crash and not a silent
    pass; unparsable input raises the typed DescriptorParseError."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "a descriptor"}', encoding="utf-8")
    result = dbg.inspect(bad)  # must not raise
    cats = {(d.category, d.rule_id) for d in result.diagnostics}
    assert ("violated", "dsc03.invalid_shape") in cats, \
        f"malformed descriptor classified, got: {cats}"
    assert all(d.category in dbg.CATEGORIES for d in result.diagnostics)
    assert result.unchanged_bytes

    unparsable = tmp_path / "unparsable.json"
    unparsable.write_bytes(b"{not json at all")
    with pytest.raises(dbg.DescriptorParseError):
        dbg.inspect(unparsable)


# -- (7) honest wall-time measurement, no performance-win claims --------------------
def test_inspection_wall_time_recorded_no_claims(tmp_path):
    """Measure real wall-clock time of one full inspection pass over the
    pinned committed fixture and record the measurement in the output.
    Assertions cover the MEASUREMENT only: no speed claims, no bounds beyond
    a positive, finite, non-clock-polluted value."""
    if not PINNED_FIXTURE.is_file():
        pytest.skip(f"pinned fixture missing: {PINNED_FIXTURE}")

    measured = []
    for _ in range(2):
        t0 = time.perf_counter()
        result = dbg.inspect(PINNED_FIXTURE)
        elapsed = time.perf_counter() - t0
        assert result.unchanged_bytes
        assert result.diagnostics  # the pass actually did the work
        measured.append(elapsed)

    assert all(m > 0.0 for m in measured), "wall time honestly measured"
    assert all(m == m and m != float("inf") for m in measured)

    record = {
        "fixture": str(PINNED_FIXTURE.relative_to(
            Path(__file__).resolve().parents[2])),
        "runs": 2,
        "wall_time_s": [round(m, 6) for m in measured],
        "claim": "measurement only; no performance-win claim is made",
    }
    warnings.warn(
        "inspection wall-time record (measurement only, no perf claim): "
        + json.dumps(record, sort_keys=True),
        UserWarning,
        stacklevel=1,
    )
