# Purpose: Native word/line/block descriptor regions and derived side files
#   (add-scale-complete-regions tasks 3.1, 3.2, 3.3).
# Responsibilities: Words and lines appear as descriptor regions with
#   interval+box selectors; line-map.json and page-map.json regenerate
#   byte-identically from the descriptor; the manifest is version 3 and any
#   other manifest version is refused as unsupported-version.
# Rationale: add-scale-complete-regions "Native regions below page level".
import json

from digitization.native import (OUTCOME_MANIFEST_VERSION, export_line_map,
                                 export_page_map, extract)
from digitization.native_inspection import inspect_native


def layout_pdf(path):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.insert_text((72, 72), "Native regions below page level scale cleanly.")
    page.insert_text((72, 120), "A second line of body text for the ladder.")
    doc.save(str(path))
    doc.close()


def _extract(tmp_path):
    source = tmp_path / "src.pdf"
    layout_pdf(source)
    output = tmp_path / "run"
    result = extract(source, output)
    assert result["status"] in ("text-complete", "text-with-gaps")
    return output


def _descriptor(output):
    return json.loads((output / "descriptor.json").read_text(encoding="utf-8"))


def test_manifest_is_version_3(tmp_path):
    output = _extract(tmp_path)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == OUTCOME_MANIFEST_VERSION == "3"


def test_words_and_lines_appear_as_descriptor_regions_with_interval_box_selectors(tmp_path):
    output = _extract(tmp_path)
    desc = _descriptor(output)
    words = json.loads((output / "word-map.json").read_text(encoding="utf-8"))
    regions_by_kind = {}
    for region in desc["regions"]:
        regions_by_kind.setdefault(region["kind"], []).append(region)
    assert regions_by_kind.get("word"), "no word regions in descriptor"
    assert regions_by_kind.get("line"), "no line regions in descriptor"
    assert regions_by_kind.get("block"), "no block regions in descriptor"
    sel_by_target = {s["target"]: s for s in desc["selectors"] if s["kind"] == "pdf-area"}
    word_intervals = set()
    for region in regions_by_kind["word"]:
        selector = sel_by_target[region["id"]]
        page, (start, end), box = _parse(selector["locator"])
        assert end > start
        word_intervals.add((page, start, end))
        assert len(box) == 4 and box[2] > box[0] and box[3] > box[1]
    # every retained word-map entry has exactly one matching word region
    expected = {(w["page"], w["raw_start"], w["raw_end"]) for w in words}
    assert word_intervals == expected
    # ladder: each word region sits inside a line via a contains edge
    parents = {r["to"]: r["from"] for r in desc["relations"] if r["kind"] == "contains"}
    kinds = {r["id"]: r["kind"] for r in desc["regions"]}
    for region in regions_by_kind["word"]:
        assert kinds[parents[region["id"]]] == "line"
    for region in regions_by_kind["line"]:
        assert kinds[parents[region["id"]]] == "block"
    for region in regions_by_kind["block"]:
        assert kinds[parents[region["id"]]] == "page"


def _parse(locator):
    scope, rest = locator.split("/", 1)
    span, box = rest.split("[", 1)[1].split(")/box=[", 1)
    start, end = (int(v) for v in span.split(","))
    return int(scope.split(":", 1)[1]), (start, end), [int(v) for v in box.rstrip("]").split(",")]


def test_line_map_regenerates_byte_identically_from_descriptor(tmp_path):
    output = _extract(tmp_path)
    original = (output / "line-map.json").read_bytes()
    desc = _descriptor(output)
    raw = (output / "raw.txt").read_text(encoding="utf-8")
    (output / "line-map.json").unlink()
    regenerated = export_line_map(desc, raw)
    (output / "line-map.json").write_bytes(regenerated)
    assert regenerated == original


def test_page_map_regenerates_byte_identically_from_descriptor(tmp_path):
    output = _extract(tmp_path)
    original = (output / "page-map.json").read_bytes()
    desc = _descriptor(output)
    geometry = next(p for p in desc["profiles"] if p["kind"] == "geometry")
    geometry_bytes = (output / geometry["uri"]).read_bytes()
    (output / "page-map.json").unlink()
    regenerated = export_page_map(json.loads(geometry_bytes))
    (output / "page-map.json").write_bytes(regenerated)
    assert regenerated == original


def test_inspection_verifies_derived_exports(tmp_path):
    output = _extract(tmp_path)
    report = inspect_native(output)
    assert report["status"] in ("text-complete", "text-with-gaps")
    # tamper with the derived line-map: inspection must refuse
    lines = json.loads((output / "line-map.json").read_text(encoding="utf-8"))
    lines[0]["text"] = "tampered"
    data = (json.dumps(lines, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode()
    (output / "line-map.json").write_bytes(data)
    import hashlib
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    manifest["artifacts"]["line-map.json"]["sha256"] = hashlib.sha256(data).hexdigest()
    semantic = {n: r["sha256"] for n, r in sorted(manifest["artifacts"].items())}
    manifest["semantic_artifacts"] = semantic
    manifest["semantic_sha256"] = hashlib.sha256(
        (json.dumps(semantic, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode()).hexdigest()
    (output / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode())
    from digitization.inspection import IntegrityError
    try:
        inspect_native(output)
    except IntegrityError:
        pass
    else:
        raise AssertionError("tampered derived line-map not refused")


def test_unknown_manifest_version_refused_as_unsupported_version(tmp_path):
    output = _extract(tmp_path)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    manifest["version"] = "9"
    (output / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode())
    report = inspect_native(output)
    assert report["status"] == "unsupported-version"
    assert report["reason"] == "unsupported-version"
