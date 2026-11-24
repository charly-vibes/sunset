# Purpose: Scale-ladder containment laws (add-scale-complete-regions tasks 2.1, 2.2).
# Responsibilities: RED-first tests for word/line containment on the ladder:
#   a word outside its line is refused WITH a witness naming child and parent;
#   sub-tolerance box overhang is accepted and recorded; interval containment
#   is exact; box containment holds within the tolerance declared by the
#   geometry profile (default 0.5 pt); ladder scope order is enforced.
# Rationale: add-scale-complete-regions "Scale ladder with checked containment".
from dsc03.zoom import (DEFAULT_TOLERANCE_PT, SCALE_ORDER, containment,
                        geometry_tolerance, ladder_report)


def region(rid, scale, interval, box):
    return {"id": rid, "scale": scale, "interval": interval, "box": box}


def test_ladder_order_is_word_line_block_page():
    assert SCALE_ORDER == ("word", "line", "block", "page")


def test_word_outside_its_line_is_refused_with_witness():
    # Word raw interval exceeds the line interval: exact refusal, witness
    # naming the word (child) and the line (parent).
    word = region("w1", "word", (10, 30), [0, 0, 5, 5])
    line = region("l1", "line", (12, 28), [0, 0, 10, 10])
    outcome = containment(word, line, tolerance=DEFAULT_TOLERANCE_PT)
    assert outcome["status"] == "refused"
    assert outcome["reason"] == "scope-outside-parent"
    witness = outcome["witness"]
    assert witness["child"] == "w1"
    assert witness["parent"] == "l1"
    assert witness["interval_outside"] is True


def test_word_interval_outside_is_refused_even_when_box_fits():
    word = region("w1", "word", (0, 50), [1, 1, 9, 9])
    line = region("l1", "line", (0, 40), [0, 0, 10, 10])
    outcome = containment(word, line, tolerance=DEFAULT_TOLERANCE_PT)
    assert outcome["status"] == "refused"
    assert outcome["witness"]["interval_outside"] is True


def test_sub_tolerance_overhang_is_accepted_and_recorded():
    # Word box overhangs the line box by 0.3 pt (< 0.5 pt default): kept,
    # with the overhang recorded on the outcome, never refused.
    word = region("w1", "word", (1, 9), [-0.3, 0, 10.3, 10])
    line = region("l1", "line", (0, 10), [0, 0, 10, 10])
    outcome = containment(word, line, tolerance=DEFAULT_TOLERANCE_PT)
    assert outcome["status"] == "accepted"
    assert outcome["overhang"] is not None
    assert outcome["overhang"]["child"] == "w1"
    assert outcome["overhang"]["parent"] == "l1"
    assert abs(max(outcome["overhang"]["edges"]) - 0.3) < 1e-9


def test_exact_containment_is_accepted_without_overhang():
    word = region("w1", "word", (1, 9), [1, 1, 9, 9])
    line = region("l1", "line", (1, 9), [1, 1, 9, 9])
    outcome = containment(word, line, tolerance=DEFAULT_TOLERANCE_PT)
    assert outcome["status"] == "accepted"
    assert outcome["overhang"] is None


def test_overhang_beyond_tolerance_is_refused():
    word = region("w1", "word", (0, 10), [-2.0, 0, 10, 10])
    line = region("l1", "line", (0, 10), [0, 0, 10, 10])
    outcome = containment(word, line, tolerance=DEFAULT_TOLERANCE_PT)
    assert outcome["status"] == "refused"
    assert outcome["witness"]["child"] == "w1"
    assert outcome["witness"]["parent"] == "l1"


def test_ladder_scope_order_is_enforced():
    # Same-scale or inverted nesting (word in word, block in line) is a
    # typed refusal, never silently accepted.
    inner = region("x1", "block", (0, 10), [0, 0, 10, 10])
    outer = region("x2", "line", (0, 10), [0, 0, 10, 10])
    outcome = containment(inner, outer, tolerance=DEFAULT_TOLERANCE_PT)
    assert outcome["status"] == "refused"
    assert outcome["reason"] == "invalid-ladder-order"


def test_tolerance_is_declared_by_the_geometry_profile():
    # The geometry profile declares the tolerance; a 1.5 pt overhang refused
    # at the 0.5 pt default is accepted under a declared 2.0 pt tolerance.
    profile = {"kind": "geometry", "version": "1", "frames": [], "tolerance": 2.0}
    assert geometry_tolerance(profile) == 2.0
    assert geometry_tolerance({"kind": "geometry", "version": "1", "frames": []}) == 0.5
    word = region("w1", "word", (0, 10), [-1.5, 0, 10, 10])
    line = region("l1", "line", (0, 10), [0, 0, 10, 10])
    assert containment(word, line, tolerance=2.0)["status"] == "accepted"
    assert containment(word, line, tolerance=0.5)["status"] == "refused"


def test_ladder_report_records_overhangs_and_refuses_violations():
    # A full descriptor ladder: every checked contains edge is evaluated;
    # the report records sub-tolerance overhangs and refuses violations
    # with witnesses.
    regions = {
        "l1": region("l1", "line", (0, 20), [0, 0, 100, 10]),
        "w1": region("w1", "word", (0, 10), [-0.2, 0, 50, 10]),
        "w2": region("w2", "word", (10, 30), [40, 0, 90, 10]),  # interval outside
    }
    contains = [("l1", "w1"), ("l1", "w2")]
    report = ladder_report(lambda rid: regions[rid], contains,
                           tolerance=DEFAULT_TOLERANCE_PT)
    assert report["status"] == "refused"
    assert any(v["witness"]["child"] == "w2" and v["witness"]["parent"] == "l1"
               for v in report["violations"])
    assert any(o["child"] == "w1" for o in report["overhangs"])

    clean = {"w2": region("w2", "word", (10, 20), [40, 0, 90, 10])}
    report = ladder_report(lambda rid: {**regions, **clean}[rid], contains,
                           tolerance=DEFAULT_TOLERANCE_PT)
    assert report["status"] == "accepted"
    assert any(o["child"] == "w1" for o in report["overhangs"])
