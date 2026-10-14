# Purpose: Real-carrier adapter tests (sunset-r68.11, tasks.md 3.1).
# Responsibilities: Verify that dsc03.adapters turns the committed real
#   PDF/EPUB carriers (fixtures/carriers/) into 0.3 descriptors that (a)
#   validate clean against the 0.3 schema, (b) pass scoped-coverage
#   verification with enumeration computed from the actual source bytes, and
#   (c) preserve the source observations actually present in the carrier
#   (pages, text, images, vectors, annotations; EPUB manifest/spine/nav and
#   every archive member). The canned tracer fixtures are not used here:
#   synthetic descriptors do not count per tasks.md 3.1.
# Rationale: add-dsc-03 document-adapters "Independent coverage inventory" and
#   "Scoped coverage dispositions" applied to real carriers.
"""Real PDF/EPUB carrier adapters preserve source observations (sunset-r68.11)."""
import tempfile
import zipfile
from pathlib import Path

import pymupdf

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import adapters, coverage, profiles, validator

CARRIERS = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"
PDF = CARRIERS / "agentic-patterns-excerpt.pdf"
EPUB = CARRIERS / "sunset-carrier-sample.epub"


def pdf_pages(path):
    with pymupdf.open(stream=path.read_bytes(), filetype="application/pdf") as doc:
        return doc.page_count


def pdf_annot_count(path):
    n = 0
    with pymupdf.open(stream=path.read_bytes(), filetype="application/pdf") as doc:
        for page in doc:
            n += len(list(page.annots()))
    return n


def real_pdf_enumerator(fmt, kind):
    """Enumeration from the real carrier bytes (not a canned page count)."""
    if fmt != "application/pdf":
        return None
    if kind == "document":
        return ["document"]
    if kind == "pdf-page":
        return [f"page:{i}" for i in range(1, pdf_pages(PDF) + 1)]
    return None


def real_epub_enumerator(fmt, kind):
    if fmt != "application/epub+zip":
        return None
    if kind == "document":
        return ["document"]
    if kind == "epub-resource":
        with zipfile.ZipFile(EPUB) as z:
            return [
                f"resource:{n}"
                for n in z.namelist()
                if not n.endswith("/")
            ]
    return None


def _resolved(descriptor, root):
    registry = profiles.Registry(root)
    return {p["id"]: profiles.resolve(p, registry) for p in descriptor["profiles"]}


# -- PDF adapter -----------------------------------------------------------------
def test_pdf_adapter_descriptor_is_schema_valid():
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_pdf(PDF, Path(out))
        assert validator.validate(d) == []


def test_pdf_adapter_coverage_verified_against_real_bytes():
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_pdf(PDF, Path(out))
        report = coverage.verify(d, _resolved(d, Path(out)), real_pdf_enumerator)
        assert report["reasons"] == []
        assert report["summaries"]["pdf:glyphs"] == "preserved"
        assert report["summaries"]["pdf:annotations"] == "preserved"
        # attachment disposition must reflect the real carrier: supported when
        # embedded files exist, preserved-after-verified-absence when they don't
        with pymupdf.open(stream=PDF.read_bytes(), filetype="application/pdf") as doc:
            has_attachments = doc.embfile_count() > 0
        expected = "unsupported" if has_attachments else "preserved"
        assert report["summaries"]["pdf:attachments"] == expected


def test_pdf_adapter_preserves_source_annotations():
    n = pdf_annot_count(PDF)
    assert n > 0  # the carrier really does carry annotations
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_pdf(PDF, Path(out))
        assert len(d["annotations"]) == n
        assert all(a["origin"] == "source" for a in d["annotations"])
        assert all(a["term"].startswith("ex:") for a in d["annotations"])


def test_pdf_adapter_records_every_page_and_text():
    pages = pdf_pages(PDF)
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_pdf(PDF, Path(out))
        page_regions = [r for r in d["regions"] if r["kind"] == "page"]
        assert len(page_regions) == pages
        with pymupdf.open(stream=PDF.read_bytes(), filetype="application/pdf") as doc:
            textual = sum(1 for p in doc if p.get_text().strip())
        assert len(d["contents"]) == textual


def test_pdf_adapter_inventory_and_manifest_artifacts_are_written():
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_pdf(PDF, Path(out))
        root = Path(out)
        assert (root / "inventory.json").is_file()
        assert (root / "manifest.json").is_file()
        statuses = {p["id"]: s for p, (s, _) in zip(d["profiles"], [profiles.resolve(p, profiles.Registry(root)) for p in d["profiles"]])}
        assert all(s == "resolved" for s in statuses.values())


# -- EPUB adapter ----------------------------------------------------------------
def test_epub_adapter_descriptor_is_schema_valid():
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_epub(EPUB, Path(out))
        assert validator.validate(d) == []


def test_epub_adapter_coverage_verified_against_real_bytes():
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_epub(EPUB, Path(out))
        report = coverage.verify(d, _resolved(d, Path(out)), real_epub_enumerator)
        assert report["reasons"] == []
        assert report["summaries"]["epub:manifest"] == "preserved"
        assert report["summaries"]["epub:spine"] == "preserved"
        assert report["summaries"]["epub:navigation"] == "preserved"
        assert report["summaries"]["epub:resources"] == "preserved"


def test_epub_adapter_covers_every_archive_member():
    with zipfile.ZipFile(EPUB) as z:
        members = {f"resource:{n}" for n in z.namelist() if not n.endswith("/")}
    with tempfile.TemporaryDirectory() as out:
        d = adapters.describe_epub(EPUB, Path(out))
        scopes = {c["scope"] for c in d["coverage"] if c["feature"] == "epub:resources"}
        assert scopes == members
