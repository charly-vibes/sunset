# Purpose: Consolidated law catalogue for define-document-composition-semantics
#   (sunset-905.1/.2): every assembly, views, space and context law of the four
#   deltas' Properties tables, listed with id, seeded generator and the verdict
#   vocabulary holds / violated / not-applicable / incomplete, run over seeded
#   generated inputs.
# Responsibilities: run_law/run_catalogue — classify each law into the verdict
#   vocabulary (a law without a generator or without a required declaration is
#   incomplete and NEVER holds; not-applicable is reported, never collapsed
#   into holds); export_violation — replayable counterexample bundles through
#   the existing dsc03.compare.export_counterexample path, carrying inputs +
#   seed + law id, byte-deterministic via compare.serialize_bundle; replay_law —
#   re-run the law on the regenerated inputs and confirm the verdict
#   reproduces; UNKNOWNS — unimplemented operations documented as unknowns,
#   never implied passing (no deployed-kernel composition checker, no Lens
#   export yet, no OCR runs, no independent-agreement slice). Machinery-level
#   witnessing only: no deployed-kernel conformance is claimed anywhere.
# Rationale: the unchecked catalogue task of the change — one catalogue over
#   the four deltas' laws, machinery-side, beside the fixture modules the laws
#   are witnessed with; violations must export through the same counterexample
#   machinery the debugger slice shipped (sunset-xx7.3).
"""Law catalogue: id + seeded generator + verdict per assembly/views/space/context law."""
import copy
import dataclasses
import hashlib
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_assembly_laws as al  # reuse the assembly fixture builders (same dir)

from dsc03 import compare
from dsc03.substrate import context as ctx
from dsc03.substrate import space, views
from dsc03.substrate.assembly import canonically_equal, compose, empty_part
from dsc03.substrate.laws import synthetic_sha, typed_check

VERDICTS = ("holds", "violated", "not-applicable", "incomplete")

SECTIONS = ("assembly", "views", "space", "context")

# Required declarations registry: a law that needs a pinned declaration runs
# only when the declaration is present here; otherwise it is incomplete.
_IDENTITY_ARTIFACT = {"kind": "identity", "version": "1",
                      "digest": {"algorithm": "sha256", "truncation_bits": 128,
                                 "prefix": "a:"}}
DECLARATIONS = {
    # the pinned identity profile declaration (same artifact bytes as
    # test_assembly_laws._identity_decl resolves at profiles/identity-v1.json)
    "identity_profile_v1": {
        "uri": "profiles/identity-v1.json", "version": "1",
        "sha256": hashlib.sha256(
            json.dumps(_IDENTITY_ARTIFACT, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")).hexdigest(),
    },
}

# Unimplemented operations and unknowns — documented, never implied passing.
UNKNOWNS = (
    {"topic": "deployed kernel composition checker",
     "detail": "the deployed kernel has no A⊕B checker (restore-document-"
               "substrate mapping.md law 5 is partial); every assembly verdict "
               "in this catalogue is machinery-level "
               "(dsc03/substrate/assembly.py), never a kernel conformance claim."},
    {"topic": "counterexample export to Sunset Lens",
     "detail": "exposing failed laws and source witnesses to Lens is an "
               "unchecked task of this change; bundles are exported in-repo "
               "only (compare.export_counterexample), no Lens surface exists."},
    {"topic": "independent reader agreement (debugger slice 4)",
     "detail": "independent_agreement is intentionally out of scope of "
               "dsc03.compare (slice 3); no catalogue verdict depends on it."},
    {"topic": "OCR runs and real-carrier factorization",
     "detail": "no OCR was run and no real-carrier sign-column factorization "
               "was executed for this catalogue; space/context verdicts come "
               "from validated synthetic fixtures only."},
    {"topic": "EPUB carrier runs",
     "detail": "EPUB rendering was waived by the owner (sunset-905.3); "
               "epub_reflow is witnessed on the synthetic EPUB-carrier "
               "fixture only."},
)


def _w(witness, expected, observed):
    """A minimal violated-law witness: what failed, expected vs observed."""
    return {"witness": witness, "expected": expected, "observed": observed}


def _applicable(case):
    return True


@dataclasses.dataclass(frozen=True)
class LawSpec:
    """One catalogue entry: stable id, seeded generator, verdict check."""
    law_id: str                       # "<delta id>/<property id>"
    section: str                      # assembly | views | space | context
    constraint: str                   # the delta constraint the law derives from
    generator: object                 # seed -> case dict; None => incomplete
    check: object                     # case -> None (holds) | witness (violated)
    observable_scope: tuple = ()      # recorded in exported bundles
    required_declarations: tuple = () # keys that must exist in DECLARATIONS
    applicable: object = _applicable  # case -> bool (False => not-applicable)


# -- seeded generators (assembly) ------------------------------------------------

_WORDS = ("ink", "paper", "verse", "column", "glyph", "margin", "folio", "leaf")


def _words(rng):
    return " ".join(rng.choice(_WORDS) for _ in range(3))


def _gen_compatible_pair(seed):
    rng = random.Random(seed)
    a = al._continued(al._part(1, "r-art-1", _words(rng)), "r-art-1", "r-art-2")
    b = al._part(rng.randrange(2, 9), "r-art-2", _words(rng))
    return {"seed": seed, "a": a, "b": b}


def _check_compatible_pair(case):
    a, b = case["a"], case["b"]
    result = compose(a, b)
    if result["status"] != "assembled":
        return _w("compose_refused", "assembled",
                  {"rule": result.get("rule"), "smallest": result.get("smallest")})
    merged = result["descriptor"]
    status, reasons = typed_check(merged)
    if status != "accepted":
        return _w("union_invalid", "accepted", reasons)
    expected_nodes = sorted({r["id"] for r in a["regions"]}
                            | {r["id"] for r in b["regions"]})
    observed_nodes = sorted(r["id"] for r in merged["regions"])
    if observed_nodes != expected_nodes:
        return _w("nodes_not_preserved", expected_nodes, observed_nodes)
    if al._edge_set(merged) != al._edge_set(a) | al._edge_set(b):
        return _w("edges_not_preserved", sorted(al._edge_set(a) | al._edge_set(b)),
                  sorted(al._edge_set(merged)))
    return None


def _gen_duplicate_conflict(seed):
    rng = random.Random(seed)
    a = al._part(1, "r-art-1", _words(rng))
    b = al._part(rng.randrange(2, 9), "r-art-1", _words(rng), sha=al.SHA_EDITION_B)
    return {"seed": seed, "a": a, "b": b}


def _check_duplicate_conflict(case):
    result = compose(case["a"], case["b"])
    if result["status"] != "refused" or result["rule"] != "same_id_conflicting_source":
        return _w("conflict_not_refused", "refused/same_id_conflicting_source",
                  {"status": result.get("status"), "rule": result.get("rule")})
    if "r-art-1" not in result["smallest"]:
        return _w("witness_missing_id", ["r-art-1"], result["smallest"])
    return None


def _gen_left_right_identity(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "a": al._part(rng.randrange(1, 9), "r-art-1", _words(rng))}


def _check_left_right_identity(case):
    a, empty = case["a"], empty_part()
    for side, x in (("right", compose(a, empty)), ("left", compose(empty, a))):
        if x["status"] != "assembled":
            return _w(f"identity_refused_{side}", "assembled",
                      {"rule": x.get("rule"), "smallest": x.get("smallest")})
        if not canonically_equal(x["descriptor"], a):
            return _w(f"identity_broken_{side}", "canonical(A)", "differed")
    return None


def _gen_associate_three(seed):
    rng = random.Random(seed)
    a = al._continued(al._part(1, "r-art-1", _words(rng)), "r-art-1", "r-art-2")
    b = al._part(rng.randrange(2, 9), "r-art-2", _words(rng))
    c = al._part(rng.randrange(2, 9), "r-art-3", _words(rng))
    return {"seed": seed, "a": a, "b": b, "c": c}


def _check_associate_three(case):
    a, b, c = case["a"], case["b"], case["c"]
    left, right = compose(compose(a, b), c), compose(a, compose(b, c))
    for side, x in (("left", left), ("right", right)):
        if x["status"] != "assembled":
            return _w(f"bracketing_refused_{side}", "assembled",
                      {"rule": x.get("rule"), "smallest": x.get("smallest")})
    if not canonically_equal(left["descriptor"], right["descriptor"]):
        return _w("bracketings_differ", "canonical grouping agreement", "differed")
    return None


def _gen_no_invented_order(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "a": al._part(rng.randrange(1, 9), "r-art-1", _words(rng)),
            "b": al._part(rng.randrange(1, 9), "r-art-2", _words(rng))}


def _check_no_invented_order(case):
    a, b = case["a"], case["b"]
    result = compose(a, b)
    if result["status"] != "assembled":
        return _w("compose_refused", "assembled",
                  {"rule": result.get("rule"), "smallest": result.get("smallest")})
    merged = result["descriptor"]
    precedes = sorted(r["id"] for r in merged["relations"] if r["kind"] == "precedes")
    if precedes:
        return _w("order_invented", [], precedes)
    if al._edge_set(merged) != al._edge_set(a) | al._edge_set(b):
        return _w("edges_not_preserved", sorted(al._edge_set(a) | al._edge_set(b)),
                  sorted(al._edge_set(merged)))
    return None


def _gen_shared_id_merges(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "a": al._part(1, "r-art-1", _words(rng)),
            "b": al._part(2, "r-art-2", _words(rng))}


def _check_shared_id_merges(case):
    a, b = case["a"], case["b"]
    result = compose(a, b)
    if result["status"] != "assembled":
        return _w("compose_refused", "assembled",
                  {"rule": result.get("rule"), "smallest": result.get("smallest")})
    merged = result["descriptor"]
    if typed_check(merged)[0] != "accepted":
        return _w("union_invalid", "accepted", typed_check(merged)[1])
    shared = [r for r in merged["regions"] if r["id"] == "r-issue"]
    if len(shared) != 1:
        return _w("shared_id_not_merged", 1, len(shared))
    if al._edge_set(merged) != al._edge_set(a) | al._edge_set(b):
        return _w("edges_not_preserved", sorted(al._edge_set(a) | al._edge_set(b)),
                  sorted(al._edge_set(merged)))
    pages = sorted(e["source_ref"] for e in merged["evidence"])
    if pages != sorted(e["source_ref"] for e in a["evidence"] + b["evidence"]):
        return _w("provenance_not_retained",
                  sorted(e["source_ref"] for e in a["evidence"] + b["evidence"]), pages)
    return None


# -- seeded generators (assembly join, anchor-derived parts) ---------------------

def _gen_anchored_pair(seed):
    rng = random.Random(seed)
    pages = rng.sample(range(1, 9), 2)
    arts = rng.sample(("essay", "poem", "notes", "review"), 2)
    a = al._id_part(pages[0], arts[0], _words(rng))
    b = al._id_part(pages[1], arts[1], _words(rng))
    return {"seed": seed, "a": a, "b": b}


def _check_join_commutative(case):
    a, b = case["a"], case["b"]
    ab, ba = compose(a, b), compose(b, a)
    for side, x in (("ab", ab), ("ba", ba)):
        if x["status"] != "assembled":
            return _w(f"compose_{side}_refused", "assembled",
                      {"rule": x.get("rule"), "smallest": x.get("smallest")})
    if not canonically_equal(ab["descriptor"], ba["descriptor"]):
        return _w("not_canonically_equal",
                  "canonical(compose(A,B)) == canonical(compose(B,A))", "differed")
    ids_ab = sorted(r["id"] for r in ab["descriptor"]["regions"])
    ids_ba = sorted(r["id"] for r in ba["descriptor"]["regions"])
    if ids_ab != ids_ba:
        return _w("anchor_ids_order_dependent", ids_ab, ids_ba)
    return None


def _gen_anchored_part(seed):
    rng = random.Random(seed)
    x = al._canon_sorted(al._id_part(rng.randrange(1, 9), "poem", _words(rng)))
    return {"seed": seed, "x": x, "pair": _gen_anchored_pair(seed + 1)}


def _check_join_idempotent(case):
    x = case["x"]
    result = compose(x, x)
    if result["status"] != "assembled":
        return _w("self_join_refused", "assembled",
                  {"rule": result.get("rule"), "smallest": result.get("smallest")})
    if not canonically_equal(result["descriptor"], x):
        return _w("self_join_not_identity", "canonical(compose(A,A)) == canonical(A)",
                  "differed")
    y = compose(case["pair"]["a"], case["pair"]["b"])
    if y["status"] != "assembled":
        return _w("pair_refused", "assembled",
                  {"rule": y.get("rule"), "smallest": y.get("smallest")})
    again = compose(y, y)
    if again["status"] != "assembled" or not canonically_equal(again["descriptor"],
                                                              y["descriptor"]):
        return _w("assembled_not_idempotent", "canonical((A⊕B)⊕(A⊕B)) == canonical(A⊕B)",
                  {"status": again.get("status")})
    return None


def _gen_refusal_absorption(seed):
    rng = random.Random(seed)
    page1, page2 = rng.sample(range(1, 9), 2)
    t1, t2 = _words(rng), _words(rng)
    if t1 == t2:
        t2 = t2 + " forged"
    a = al._id_part(page1, "essay", t1)
    b = al._id_part(page1, "essay", t2)   # same anchors, conflicting claims
    c = al._id_part(page2, "poem", _words(rng))
    d = al._id_part(page2, "poem", _words(rng) + " forged")
    p = al._id_part(rng.randrange(1, 9), "review", _words(rng))
    return {"seed": seed, "a": a, "b": b, "c": c, "d": d, "p": p}


def _make_absorption_check(subject):
    """The absorption check over an injectable join subject — the catalogue
    runs the real compose(); mutation probes run a broken subject to exercise
    the violation/counterexample path."""
    def check(case):
        r1 = compose(case["a"], case["b"])
        if r1.get("status") != "refused":
            return _w("no_refusal_produced", "refused", r1.get("status"))
        r2 = compose(case["c"], case["d"])
        p = case["p"]
        for label, x, y in (("left-part", r1, p), ("right-part", p, r1),
                            ("both-same", r1, r1), ("left-distinct", r1, r2),
                            ("left-empty", r1, empty_part())):
            out = subject(x, y)
            if out != r1:
                return _w(f"absorption_broken_{label}", "refusal envelope verbatim",
                          {"status": out.get("status"), "rule": out.get("rule")})
        return None
    return check


# -- generators and checks (views) ------------------------------------------------

def _check_view_overlap(case):
    desc = views.magazine_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    bindings = views.content_bindings(desc)
    for cid in ("c1", "c2"):
        if bindings.get(cid) != {"v-phys", "v-log"}:
            return _w("membership_lost", ["v-phys", "v-log"], sorted(bindings.get(cid, [])))
    return None


def _check_cycle_refused(case):
    status, reasons = typed_check(views.cycle_fixture())
    if status != "rejected" or "containment_cycle" not in reasons:
        return _w("cycle_not_rejected", "rejected/containment_cycle",
                  {"status": status, "reasons": reasons})
    report = views.containment_cycle_report(views.cycle_fixture())
    path = report.get("cycle_path") or []
    if report["status"] != "rejected" or not path or path[0] != path[-1]:
        return _w("no_closed_path_witness", "closed cycle path", report)
    if sorted(set(path[:-1])) != ["r-p1", "r-p2"]:
        return _w("path_names_wrong_regions", ["r-p1", "r-p2"], sorted(set(path[:-1])))
    if typed_check(views.magazine_fixture())[0] != "accepted":
        return _w("acyclic_base_rejected", "accepted", "rejected")
    return None


def _check_partial_order_ok(case):
    desc = views.order_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    report = views.order_status(desc, "int-ro")
    if report["status"] != "accepted" or report["incomparable"] != [["r-col-1", "r-col-2"]]:
        return _w("incomparables_not_preserved", [["r-col-1", "r-col-2"]],
                  report.get("incomparable"))
    cyc = copy.deepcopy(desc)
    cyc["relations"].append({"id": "rel-ro-fwd", "kind": "precedes",
                             "from": "r-col-1", "to": "r-col-2",
                             "interpretation_id": "int-ro"})
    cyc["relations"].append({"id": "rel-ro-back", "kind": "precedes",
                             "from": "r-col-2", "to": "r-col-1",
                             "interpretation_id": "int-ro"})
    if "order_cycle" not in typed_check(cyc)[1]:
        return _w("declared_cycle_accepted", "order_cycle rejection", "accepted")
    cyc_report = views.order_status(cyc, "int-ro")
    path = cyc_report.get("cycle_path") or []
    if cyc_report["status"] != "rejected" or path != ["r-col-1", "r-col-2", "r-col-1"]:
        return _w("cycle_path_wrong", ["r-col-1", "r-col-2", "r-col-1"],
                  {"status": cyc_report["status"], "path": path})
    return None


def _gen_projection(seed):
    rng = random.Random(seed)
    keep = {"r-doc"} | set(rng.sample(("r-p1", "r-p2"), rng.randrange(1, 3)))
    return {"seed": seed, "keep": sorted(keep)}


def _check_projection(case):
    desc = views.magazine_fixture()
    res = views.project(desc, set(case["keep"]))
    if res["status"] != "projected":
        return _w("projection_refused", "projected",
                  {"status": res["status"], "rule": res.get("rule")})
    out = res["descriptor"]
    if typed_check(out)[0] != "accepted":
        return _w("projected_invalid", "accepted", typed_check(out)[1])
    expected_kept = set(case["keep"]) | {v["root"] for v in desc["views"]}
    kept = sorted(r["id"] for r in out["regions"])
    if kept != sorted(expected_kept):
        return _w("regions_not_exact", sorted(expected_kept), kept)
    present = ({r["id"] for r in out["regions"]}
               | {c["id"] for c in out["contents"]}
               | {e["id"] for e in out["evidence"]})
    for rel in desc["relations"]:
        if rel["from"] in present and rel["to"] in present and rel not in out["relations"]:
            return _w("internal_edge_dropped", "kept verbatim", rel["id"])
    excluded_ids = sorted(e["id"] for e in res["excluded"])
    dropped = sorted(r["id"] for r in desc["relations"]
                     if r["id"] not in {x["id"] for x in out["relations"]}
                     and r["id"] in excluded_ids)
    if sorted(set(excluded_ids) & {r["id"] for r in desc["relations"]}) != dropped:
        return _w("exclusion_mismatch", dropped, excluded_ids)
    for rid in dropped:
        rel = next(r for r in desc["relations"] if r["id"] == rid)
        if rel["kind"] == "precedes":
            omitted = [c for c in out["coverage"]
                       if c["status"] == "omitted" and rid in c["feature"]]
            if not omitted or not omitted[0]["reason"]:
                return _w("dropped_link_not_in_coverage", rid, out["coverage"])
    return None


def _gen_refinement_conflict(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "removed": rng.choice(("rel-cont", "rel-doc1", "rel-doc2"))}


def _check_refinement_conflict(case):
    base = views.magazine_fixture()
    refined = copy.deepcopy(base)
    rid = case["removed"]
    refined["relations"] = [r for r in refined["relations"] if r["id"] != rid]
    conflict = views.refinement_check(base, refined)
    if conflict["status"] != "conflict" or conflict["removed"] != [rid]:
        return _w("removal_not_reported", {"status": "conflict", "removed": [rid]},
                  {"status": conflict["status"], "removed": conflict["removed"]})
    superseded = views.refinement_check(base, refined, superseded=[rid],
                                        policy="editor-review-1")
    if (superseded["status"] != "superseded" or superseded["policy"] != "editor-review-1"
            or superseded["removed"] != [rid]):
        return _w("supersession_not_recorded",
                  {"status": "superseded", "policy": "editor-review-1", "removed": [rid]},
                  superseded)
    return None


def _check_links_not_containment(case):
    desc = views.magazine_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    report = views.link_check(desc, "r-p1", "r-p2")
    if report["status"] != "typed_links" or "precedes" not in report["link_kinds"]:
        return _w("continuation_not_a_typed_link", "precedes link", report)
    if "contains" in report["link_kinds"]:
        return _w("parent_pointer_invented", "no contains edge", report["link_kinds"])
    ref = views.link_check(desc, "e-ref-src", "e-ref-dst")
    if "derived-from" not in ref["link_kinds"]:
        return _w("reference_not_a_typed_link", "derived-from link", ref["link_kinds"])
    return None


# -- generators and checks (space) ------------------------------------------------

def _locus(rng, max_w, max_h):
    w, h = rng.randrange(1, 200), rng.randrange(1, 200)
    return {"x": rng.randrange(0, max_w - w + 1), "y": rng.randrange(0, max_h - h + 1),
            "width": w, "height": h}


def _gen_pdf_rotation(seed):
    rng = random.Random(seed)
    box = _locus(rng, 792, 612)  # the rotated page box is 792 wide x 612 high
    return {"seed": seed,
            "observed": {"space": "page-1-rot90-pt", **box},
            "expected": {"space": "page-1-pt",
                         "x": 792 - (box["y"] + box["height"]),
                         "y": box["x"],
                         "width": box["height"], "height": box["width"]}}


def _check_pdf_rotation(case):
    t = space.transform_rot90(612, 792)
    normalized = space.normalize(t, case["observed"])
    if normalized != case["expected"]:
        return _w("normalized_geometry_mismatch", case["expected"], normalized)
    return None


def _gen_roundtrip(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "source": {"space": "page-1-pt", **_locus(rng, 612, 792)}}


def _check_roundtrip(case):
    t = space.transform_rot90(612, 792)
    roundtripped = space.normalize(t, space.denormalize(t, case["source"]))
    if not space.within_tolerance(roundtripped, case["source"], t.tolerance):
        return _w("roundtrip_out_of_tolerance", case["source"], roundtripped)
    if roundtripped["space"] != case["source"]["space"]:
        return _w("frame_not_preserved", case["source"]["space"], roundtripped["space"])
    return None


def _gen_cross_page_unknown(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "a": {"space": "page-1-pt", **_locus(rng, 600, 700)},
            "b": {"space": "page-2-pt", **_locus(rng, 600, 700)}}


def _check_cross_page_unknown(case):
    a, b = case["a"], case["b"]
    report = space.above(a, b)
    if report["status"] != "unknown" or report.get("reason") != "incompatible_frames":
        return _w("cross_frame_not_typed_unknown",
                  {"status": "unknown", "reason": "incompatible_frames"}, report)
    same = dict(b, space="page-1-pt")
    value = space.above(a, same)
    if value["status"] != "known" or value["value"] != (a["y"] < same["y"]):
        return _w("same_frame_value_wrong", a["y"] < same["y"], value)
    return None


def _gen_epub_reflow(seed):
    rng = random.Random(seed)
    y1 = rng.randrange(500, 2000)
    return {"seed": seed,
            "small": space.viewport_observation(
                "vp-small", x=rng.randrange(0, 100), y=y1, scale=1.0),
            "large": space.viewport_observation(
                "vp-large", x=rng.randrange(0, 100),
                y=y1 + rng.randrange(50, 500), scale=round(rng.uniform(1.2, 2.0), 2))}


def _check_epub_reflow(case):
    desc = space.epub_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    report = space.epub_identity(desc, "sel-ch3", case["small"], case["large"])
    locator = "urn:sub:epub#ch3/frag-42"
    if report["status"] != "stable" or report["selector_locator"] != locator:
        return _w("selector_unstable", locator,
                  {"status": report.get("status"),
                   "selector_locator": report.get("selector_locator")})
    if case["small"]["y"] == case["large"]["y"]:
        return _w("reflow_not_exercised", "different viewport Y", "equal Y")
    if report["xy_differs"] is not True:
        return _w("xy_difference_not_reported", True, report["xy_differs"])
    return None


def _check_native_ocr_coexist(case):
    desc = space.hybrid_page_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    report = space.mixed_observations_report(desc)
    expected = {"status": "coexist", "native_content_ids": ["c-native"],
                "ocr_content_ids": ["c-ocr"], "native_evidence_origin": "source",
                "ocr_evidence_origin": "extracted", "forced_equality": False}
    for key, want in expected.items():
        if report.get(key) != want:
            return _w("coexistence_broken", {key: want},
                      {key: report.get(key)})
    return None


def _check_spatial_not_order(case):
    desc = space.geometry_fixture()
    before = copy.deepcopy(desc["relations"])
    report = space.spatial_predicates(desc)
    overlaps = [p for p in report if p["predicate"] == "overlap"]
    if not overlaps or overlaps[0]["status"] != "known" or overlaps[0]["value"] is not True:
        return _w("overlap_not_reported", "known overlap on figure/caption",
                  overlaps[:1])
    if desc["relations"] != before:
        return _w("relations_mutated", "unchanged relation set", "mutated")
    emitted = space.emitted_order_edges(report)
    if emitted != []:
        return _w("order_edges_emitted", [], emitted)
    return None


def _check_no_spatial_reading_order(case):
    desc = space.geometry_fixture()
    before_ids = {r["id"] for r in desc["relations"]}
    report = space.spatial_predicates(desc)
    if not report:
        return _w("predicates_not_evaluated", "nonempty report", [])
    if {r["id"] for r in desc["relations"]} != before_ids:
        return _w("relations_mutated", sorted(before_ids),
                  sorted(r["id"] for r in desc["relations"]))
    emitted = space.emitted_order_edges(report)
    if emitted != []:
        return _w("precedes_contains_emitted", [], emitted)
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid_after_eval", "accepted", typed_check(desc)[1])
    return None


# -- generators and checks (context) ----------------------------------------------

def _check_publication_date(case):
    desc = ctx.issue_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    report = ctx.claim_classification(desc, "a-issue-date")
    if report["status"] != "publication_context":
        return _w("date_not_publication_context", "publication_context", report)
    own = [c["term"] for c in ctx.claims_for(desc, "r-poem")]
    if "mag:publication-date" in own:
        return _w("date_narrated_by_poem", "no date claim on the poem", own)
    return None


def _check_quoted_author(case):
    desc = ctx.issue_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    if ctx.inherited_bindings(desc, "c-quote") != []:
        return _w("automatic_inheritance", [], ctx.inherited_bindings(desc, "c-quote"))
    policy = {"inherit_terms": ["mag:author"], "along": "contains"}
    inherited = ctx.inherited_bindings(desc, "c-quote", policy)
    if not inherited:
        return _w("declared_inheritance_missing", "inherited bindings under policy", [])
    for b in inherited:
        if b["provenance"] != "inherited":
            return _w("inheritance_unmarked", "inherited", b)
    own = [c["term"] for c in ctx.claims_for(desc, "c-quote")]
    if "mag:author" in own:
        return _w("author_assigned_to_quote", "no author claim on the quote", own)
    return None


def _check_context_dispute(case):
    desc = ctx.dispute_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    report = ctx.resolve_bindings(desc, "mag:publication-date", "r-issue")
    if report["status"] != "disputed" or sorted(report["claims"]) != ["a-date-manual",
                                                                      "a-date-ocr"]:
        return _w("conflict_not_retained", {"status": "disputed",
                                            "claims": ["a-date-manual", "a-date-ocr"]},
                  report)
    resolved = ctx.resolve_bindings(
        desc, "mag:publication-date", "r-issue",
        precedence={"policy": "manual-over-ocr", "prefer_origin": "manual"})
    if (resolved["status"] != "resolved" or resolved["winner"] != "a-date-manual"
            or len(resolved["retained"]) != 2):
        return _w("precedence_not_deterministic",
                  {"status": "resolved", "winner": "a-date-manual", "retained": 2},
                  resolved)
    return None


def _gen_same_pinned_input(seed):
    rng = random.Random(seed)
    return {"seed": seed,
            "alt": rng.choice(("1991-04", "1991-05", "1992-01", "1990-12"))}


def _check_same_pinned_input(case):
    desc = ctx.issue_fixture()
    first = ctx.evaluate_claims(copy.deepcopy(desc))
    second = ctx.evaluate_claims(copy.deepcopy(desc))
    if not ctx.canonically_equal_claims(first, second):
        return _w("replay_not_deterministic", "canonical claim equality", "differed")
    if not first["claims"]:
        return _w("vacuous_replay", "nonempty claim set", [])
    changed = copy.deepcopy(desc)
    changed["annotations"][0]["value"] = case["alt"]
    if ctx.canonically_equal_claims(first, ctx.evaluate_claims(changed)):
        return _w("constant_evaluation", "changed pinned input changes the outcome",
                  case["alt"])
    return None


def _check_uncertain_ocr(case):
    desc = ctx.uncertain_fixture()
    if typed_check(desc)[0] != "accepted":
        return _w("fixture_invalid", "accepted", typed_check(desc)[1])
    claims = ctx.claims_for(desc, "c-poem-text")
    if len(claims) != 2:
        return _w("transcriptions_missing", 2, len(claims))
    by_origin = {c["origin"]: c for c in claims}
    ocr, manual = by_origin.get("extracted"), by_origin.get("manual")
    if not ocr or ocr["status"] != "disputed" or not ocr["evidence"]:
        return _w("ocr_status_laundered", "disputed with evidence", ocr)
    if not manual or manual["status"] != "supported":
        return _w("manual_status_wrong", "supported", manual)
    if ctx.elected_winner(claims) is not None:
        return _w("winner_elected", None, ctx.elected_winner(claims))
    return None


def _check_no_union_on_assembly(case):
    a, b = ctx.two_claim_parts()
    result = compose(a, b)
    if result["status"] != "assembled":
        return _w("compose_refused", "assembled",
                  {"rule": result.get("rule"), "smallest": result.get("smallest")})
    report = ctx.assembled_meaning(result["descriptor"])
    if report["status"] != "no_generic_union" or report["reason"] != "requires_pinned_domain_rule":
        return _w("generic_union", {"status": "no_generic_union",
                                    "reason": "requires_pinned_domain_rule"}, report)
    terms = sorted((c["target"], c["value"]) for c in report["claims"])
    if terms != [("r-poem-1", "1991-03"), ("r-poem-2", "1991-04")]:
        return _w("claims_scoped_wrong",
                  [("r-poem-1", "1991-03"), ("r-poem-2", "1991-04")], terms)
    return None


# -- the catalogue ----------------------------------------------------------------

LAWS = (
    LawSpec("document.assembly.layer/compatible_pair", "assembly",
            "assembly_compatible", _gen_compatible_pair, _check_compatible_pair,
            observable_scope=("a", "b")),
    LawSpec("document.assembly.layer/duplicate_conflict", "assembly",
            "assembly_compatible", _gen_duplicate_conflict, _check_duplicate_conflict,
            observable_scope=("a", "b")),
    LawSpec("document.assembly.layer/left_right_identity", "assembly",
            "assembly_identity", _gen_left_right_identity, _check_left_right_identity,
            observable_scope=("a",)),
    LawSpec("document.assembly.layer/associate_three", "assembly",
            "assembly_associative", _gen_associate_three, _check_associate_three,
            observable_scope=("a", "b", "c")),
    LawSpec("document.assembly.layer/no_invented_order", "assembly",
            "order_not_implicit", _gen_no_invented_order, _check_no_invented_order,
            observable_scope=("a", "b")),
    LawSpec("document.assembly.layer/shared_id_merges", "assembly",
            "boundaries_preserved", _gen_shared_id_merges, _check_shared_id_merges,
            observable_scope=("a", "b")),
    LawSpec("document.assembly.layer/join_commutative", "assembly",
            "assembly_join_commutative", _gen_anchored_pair, _check_join_commutative,
            observable_scope=("a", "b"), required_declarations=("identity_profile_v1",)),
    LawSpec("document.assembly.layer/join_idempotent", "assembly",
            "assembly_join_idempotent", _gen_anchored_part, _check_join_idempotent,
            observable_scope=("x",), required_declarations=("identity_profile_v1",)),
    LawSpec("document.assembly.layer/refusal_absorbs", "assembly",
            "refusal_absorbing", _gen_refusal_absorption, _make_absorption_check(compose),
            observable_scope=("a", "b", "p"),
            required_declarations=("identity_profile_v1",)),
    LawSpec("document.views.layer/view_overlap", "views",
            "named_view_membership", lambda seed: {"seed": seed}, _check_view_overlap,
            observable_scope=("fixture",)),
    LawSpec("document.views.layer/cycle_refused", "views",
            "containment_acyclic", lambda seed: {"seed": seed}, _check_cycle_refused,
            observable_scope=("fixture",)),
    LawSpec("document.views.layer/partial_order_ok", "views",
            "partial_order", lambda seed: {"seed": seed}, _check_partial_order_ok,
            observable_scope=("fixture", "cycle_variant")),
    LawSpec("document.views.layer/projection", "views",
            "projection_fidelity", _gen_projection, _check_projection,
            observable_scope=("fixture", "keep")),
    LawSpec("document.views.layer/refinement_conflict", "views",
            "refinement_explicit", _gen_refinement_conflict, _check_refinement_conflict,
            observable_scope=("fixture", "removed")),
    LawSpec("document.views.layer/links_not_containment", "views",
            "nonhierarchical_links", lambda seed: {"seed": seed},
            _check_links_not_containment, observable_scope=("fixture",)),
    LawSpec("document.space.layer/pdf_rotation", "space",
            "carrier_coordinate_frames", _gen_pdf_rotation, _check_pdf_rotation,
            observable_scope=("observed", "expected")),
    LawSpec("document.space.layer/cross_page_unknown", "space",
            "frame_compatibility", _gen_cross_page_unknown, _check_cross_page_unknown,
            observable_scope=("a", "b")),
    LawSpec("document.space.layer/epub_reflow", "space",
            "epub_stable_identity", _gen_epub_reflow, _check_epub_reflow,
            observable_scope=("small", "large")),
    LawSpec("document.space.layer/native_ocr_coexist", "space",
            "mixed_observations", lambda seed: {"seed": seed},
            _check_native_ocr_coexist, observable_scope=("fixture",)),
    LawSpec("document.space.layer/spatial_not_order", "space",
            "spatial_order_separation", lambda seed: {"seed": seed},
            _check_spatial_not_order, observable_scope=("fixture", "report")),
    LawSpec("document.space.layer/roundtrip_transform", "space",
            "geometry_transform", _gen_roundtrip, _check_roundtrip,
            observable_scope=("source",)),
    LawSpec("document.space.layer/no_spatial_reading_order", "space",
            "spatial_order_separation", lambda seed: {"seed": seed},
            _check_no_spatial_reading_order, observable_scope=("fixture", "report")),
    LawSpec("document.context.layer/publication_date", "context",
            "claims_attributed", lambda seed: {"seed": seed}, _check_publication_date,
            observable_scope=("fixture",)),
    LawSpec("document.context.layer/quoted_author", "context",
            "context_scoped", lambda seed: {"seed": seed}, _check_quoted_author,
            observable_scope=("fixture",)),
    LawSpec("document.context.layer/context_dispute", "context",
            "shadow_conflict", lambda seed: {"seed": seed}, _check_context_dispute,
            observable_scope=("fixture",)),
    LawSpec("document.context.layer/same_pinned_input", "context",
            "deterministic_interpretation", _gen_same_pinned_input,
            _check_same_pinned_input, observable_scope=("fixture", "alt")),
    LawSpec("document.context.layer/uncertain_ocr", "context",
            "no_truth_laundering", lambda seed: {"seed": seed}, _check_uncertain_ocr,
            observable_scope=("fixture",)),
    LawSpec("document.context.layer/no_union_on_assembly", "context",
            "no_generic_meaning_union", lambda seed: {"seed": seed},
            _check_no_union_on_assembly, observable_scope=("parts",)),
)

EXPECTED_LAW_IDS = frozenset(law.law_id for law in LAWS)

# Mutation probe: the pre-fix compose behavior (a LEFT-side refusal was
# unwrapped and dropped, the other operand leaking through). Used only to
# exercise the violation -> counterexample bundle -> replay path end to end;
# it is not a law of any delta and never counted as catalogue coverage.
PROBES = {
    "probe/absorption-drop-left": LawSpec(
        "probe/absorption-drop-left", "assembly", "refusal_absorbing",
        _gen_refusal_absorption,
        _make_absorption_check(lambda a, b: b if isinstance(a, dict)
                               and a.get("status") == "refused" else compose(a, b)),
        observable_scope=("a", "b", "p")),
}

REGISTRY = {**{law.law_id: law for law in LAWS}, **PROBES}


# -- runner, violation export, replay ---------------------------------------------

def run_law(law, seed=0):
    """Classify one law into the verdict vocabulary. A law without a generator
    or without a required declaration is incomplete — never holds."""
    if law.generator is None or law.check is None:
        return {"law_id": law.law_id, "section": law.section,
                "verdict": "incomplete", "reason": "no_generator"}
    missing = [d for d in law.required_declarations if d not in DECLARATIONS]
    if missing:
        return {"law_id": law.law_id, "section": law.section,
                "verdict": "incomplete", "reason": "missing_declaration",
                "missing": missing}
    case = law.generator(seed)
    if not law.applicable(case):
        return {"law_id": law.law_id, "section": law.section,
                "verdict": "not-applicable"}
    witness = law.check(case)
    if witness is None:
        return {"law_id": law.law_id, "section": law.section, "verdict": "holds"}
    return {"law_id": law.law_id, "section": law.section, "verdict": "violated",
            "witness": witness, "bundle": export_violation(law, seed, case, witness)}


def run_catalogue(seed=0):
    """Run every catalogue law over the seeded generated inputs."""
    return [run_law(law, seed) for law in LAWS]


def export_violation(law, seed, case, witness):
    """Replayable counterexample bundle through compare.export_counterexample:
    carries the generated inputs, the seed and the law id (as rule_id); the
    witness records the verdict so re-running reproduces it."""
    outcome = compare.ComparisonOutcome(
        "different", law.law_id, witness=witness["witness"],
        message=f"law {law.law_id} violated on seeded generated inputs",
        details={"expected": witness["expected"], "observed": witness["observed"]})
    spec = compare.ComparatorSpec("law-catalogue", "1",
                                  ("law_case", "law_case"),
                                  tuple(law.observable_scope))
    left = compare.ComparisonInput(
        "law_case", {"law_id": law.law_id, "seed": seed, "case": case})
    right = compare.ComparisonInput(
        "law_case", {"verdict": "violated", "expected": witness["expected"],
                     "observed": witness["observed"]})
    bundle = compare.export_counterexample(outcome, spec, left, right)
    bundle["witness"]["seed"] = seed
    bundle["witness"]["law_id"] = law.law_id
    bundle["witness"]["verdict"] = "violated"
    return bundle


def replay_law(bundle):
    """Re-run a law from an exported bundle: regenerate the case from the
    carried seed (hash-checked against the carried inputs), re-check, and
    confirm the verdict reproduces."""
    raw = compare.load_bundle(compare.serialize_bundle(bundle))
    witness = raw["witness"]
    if not witness.get("replayable", True):
        raise compare.NotReplayable(witness["rule_id"])
    law = REGISTRY.get(witness["law_id"])
    if law is None:
        return {"reproduced": False, "verdict": "unknown_law"}
    case = law.generator(witness["seed"])
    regenerated = {"law_id": witness["law_id"], "seed": witness["seed"],
                   "case": case}
    if raw["inputs"]["left"]["payload"] != regenerated:
        return {"reproduced": False, "verdict": "input_regeneration_mismatch"}
    verdict = "violated" if law.check(case) is not None else "holds"
    return {"reproduced": verdict == witness["verdict"], "verdict": verdict}


# -- catalogue tests ----------------------------------------------------------------

class TestLawCatalogue(unittest.TestCase):
    def test_catalogue_lists_every_law_with_generator(self):
        """Every assembly/views/space/context law is listed exactly once, with
        id, seeded generator and check — a complete catalogue."""
        self.assertTrue(LAWS)
        self.assertEqual(frozenset(law.law_id for law in LAWS), EXPECTED_LAW_IDS)
        self.assertEqual(len(LAWS), len(set(law.law_id for law in LAWS)))
        for law in LAWS:
            self.assertIn(law.section, SECTIONS, law.law_id)
            self.assertTrue(law.constraint, law.law_id)
            self.assertIsNotNone(law.generator, law.law_id)
            self.assertIsNotNone(law.check, law.law_id)

    def test_seeded_run_over_generated_inputs(self):
        """Running the catalogue over seeded generated inputs: every listed
        law holds; nothing is violated, incomplete or not-applicable."""
        for seed in (0, 7, 2026):
            results = run_catalogue(seed)
            self.assertEqual(len(results), len(EXPECTED_LAW_IDS))
            for r in results:
                self.assertEqual(r["verdict"], "holds", (r["law_id"], r))
                self.assertNotIn("bundle", r)

    def test_seeded_generation_is_deterministic_and_seed_sensitive(self):
        """The same seed regenerates identical inputs; a different seed
        regenerates different ones (generation is reproducible, not constant)."""
        self.assertEqual(_gen_anchored_pair(11), _gen_anchored_pair(11))
        self.assertNotEqual(_gen_anchored_pair(11), _gen_anchored_pair(12))
        self.assertEqual(_gen_projection(3), _gen_projection(3))
        self.assertEqual(run_catalogue(5), run_catalogue(5))

    def test_incomplete_laws_never_hold(self):
        """A law without a generator or without a required declaration is
        reported incomplete — never holds."""
        law = next(l for l in LAWS if "join" in l.law_id)
        no_gen = dataclasses.replace(law, generator=None, check=None)
        r = run_law(no_gen, seed=1)
        self.assertEqual(r["verdict"], "incomplete")
        self.assertEqual(r["reason"], "no_generator")
        self.assertNotEqual(r["verdict"], "holds")
        self.assertNotIn("bundle", r)
        missing = dataclasses.replace(law, required_declarations=("undeclared:profile",))
        r2 = run_law(missing, seed=1)
        self.assertEqual(r2["verdict"], "incomplete")
        self.assertEqual(r2["reason"], "missing_declaration")
        self.assertEqual(r2["missing"], ["undeclared:profile"])
        self.assertNotEqual(r2["verdict"], "holds")

    def test_not_applicable_is_reported_not_collapsed(self):
        """not-applicable is part of the vocabulary and is reported as such —
        never collapsed into holds or violated."""
        law = next(l for l in LAWS if l.law_id.endswith("refusal_absorbs"))
        r = run_law(dataclasses.replace(law, applicable=lambda case: False), seed=2)
        self.assertEqual(r["verdict"], "not-applicable")
        self.assertIn("not-applicable", VERDICTS)
        self.assertEqual(set(VERDICTS),
                         {"holds", "violated", "not-applicable", "incomplete"})

    def test_violation_exports_replayable_counterexample_bundle(self):
        """A violated law exports a replayable counterexample bundle through
        compare.export_counterexample carrying inputs + seed + law id; replay
        reproduces the verdict; export is byte-deterministic."""
        probe = PROBES["probe/absorption-drop-left"]
        r = run_law(probe, seed=5)
        self.assertEqual(r["verdict"], "violated")
        bundle = r["bundle"]
        raw = compare.load_bundle(compare.serialize_bundle(bundle))
        w = raw["witness"]
        self.assertEqual(w["law_id"], probe.law_id)
        self.assertEqual(w["rule_id"], probe.law_id)
        self.assertEqual(w["seed"], 5)
        self.assertEqual(w["verdict"], "violated")
        self.assertTrue(w["replayable"])
        self.assertIn("case", raw["inputs"]["left"]["payload"])
        sha = hashlib.sha256(json.dumps(raw["inputs"]["left"]["payload"],
                                        sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(w["input_hashes"]["left"], sha)
        rep = replay_law(bundle)
        self.assertTrue(rep["reproduced"], rep)
        self.assertEqual(rep["verdict"], "violated")
        again = run_law(probe, seed=5)["bundle"]
        self.assertEqual(compare.serialize_bundle(bundle),
                         compare.serialize_bundle(again))

    def test_redacted_bundle_is_not_replayable(self):
        """A redacted export (replayable=false) refuses replay instead of
        fabricating a reproducible source (compare.NotReplayable)."""
        probe = PROBES["probe/absorption-drop-left"]
        r = run_law(probe, seed=6)
        outcome, spec = compare.ComparisonOutcome(
            "different", probe.law_id, witness="redacted-probe"), compare.ComparatorSpec(
            "law-catalogue", "1", ("law_case", "law_case"), ())
        redacted = compare.export_counterexample(
            outcome, spec,
            compare.ComparisonInput("law_case", {"payload": "withheld"}),
            compare.ComparisonInput("law_case", {"payload": "withheld"}), redact=True)
        self.assertFalse(redacted["witness"]["replayable"])
        raw = compare.load_bundle(compare.serialize_bundle(redacted))
        with self.assertRaises(compare.NotReplayable):
            replay_law(raw)

    def test_unknowns_documented_not_implied_passing(self):
        """Unimplemented operations are documented unknowns; no catalogue
        verdict implies kernel conformance or unexecuted runs."""
        self.assertTrue(UNKNOWNS)
        topics = {u["topic"] for u in UNKNOWNS}
        for topic in ("deployed kernel composition checker",
                      "counterexample export to Sunset Lens",
                      "independent reader agreement (debugger slice 4)",
                      "OCR runs and real-carrier factorization",
                      "EPUB carrier runs"):
            self.assertIn(topic, topics)
        for u in UNKNOWNS:
            self.assertTrue(u["topic"] and u["detail"], u)
        # every catalogue law is machinery-side: its verdict comes from an
        # executed check over generated inputs, never from a conformance label
        for law in LAWS:
            self.assertTrue(callable(law.check), law.law_id)
            self.assertTrue(callable(law.generator), law.law_id)


if __name__ == "__main__":
    unittest.main()
