# Purpose: Record visual-oracle results into demo/evaluation report dicts as a
#   SEPARATE evidence class (sunset-xzy.7, tasks.md 6.1).
# Responsibilities: Provide the pure ``record(report, visual_results)`` wiring:
#   it returns a NEW report dict carrying a distinct ``visual_oracles`` section
#   (per property/carrier/page outcome status, reasons, evidence-class label,
#   retained region verdicts, the shared aggregate status + blocker reasons,
#   and an explicit non-substitution note naming the conformance inputs this
#   section does NOT provide). Honest statuses only: every
#   ``unknown``/``unavailable``/``uncalibrated`` outcome passes through
#   verbatim (SCOPE-002) — never upgraded, never dropped, never masked by the
#   aggregate (the real ``coverage.aggregate`` rule decides pass/blocked).
#   Never mutates its inputs; never touches any other report section
#   (schema/profiles/coverage/interpretation, reader agreement, extractor
#   comparison, reviewed anchor mapping).
# Rationale: document-visual-oracles "Distinct evidence class in
#   demonstrations" (visual results are recorded separately from reader
#   agreement, extractor comparison and reviewed anchor mapping, and never
#   substitute for any of them), scenario "Oracles cannot complete a suite"
#   (passing oracles without independent readers leave the label
#   ``incomplete``), "Labeled evidence class" (correlated demonstrates
#   sensitivity, never accuracy), "No silent resolution", "Scoped property
#   claims", "No false claims". PLUMBING slice: no oracle semantics change, no
#   threshold change, no label change — ``dsc03.conformance.classify`` is
#   consumed as shipped and remains inert to this section. AGENT-EXECUTED:
#   nothing recorded here produces human evidence; a human pass supersedes.
"""Visual-oracle results as a separate evidence class in report dicts.

The section shape (per report dict):

- ``outcomes``: one entry per recorded outcome, in input order —
  ``property``, ``carrier``, ``page``, ``status`` (``agree``/``differ``/
  ``unknown``/``unavailable``, verbatim), ``reason`` (verbatim, may be
  ``None``), ``evidence_class`` (``correlated``/``independent`` per the
  pinned render rule), ``regions`` (retained per-claim verdicts, copied).
- ``aggregate``: the SHARED aggregate rule (``dsc03.visual.coverage.aggregate``)
  as plain scalars — ``pass`` ONLY when every page outcome agrees; any
  ``unknown``/``unavailable``/``differ`` page, or an empty outcome set,
  blocks with its reasons listed.
- ``evidence_class``: the section-level label — the single recorded class
  when uniform, ``mixed`` when outcomes carry differing classes, ``None``
  when nothing is recorded.
- ``non_substitution``: the conformance inputs this section does NOT
  provide (real carriers, independent readers, extractor comparison,
  reviewed anchor mapping) — recording visual results fills none of them.
"""
from __future__ import annotations

from dsc03.visual import coverage

SECTION = "visual_oracles"

# The conformance inputs this section does NOT provide, by suite-dict key
# name. Recording visual-oracle results fills NONE of them — not in data
# shape, not in labels.
NON_SUBSTITUTION = (
    "real_carriers",
    "independent_readers",
    "extractor_comparison",
    "anchor_mapping_reviewed",
)


def record(report, visual_results):
    """Return a new report dict with a distinct ``visual_oracles`` section.

    ``visual_results`` are typed oracle outcomes (``CoverageOutcome`` /
    ``AlignmentOutcome``). The input ``report`` is never mutated and its
    pre-existing sections are never filled, rewritten or relabeled; honest
    statuses pass through verbatim.
    """
    outcomes = list(visual_results)
    entries = [
        {
            "property": outcome.property,
            "carrier": outcome.carrier,
            "page": outcome.page,
            "status": outcome.status,
            "reason": outcome.reason,
            "evidence_class": outcome.evidence_class,
            "regions": [dict(region) for region in outcome.regions],
        }
        for outcome in outcomes
    ]
    aggregate = coverage.aggregate(outcomes)
    labels = sorted({outcome.evidence_class for outcome in outcomes})
    if not labels:
        section_label = None
    elif len(labels) == 1:
        section_label = labels[0]
    else:
        section_label = "mixed"
    section = {
        "outcomes": entries,
        "aggregate": {
            "status": aggregate.status,
            "reasons": list(aggregate.reasons),
        },
        "evidence_class": section_label,
        "non_substitution": list(NON_SUBSTITUTION),
    }
    recorded = dict(report)
    recorded[SECTION] = section
    return recorded
