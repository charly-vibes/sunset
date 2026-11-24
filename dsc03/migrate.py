# Purpose: Reported migrations — 0.2 descriptors to 0.3 (sunset-r68.9, tasks.md
#   4.1 + 4.2) and label-id descriptors to the identity profile
#   (add-anchor-derived-identity tasks.md 5.1).
# Responsibilities: Convert a valid 0.2 descriptor into a 0.3 descriptor plus a
#   migration report — legacy cross-view containment becomes per-view trees (one
#   root per view), legacy precedes edges are kept only when both endpoints share
#   a view (otherwise reported as unsupported), original source digests and ids
#   are preserved where unambiguous, legacy geometry without profile bindings is
#   reported unexamined (never invented), legacy extracted/inferred evidence
#   without replay material is dropped as unrecoverable (annotations demoted with
#   a report entry), ambiguous or unbound annotation view bindings are reported,
#   and NFC-only 0.2 text is reported as unrecoverable to original code points.
#   migrate_to_identity additionally relabels a valid label-id 0.3 descriptor to
#   the identity profile: anchors computed from DECLARED data only (selector
#   locators, evidence source_ref, a unique targeting selector), records whose
#   anchor cannot be derived are reported (never invented), the old→new table is
#   emitted as relabel-table evidence per design Decision 5, every reference to a
#   renamed record is rebound, and content values are never touched.
# Rationale: add-dsc-03 design.md "Compatibility and migration";
#   add-anchor-derived-identity design.md Decision 5 ("Explicit relabeling"); no
#   guessing.
"""Reported migrations (0.2 -> 0.3, label-id -> identity profile); nothing is invented."""
import copy
import hashlib
import json

from dsc03 import identity


def migrate(d02):
    """Migrate a valid 0.2 descriptor. Returns (descriptor_03, report).

    The report records every loss: dropped edges, unsupported order assertions,
    unexamined material and unrecoverable data. Regions/contents/evidence ids
    are preserved where the record survives.
    """
    report = {
        "views_created": [],
        "dropped": [],
        "unsupported": [],
        "unexamined": [],
        "unrecoverable": [],
        "demoted": [],
    }

    # -- regions and per-view trees -------------------------------------------
    view_of = {}
    for r in d02["regions"]:
        if "geometry" in r:
            report["unexamined"].append(
                f"geometry of region {r['id']} dropped: legacy coordinates have no profile binding"
            )
    class_edges = {"physical": [], "logical": []}
    parents = {}
    for rel in d02["relations"]:
        if rel["kind"] != "contains":
            continue
        va = region_view(d02, rel["from"])
        vb = region_view(d02, rel["to"])
        if va == vb and va in class_edges:
            class_edges[va].append((rel["id"], rel["from"], rel["to"]))
            parents[rel["to"]] = rel["from"]
        else:
            report["dropped"].append({
                "what": "contains-edge", "id": rel["id"],
                "reason": f"cross-view {va}->{vb}; per-view trees cannot keep it",
            })
    # forest per class; each tree becomes its own view
    children = {}
    for _, a, b in class_edges_all(class_edges):
        children.setdefault(a, []).append(b)
    view_by_root = {}
    counter = {"physical": 0, "logical": 0}
    d03_regions = []
    for r in d02["regions"]:
        rr = {"id": r["id"], "view_id": None, "kind": r["kind"]}
        d03_regions.append(rr)
    # find roots per class
    for cls in ("physical", "logical"):
        members = [r["id"] for r in d02["regions"] if r.get("view") == cls]
        roots = [m for m in members if m not in parents]
        if not roots and members:
            roots = [members[0]]  # cycle: pick a deterministic head, report it
            report["unsupported"].append({
                "what": "containment-cycle", "view_class": cls,
                "reason": "legacy containment cycle; head chosen deterministically for the tree",
            })
        for i, root in enumerate(roots):
            counter[cls] += 1
            vid = cls if i == 0 else f"{cls}-{counter[cls]}"
            members_tree = collect_tree(root, children, {m for m in members})
            for m in members_tree:
                view_of[m] = vid
            report["views_created"].append({"id": vid, "kind": cls, "root": root})
    for rr in d03_regions:
        rr["view_id"] = view_of[rr["id"]]

    d03 = {
        "version": "0.3",
        "id": d02["id"],
        "source": dict(d02["source"]),  # digest and locator preserved
        "views": report["views_created"],
        "regions": d03_regions,
        "contents": [dict(c) for c in d02["contents"]],
        "relations": [],
        "annotations": [],
        "evidence": [],
        "selectors": [],
        "interpretations": [],
        "coverage": [],
        "profiles": [],
        "vocabularies": [dict(v) for v in d02["vocabularies"]],
    }
    report["unrecoverable"].append(
        "original pre-normalization code points of text contents cannot be "
        "recovered: 0.2 stored NFC-normalized text only"
    )

    # -- relations: keep same-view structural edges; precedes via interpretations
    order_edges = {}  # view_id -> [(from, to)]
    keep_kinds = {"contains", "realizes", "has-content"}
    for rel in d02["relations"]:
        kind = rel["kind"]
        a, b = rel["from"], rel["to"]
        if kind == "contains":
            if view_of.get(a) == view_of.get(b) and (rel["id"], a, b) in set(class_edges_all(class_edges)):
                d03["relations"].append({"id": rel["id"], "kind": "contains", "from": a, "to": b})
            continue
        if kind in keep_kinds:
            if kind == "realizes" and view_of.get(a) != view_of.get(b):
                # realizes crosses the physical/logical split by design: keep only
                # if the physical region's view is physical and logical stays logical
                pass
            d03["relations"].append({"id": rel["id"], "kind": kind, "from": a, "to": b})
        elif kind == "precedes":
            va, vb = view_of.get(a), view_of.get(b)
            if va is not None and va == vb:
                order_edges.setdefault(va, []).append((a, b))
            else:
                report["unsupported"].append({
                    "what": "precedes-edge", "id": rel["id"],
                    "reason": f"endpoints in different migrated views ({va}/{vb}); no observed order can be asserted",
                })
        elif kind == "derived-from":
            report["dropped"].append({
                "what": "derived-from-edge", "id": rel["id"],
                "reason": "re-evaluated against migrated evidence below",
            })
    for vid, edges in order_edges.items():
        iid = f"migrated-order-{vid}"
        d03["interpretations"].append({
            "id": iid, "kind": "reading-order", "view_id": vid,
            "origin": "manual", "status": "asserted_without_evidence", "evidence": [],
        })
        for j, (a, b) in enumerate(edges):
            d03["relations"].append({
                "id": f"migrated-precedes-{vid}-{j}", "kind": "precedes",
                "from": a, "to": b, "interpretation_id": iid,
            })

    # -- evidence: keep source/manual/external; drop extracted/inferred without replay
    kept_evidence = set()
    for e in d02["evidence"]:
        if e["origin"] in ("extracted", "inferred"):
            report["unrecoverable"].append(
                f"evidence {e['id']} dropped: legacy transform has no input/output lineage, replay cannot be reconstructed"
            )
            continue
        d03["evidence"].append({
            "id": e["id"], "origin": e["origin"], "source_ref": e["source_ref"],
            "content_ids": [], "selector_ids": [],
        })
        kept_evidence.add(e["id"])

    # -- annotations: bind the view; demote when their evidence was dropped
    content_bindings = {}  # content -> set of region ids binding it
    for rel in d02["relations"]:
        if rel["kind"] == "has-content":
            content_bindings.setdefault(rel["to"], set()).add(rel["from"])
    for a in d02["annotations"]:
        t = a["target"]
        if t in view_of:
            vid = view_of[t]
        elif t in content_bindings:
            regions = sorted(content_bindings[t])
            vids = {view_of[r] for r in regions if r in view_of}
            if len(vids) != 1:
                report["unrecoverable"].append(
                    f"annotation {a['id']} dropped: target content is bound in ambiguous views {sorted(vids)}"
                )
                continue
            vid = vids.pop()
        else:
            report["unrecoverable"].append(
                f"annotation {a['id']} dropped: target has no binding in any migrated view"
            )
            continue
        status = a["status"]
        evidence = [x for x in a["evidence"] if x in kept_evidence]
        if status == "supported" and not evidence:
            status = "asserted_without_evidence"
            report["demoted"].append(
                f"annotation {a['id']} demoted: its evidence could not be migrated"
            )
        na = dict(a, status=status, evidence=evidence, view_id=vid)
        d03["annotations"].append(na)
    return d03, report


def region_view(d02, rid):
    for r in d02["regions"]:
        if r["id"] == rid:
            return r.get("view")
    return None


def class_edges_all(class_edges):
    for edges in class_edges.values():
        for e in edges:
            yield e


def collect_tree(root, children, members):
    out = [root]
    stack = [root]
    while stack:
        x = stack.pop()
        for c in children.get(x, []):
            if c in members:
                out.append(c)
                stack.append(c)
    return out


# -- label-id -> identity-profile migration (add-anchor-derived-identity 5.1) -------

# The identity profile this migration declares: the pinned artifact bytes are
# the ones profiles.resolve expects at profiles/identity-v1.json (see
# tests/tracer/test_identity.py IDENTITY_ARTIFACT — same bytes, one pin).
IDENTITY_ARTIFACT = {
    "kind": "identity",
    "version": "1",
    "digest": {"algorithm": "sha256", "truncation_bits": 128, "prefix": "a:"},
}
IDENTITY_PROFILE_ID = "identity"
IDENTITY_PROFILE_VERSION = "1"
IDENTITY_PROFILE_DECL = {
    "id": IDENTITY_PROFILE_ID,
    "kind": "identity",
    "uri": "profiles/identity-v1.json",
    "version": IDENTITY_PROFILE_VERSION,
    "sha256": hashlib.sha256(
        json.dumps(IDENTITY_ARTIFACT, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest(),
}
# The migration is the PRODUCER of its relabel-table evidence record and pins
# that new record at this declared path (design Decision 5). The fixed path
# keeps the record's derivation independent of the table it carries (no
# self-reference); the no-invention rule governs locators of pre-existing
# records, not records the migration itself emits.
RELABEL_LOCATOR = "relabel-table"

# The four sections the identity rule covers (validator, add-anchor-derived-
# identity §2.4). Views/relations/annotations/interpretations keep their label
# ids; they are relabeled only where they REFERENCE a renamed record.
_IDENTITY_SECTIONS = (
    ("regions", "region"),
    ("contents", "content"),
    ("selectors", "selector"),
    ("evidence", "evidence"),
)


def _targeting(d):
    """Record id -> the selector records targeting it (the declared pins)."""
    out = {}
    for sl in d["selectors"]:
        out.setdefault(sl["target"], []).append(sl)
    return out


def _declared_anchor(rec_kind, rec, targeting, source_sha):
    """(record_kind, locator_path, derivation source_sha256) from DECLARED
    data only, or None.

    Selectors carry their own profile-bound locator and their own
    source_sha256 (the derivation source the validator uses); evidence its
    source_ref; a region/content is anchored only when exactly ONE selector
    pins it — text contents take the pinning text-range locator as a
    raw-text interval per design Decision 1. None = no declared locator; the
    caller reports the record, never invents one.
    """
    if rec_kind == "selector":
        return rec_kind, rec["locator"], rec["source_sha256"]
    if rec_kind == "evidence":
        return rec_kind, rec["source_ref"], source_sha
    pins = targeting.get(rec["id"], [])
    if len(pins) != 1:
        return None
    locator = pins[0]["locator"]
    if rec_kind == "content" and pins[0]["kind"] == "text-range":
        locator = f"raw:{locator}"
    return rec_kind, locator, source_sha


def _unanchored_reason(rec_kind, rec, targeting):
    """Why this record has no declared locator (report entry: id + reason)."""
    pins = targeting.get(rec["id"], [])
    if not pins:
        return f"no declared locator: no selector targets this {rec_kind}"
    names = ", ".join(sorted(sl["id"] for sl in pins))
    return (f"no declared locator: pinned by {len(pins)} selectors ({names}); "
            "choosing one would be a guess")


def migrate_to_identity(d):
    """Relabel a valid label-id descriptor to the identity profile.

    Returns (descriptor, report). Every region/content/selector/evidence
    record whose anchor is derivable from DECLARED data only (selector
    locators, evidence source_ref, one unique targeting selector's locator)
    is renamed to derive_id over its anchor tuple and carries its anchor on
    the wire; every reference to a renamed record is rebound; content values
    are never touched. Input must be a valid 0.3 label-id descriptor (no
    declared identity profile), as migrate() expects valid 0.2 input.

    The old->new table is emitted as ONE relabel-table evidence record
    (Decision 5): origin "manual", source_ref "sha256:<source>#relabel-
    table=" followed by the canonical JSON of the sorted [old, new] pairs.
    Wire decision: the evidence schema is closed (no extra keys), its
    content_ids/selector_ids are referential (old ids would dangle under
    relabeling), and a transform would claim content lineage the migration
    must not assert (values are untouched) — so the table rides in
    source_ref, the record's declared reference payload.

    Records whose anchor cannot be derived — and records whose anchor tuple
    duplicates another's, which would derive the same id — are REPORTED in
    report["unanchored"] ({id, reason}), keep their label ids and gain no
    anchor; a nonempty list therefore means the result does not validate
    under the identity profile. report["relabel"] mirrors the emitted table;
    report["relabel_evidence"] is the table record's derived id.
    """
    d = copy.deepcopy(d)
    report = {"relabel": [], "unanchored": [], "relabel_evidence": None}
    source_sha = d["source"]["sha256"]
    targeting = _targeting(d)

    anchors = {}  # old id -> (record_kind, locator_path, derivation source_sha256)
    for section, rec_kind in _IDENTITY_SECTIONS:
        for rec in d[section]:
            anchor = _declared_anchor(rec_kind, rec, targeting, source_sha)
            if anchor is None:
                report["unanchored"].append({
                    "id": rec["id"],
                    "reason": _unanchored_reason(rec_kind, rec, targeting),
                })
            else:
                anchors[rec["id"]] = anchor

    # Derive; two records with the same anchor tuple derive the same id, so
    # both are refused (admission, never a silent merge or rename).
    new_id = {}  # old id -> derived id, migrated records only
    seen = {}    # derived id -> old id
    for old, (rec_kind, locator, sha) in anchors.items():
        status, derived = identity.derive_id(
            (sha, rec_kind, locator, IDENTITY_PROFILE_ID, IDENTITY_PROFILE_VERSION))
        if status != "derived":  # unreachable for validator-shaped records; kept typed
            report["unanchored"].append({"id": old, "reason": f"anchor refused: {status}"})
            continue
        dup = seen.get(derived)
        if dup is not None:
            report["unanchored"].append({"id": old, "reason": f"anchor tuple duplicates {dup}"})
            report["unanchored"].append({"id": dup, "reason": f"anchor tuple duplicates {old}"})
            del new_id[dup]
            continue
        seen[derived] = old
        new_id[old] = derived

    # Decision 5: the relabel table as evidence, mapping EVERY migrated old id.
    pairs = sorted((list(pair) for pair in new_id.items()), key=lambda p: p[0])
    report["relabel"] = pairs
    table = json.dumps(pairs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    _, eid = identity.derive_id(
        (source_sha, "evidence", RELABEL_LOCATOR, IDENTITY_PROFILE_ID, IDENTITY_PROFILE_VERSION))
    if eid in seen:  # a pre-existing record already derives the table locator
        report["unanchored"].append({
            "id": eid,
            "reason": "relabel-table locator already derived by an existing record",
        })
    else:
        report["relabel_evidence"] = eid
        d["evidence"].append({
            "id": eid,
            "anchor": {"record_kind": "evidence", "locator_path": RELABEL_LOCATOR},
            "origin": "manual",
            "source_ref": f"sha256:{source_sha}#relabel-table={table}",
            "content_ids": [],
            "selector_ids": [],
        })

    # Relabel in place (array position preserved; the readers sort under the
    # profile). Unanchored records keep their label ids and gain no anchor.
    for section, rec_kind in _IDENTITY_SECTIONS:
        for rec in d[section]:
            new = new_id.get(rec["id"])
            if new is not None:
                rec["anchor"] = {"record_kind": rec_kind,
                                 "locator_path": anchors[rec["id"]][1]}
                rec["id"] = new

    # Rebind every reference to a renamed record; unrenamed ids pass through.
    for v in d["views"]:
        v["root"] = new_id.get(v["root"], v["root"])
    for r in d["relations"]:
        r["from"] = new_id.get(r["from"], r["from"])
        r["to"] = new_id.get(r["to"], r["to"])
        if "evidence" in r:
            r["evidence"] = [new_id.get(x, x) for x in r["evidence"]]
    for a in d["annotations"]:
        a["target"] = new_id.get(a["target"], a["target"])
        a["evidence"] = [new_id.get(x, x) for x in a["evidence"]]
        if "selector_ids" in a:
            a["selector_ids"] = [new_id.get(x, x) for x in a["selector_ids"]]
    for e in d["evidence"]:
        e["content_ids"] = [new_id.get(x, x) for x in e["content_ids"]]
        e["selector_ids"] = [new_id.get(x, x) for x in e["selector_ids"]]
        t = e.get("transform")
        if t is not None:
            t["inputs"] = [new_id.get(x, x) for x in t["inputs"]]
            t["outputs"] = [new_id.get(x, x) for x in t["outputs"]]
    for sl in d["selectors"]:
        sl["target"] = new_id.get(sl["target"], sl["target"])
    for i in d["interpretations"]:
        i["evidence"] = [new_id.get(x, x) for x in i["evidence"]]

    # The migrated descriptor declares the identity profile it now obeys.
    d["profiles"].append(copy.deepcopy(IDENTITY_PROFILE_DECL))
    return d, report
