# Purpose: Queue-to-SPA wiring (sunset-3oq task 3.2): build review bundles
#   from the derived queue using the EXISTING visual-review SPA template —
#   one review path, one human-evidence record; and map the verdicts that
#   SPA emits back to human-origin claims (sunset-3oq 3.1, dedupe 1.1).
# Responsibilities: (1) crop references resolved from the descriptor's
#   declared geometry (region ids are claim anchors); (2) build_queue_bundle
#   — render pages, embed queue items in the SPA's carriers/pages/regions
#   data-island shape, record the queue with crop references; (3)
#   verdicts_to_decisions — agree → human accept claim, differ → human
#   rejected claim, unknown → no claim (the item stays queued); anchored
#   region ids that no queued claim uses produce no claim. Model claims are
#   never mutated.
# Rationale: design decision "duplicating the HITL review path would fork
#   the human-evidence record". Render crops are correlated lineage and are
#   labeled as such by digitization.render; they are for human review only.
"""Review queue bundles and verdict-to-decision mapping."""
import base64
import json
from pathlib import Path

from digitization.render import (crop_reference, page_frames, render_page)
from dsc03.review_queue import decide, review_queue
from dsc03.visual.review import TEMPLATE_PATH

DATA_ISLAND = "__REVIEW_DATA_ISLAND__"
REVIEW_PROVENANCE = "REVIEW-QUEUE-SPA"


def _geometry_profile_digest(descriptor):
    """The declared geometry profile's pinned digest; None when undeclared."""
    for profile in descriptor.get("profiles", []):
        if profile.get("kind") == "geometry":
            return profile.get("sha256")
    return None


def _region_geometry(descriptor):
    """region id -> declared geometry box (page-pt frame), from DSC 0.3
    descriptors as produced by `python3 -m digitization run`."""
    return {r["id"]: r["geometry"]
            for r in descriptor.get("regions", []) if "geometry" in r}


def crop_references(descriptor, source, dpi):
    """Pinned crop references for every declared region geometry."""
    digest = _geometry_profile_digest(descriptor)
    boxes = _region_geometry(descriptor)
    if not boxes:
        return {}
    frames = page_frames(source, sorted({b["page"] for b in boxes.values()}))
    refs = {}
    for region_id, box in boxes.items():
        frame = frames[box["page"]]
        render_record = {
            "page_frame": f"page-{box['page']}-pt",
            "width_pt": frame["width"], "height_pt": frame["height"],
        }
        refs[region_id] = crop_reference(digest, render_record, box)
    return refs


def build_queue_bundle(descriptor, claims, source, out_path, dpi=72,
                       reviewer=None):
    """Derive the queue, render the pages it anchors, and embed everything
    into the existing review SPA template. Returns the embedded record."""
    refs = crop_references(descriptor, source, dpi)
    queue = review_queue(claims, crop_references=refs)
    boxes = _region_geometry(descriptor)
    scale = dpi / 72.0

    pages = {}
    for region_id, box in sorted(boxes.items()):
        pages.setdefault(box["page"], []).append((region_id, box))

    page_records = []
    for page_number in sorted(pages):
        png, meta = render_page(source, page_number, dpi)
        page_records.append({
            "page": page_number,
            "image": "data:image/png;base64,"
                     + base64.b64encode(png).decode("ascii"),
            "width": meta["width_px"], "height": meta["height_px"],
            "regions": [
                {"id": region_id,
                 "rect_px": [round(box["x"] * scale),
                             round(box["y"] * scale),
                             round(box["w"] * scale),
                             round(box["h"] * scale)]}
                for region_id, box in pages[page_number]
            ],
        })

    record = {
        "kind": "review-queue-bundle",
        "reviewer": reviewer,
        "rules": review_queue.__doc__.split(".")[0],
        "carriers": [{"carrier": descriptor["id"],
                      "pages": page_records}],
        "queue": queue,
        "provenance": REVIEW_PROVENANCE,
    }
    template = TEMPLATE_PATH.read_text()
    embedded = json.dumps(record, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace(DATA_ISLAND, embedded)
    assert DATA_ISLAND not in html
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return record


def verdicts_to_decisions(verdicts, desc, claims):
    """Map the existing SPA's verdicts JSON to human-origin claims.

    agree → accept (human claim repeating the canonical value), differ →
    reject (human claim, status rejected), unknown → nothing recorded
    (unknown is an answer; the item stays queued). Regions that anchor no
    queued claim produce no claim — verdicts are never fabricated into
    claims. Provenance is carried as non-semantic metadata; the model
    claims are never mutated.
    """
    reviewer = verdicts.get("reviewer")
    queued = review_queue(claims)
    human = []
    for carrier in verdicts.get("carriers", []):
        for page in carrier.get("pages", []):
            for region in page.get("regions", []):
                verdict = region.get("verdict")
                if verdict not in ("agree", "differ"):
                    continue
                # only regions anchoring a queued claim resolve to a decision
                items = [i for i in queued if region["id"] in i["scope"]]
                if not items:
                    continue
                item = items[0]
                model = next(c for c in claims if c["id"] == item["claim_id"])
                action = "accept" if verdict == "agree" else "reject"
                decision = decide(desc, model, action, reviewer=reviewer)
                decision["review_provenance"] = REVIEW_PROVENANCE
                human.append(decision)
    return human
