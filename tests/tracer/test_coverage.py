# Purpose: Coverage inventory/manifest grammar and scoped disposition tests
#   (sunset-r68.6, tasks.md 2.2 + 3.2).
# Responsibilities: Validate carrier-inventory and adapter-manifest artifacts
#   (exact shapes, minimum feature inventories per source format, manifest
#   features within the inventory, version/source_format agreement); verify
#   descriptor coverage: paired profile declarations, exactly one disposition per
#   (inventory, feature, scope), scope grammar matching the feature's scope_kind,
#   manifest membership for preserved/transformed/approximated claims, one
#   adapter run/configuration, enumeration-completeness with the single `*`
#   unexamined replacement, and least-preserving feature summaries.
# Rationale: add-dsc-03 document-adapters "Independent coverage inventory" and
#   "Scoped coverage dispositions".
"""Coverage inventory/manifest + scoped disposition tests (sunset-r68.6)."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import coverage, profiles, validator

PROFILES = Path(__file__).parent / "profiles"
TRACER = Path(__file__).parent / "fixture_minimal.json"
PDF_PAGES = [f"page:{i}" for i in range(1, 11)]
ALL_FEATURES = ("pdf:glyphs", "pdf:images", "pdf:vectors", "pdf:annotations")


def decl(pid, uri, kind):
    return {
        "id": pid, "kind": kind, "uri": uri, "version": "1",
        "sha256": hashlib.sha256((PROFILES / uri).read_bytes()).hexdigest(),
    }


def entry(feature, scope, status, reason=None):
    return {
        "inventory_id": "p-inv", "manifest_id": "p-man", "feature": feature,
        "scope": scope, "status": status, "reason": reason or "",
        "adapter_id": "demo-adapter", "adapter_version": "0.1",
        "config_sha256": "b" * 64,
    }


def full_pages(glyph_status="preserved"):
    """All five inventory features covered across the known 10-page enumeration."""
    es = [entry("pdf:glyphs", s, "preserved") for s in PDF_PAGES[:-1]]
    es.append(entry("pdf:glyphs", PDF_PAGES[-1], glyph_status, "loss on page 10"))
    for f in ALL_FEATURES[1:]:
        es += [entry(f, s, "preserved") for s in PDF_PAGES]
    es.append(entry("pdf:attachments", "document", "unsupported", "not implemented"))
    return es


def star_entries(status="unexamined"):
    es = [entry(f, "*", status, "page count unknown") for f in ALL_FEATURES]
    es.append(entry("pdf:attachments", "*", status, "page count unknown"))
    return es


def pdf_descriptor(entries):
    d = validator.load(TRACER)
    d["profiles"] += [decl("p-inv", "inventory-pdf.json", "carrier-inventory"), decl("p-man", "manifest-pdf.json", "adapter-manifest")]
    d["coverage"] = entries
    return d


def enumerated(fmt, scope_kind):
    if fmt != "application/pdf":
        return None
    return list(PDF_PAGES) if scope_kind == "pdf-page" else ["document"]


def unknown(fmt, scope_kind):
    return None


def resolve(d):
    return {p["id"]: profiles.resolve(p, profiles.Registry(PROFILES)) for p in d["profiles"]}


def verify(d, enum=enumerated):
    return coverage.verify(d, resolve(d), enum)


def test_complete_descriptor_validates_schema_clean():
    assert validator.validate(pdf_descriptor(full_pages())) == []


# -- inventory grammar ---------------------------------------------------------
def test_minimal_pdf_inventory_passes():
    inv = validator.loads((PROFILES / "inventory-pdf.json").read_text())
    assert coverage.inventory_errors(inv) == []


def test_inventory_omitting_minimum_feature_fails():
    short = validator.loads((PROFILES / "inventory-pdf-short.json").read_text())
    assert coverage.inventory_errors(short) == ["invalid_coverage_inventory"]


def test_epub_minimums_pass():
    epub = validator.loads((PROFILES / "inventory-epub.json").read_text())
    assert coverage.inventory_errors(epub) == []


# -- manifest grammar ------------------------------------------------------------
def test_manifest_feature_outside_inventory_is_invalid():
    d = pdf_descriptor([])
    resolved = {p["id"]: profiles.resolve(p, profiles.Registry(PROFILES)) for p in d["profiles"]}
    resolved["p-man"][1]["features"].append("pdf:not-in-inventory")
    assert "invalid_coverage" in verify(d)["reasons"]


def test_manifest_version_must_match_declaration():
    d = pdf_descriptor([])
    resolved = {p["id"]: profiles.resolve(p, profiles.Registry(PROFILES)) for p in d["profiles"]}
    resolved["p-man"][1]["version"] = "2"
    assert "invalid_coverage" in verify(d)["reasons"]


# -- descriptor-level coverage ------------------------------------------------------
def test_unpaired_profile_declarations_are_invalid():
    d = pdf_descriptor([entry("pdf:glyphs", "page:1", "preserved")])
    d["profiles"] = [p for p in d["profiles"] if p["id"] != "p-man"]
    resolved = {p["id"]: profiles.resolve(p, profiles.Registry(PROFILES)) for p in d["profiles"]}
    assert "invalid_coverage" in coverage.verify(d, resolved, enumerated)["reasons"]


def test_no_adapter_run_is_unexamined():
    d = validator.load(TRACER)
    resolved = {p["id"]: profiles.resolve(p, profiles.Registry(PROFILES)) for p in d["profiles"]}
    report = coverage.verify(d, resolved, enumerated)
    assert report["source_coverage"] == "unexamined"
    assert report["reasons"] == []


def test_every_inventory_feature_needs_coverage():
    assert "invalid_coverage" in verify(pdf_descriptor([entry("pdf:glyphs", "page:1", "preserved")]))["reasons"]


def test_duplicate_disposition_is_invalid():
    es = full_pages() + [entry("pdf:glyphs", "page:1", "preserved")]
    assert "invalid_coverage" in verify(pdf_descriptor(es))["reasons"]


def test_scope_kind_must_match_feature():
    es = full_pages()[:-1] + [entry("pdf:attachments", "page:1", "preserved")]
    assert "invalid_coverage" in verify(pdf_descriptor(es))["reasons"]


def test_preserved_claim_needs_manifest_membership():
    es = full_pages()[:-1] + [entry("pdf:attachments", "document", "preserved")]
    assert "invalid_coverage" in verify(pdf_descriptor(es))["reasons"]


def test_adapter_identity_must_match_manifest():
    es = full_pages()
    es[0]["adapter_id"] = "other-adapter"
    assert "invalid_coverage" in verify(pdf_descriptor(es))["reasons"]


# -- enumeration and summaries -------------------------------------------------------
def test_full_enumeration_with_one_omitted_page_summary():
    report = verify(pdf_descriptor(full_pages(glyph_status="omitted")))
    assert report["reasons"] == []
    assert report["summaries"]["pdf:glyphs"] == "omitted"
    assert report["summaries"]["pdf:attachments"] == "unsupported"
    assert report["source_coverage"] == "unsupported"


def test_partial_page_loss_is_omitted():
    report = verify(pdf_descriptor(full_pages(glyph_status="omitted")))
    assert report["summaries"]["pdf:glyphs"] == "omitted"


def test_unknown_enumeration_forbids_finite_scopes():
    assert "invalid_coverage" in verify(pdf_descriptor(full_pages()), unknown)["reasons"]


def test_unknown_enumeration_requires_single_star_entry():
    report = verify(pdf_descriptor(star_entries()), unknown)
    assert report["reasons"] == []
    assert report["summaries"]["pdf:glyphs"] == "unexamined"
    assert report["source_coverage"] == "unexamined"


def test_least_preserving_precedence_in_summary():
    # images: 9 preserved + 1 unexamined -> summary unexamined (beats preserved)
    es = full_pages()
    i = next(j for j, e in enumerate(es) if e["feature"] == "pdf:images" and e["scope"] == "page:10")
    es[i] = entry("pdf:images", "page:10", "unexamined", "page skipped")
    report = verify(pdf_descriptor(es))
    assert report["summaries"]["pdf:images"] == "unexamined"
