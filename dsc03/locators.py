# Purpose: Carrier locator adapters and synchronized selection for the document
#   structural debugger (sunset-xx7.2, slice 2 of add-document-structural-debugger).
# Responsibilities: Resolve a selected region/content to ALL available source
#   loci and evidence records over carrier-specific coordinate domains — PDF
#   fixed-coordinate page/rect geometry, EPUB stable XHTML/CFI selectors where
#   transient viewport coordinates are never persistent identity, and scan-image
#   pixel-domain locators with explicit dpi/scale keeping mixed-mode native/raster
#   observations distinct — while reporting missing selectors as an explicit
#   missing state, multiple matching targets as ambiguity with neither target
#   auto-selected, and unsupported locators via the slice-1 unsupported diagnostic
#   category (dbg.locator.unsupported); enumerate every legal topological sort of
#   a scoped reading order (partial order: no total order invented, display sort
#   labeled as not unique) and derive display coordinates only on explicit
#   request (to_display). Pure read-only: consumes dsc03.inspect indexes and
#   never writes or mutates descriptors or sources.
# Rationale: document-debugger spec deltas (carrier_locators,
#   bidirectional_navigation, scoped_structure; properties pdf_epub_no_ocr,
#   ambiguous_selector, partial_order). Builds on the shipped slice-1 surface
#   (InspectionIndex/Diagnostic) without changing it; comparators/counterexamples
#   (slice 3) and a11y (slice 4) stay out of scope. No OCR, no network.
"""Carrier locator adapters + synchronized selection (sunset-xx7.2)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from dsc03.inspect import Diagnostic

__all__ = [
    "Locus",
    "ReadingOrderView",
    "ScanObservation",
    "Selection",
    "classify_locator",
    "locator_support",
    "reading_orders",
    "resolve",
    "resolve_locator",
    "resolve_scan_page",
    "to_display",
    "unsupported_diagnostics",
]

_RULE_LOCATOR_UNSUPPORTED = "dbg.locator.unsupported"

_PDF_LOCATOR_RE = re.compile(
    r"^page:(?P<page>\d+)(?:\s+rect:(?P<rect>\d+,\d+,\d+,\d+))?$"
)
_SCAN_LOCATOR_RE = re.compile(
    r"^pixels\s+rect:(?P<rect>\d+,\d+,\d+,\d+)\s+dpi:(?P<dpi>\d+)"
    r"(?:\s+scale:(?P<scale>\d+(?:\.\d+)?))?$"
)
_DOMAINS = {
    "pdf": "pdf-fixed-coordinate",
    "epub-cfi": "epub-stable-selector",
    "epub-resource": "epub-stable-selector",
    "scan": "scan-pixel-domain",
}


def classify_locator(locator: str):
    """Classify a locator string into its coordinate-domain scheme.

    Returns (scheme, reason): scheme is one of "pdf", "epub-cfi",
    "epub-resource", "scan", "viewport" (transient — never persistent
    identity), or None for unclassifiable input; reason is "" exactly when
    the scheme is usable as a persistent source anchor.
    """
    # sunset-xx7.4 (additive): non-string locators are classified input, not
    # crashes — return the same (None, reason) shape as unknown schemes.
    if not isinstance(locator, str):
        return None, f"non-string locator: {type(locator).__name__}"
    text = locator.strip()
    if text.startswith("viewport"):
        return "viewport", "viewport coordinates are transient and never persistent identity"
    if _PDF_LOCATOR_RE.match(text):
        return "pdf", ""
    if _SCAN_LOCATOR_RE.match(text):
        return "scan", ""
    if text.startswith("epubcfi(") and text.endswith(")"):
        return "epub-cfi", ""
    if text.startswith("resource:"):
        return "epub-resource", ""
    scheme = text.split(":", 1)[0] if ":" in text else text.split(" ", 1)[0]
    return None, f"unknown locator scheme: {scheme}"


@dataclass(frozen=True)
class Locus:
    """One persistent source location in its declared coordinate domain.

    display_rect is always None here: display coordinates exist only as the
    explicit, on-demand output of to_display() — never as stored identity.
    """

    domain: str
    kind: str
    value: str
    page: int | None = None
    rect: tuple | None = None
    dpi: int | None = None
    scale: float | None = None
    display_rect: tuple | None = None


@dataclass(frozen=True)
class Selection:
    """Outcome of resolving one selection (bidirectional_navigation).

    status is "resolved", "missing", "ambiguous" or "unsupported"; loci is
    empty unless exactly one interpretation is possible; candidates carries
    the competing targets for ambiguity (neither auto-selected); reason is a
    classified explanation for every non-resolved status.
    """

    target_id: str
    status: str
    loci: tuple = ()
    evidence_ids: tuple = ()
    candidates: tuple = ()
    reason: str = ""


@dataclass(frozen=True)
class ScanObservation:
    """One distinct observation on a scan page (mixed mode is never merged)."""

    region_id: str
    origin: str
    loci: tuple
    evidence_ids: tuple


@dataclass(frozen=True)
class ReadingOrderView:
    """All legal topological sorts of a scoped reading order (partial_order).

    orders lists every legal sort; display_sort is one deterministic display
    convenience order that is explicitly NOT asserted as unique.
    """

    view_id: str
    orders: tuple
    display_sort: tuple
    display_is_unique: bool = False


def _parse_pdf(locator: str) -> Locus:
    m = _PDF_LOCATOR_RE.match(locator.strip())
    rect = None
    if m.group("rect"):
        rect = tuple(int(x) for x in m.group("rect").split(","))
    return Locus(
        domain="pdf-fixed-coordinate",
        kind="page" if rect is None else "rect",
        value=locator.strip(),
        page=int(m.group("page")),
        rect=rect,
    )


def _parse_scan(locator: str) -> Locus:
    m = _SCAN_LOCATOR_RE.match(locator.strip())
    rect = tuple(int(x) for x in m.group("rect").split(","))
    scale = float(m.group("scale")) if m.group("scale") else None
    return Locus(
        domain="scan-pixel-domain",
        kind="pixel-rect",
        value=locator.strip(),
        rect=rect,
        dpi=int(m.group("dpi")),
        scale=scale,
    )


def _parse_epub(locator: str, scheme: str) -> Locus:
    return Locus(
        domain="epub-stable-selector",
        kind="cfi" if scheme == "epub-cfi" else "resource",
        value=locator.strip(),
    )


def _build_locus(locator: str, scheme: str):
    if scheme == "pdf":
        return _parse_pdf(locator)
    if scheme == "scan":
        return _parse_scan(locator)
    if scheme in ("epub-cfi", "epub-resource"):
        return _parse_epub(locator, scheme)
    return None


def locator_support(index, selector) -> tuple:
    """(supported, reason) for one selector's locator as a persistent anchor."""
    # sunset-xx7.4 (additive): a selector with no locator key is malformed
    # input, classified like any other unclassifiable locator (never a crash).
    scheme, reason = classify_locator(selector.get("locator"))
    if scheme == "viewport":
        return False, reason
    if scheme is None:
        return False, reason
    return True, ""


def _evidence_for(index, target_id: str, selector_ids) -> tuple:
    """All evidence records linked to the selection: via its selectors and
    via the contents attached to it (has-content)."""
    sset = set(selector_ids)
    attached = {
        r["to"]
        for r in index.relations.values()
        if r["kind"] == "has-content" and r["from"] == target_id
    }
    out = set()
    for e in index.evidence.values():
        if sset & set(e["selector_ids"]) or (
            set(e["content_ids"]) & attached or target_id in e["content_ids"]
        ):
            out.add(e["id"])
    return tuple(sorted(out))


def _selectors_for(index, target_id: str) -> list:
    return [s for s in index.selectors.values() if s["target"] == target_id]


def resolve(index, target_id: str) -> Selection:
    """Resolve one selected region/content id to ALL available source loci
    and evidence records. Missing, ambiguous and unsupported outcomes are
    explicit; nothing is invented and nothing is auto-selected."""
    is_region = target_id in index.regions
    is_content = target_id in index.contents
    if is_region and is_content:
        return Selection(
            target_id=target_id,
            status="ambiguous",
            candidates=("content", "region"),
            reason=(
                f"multiple matching targets for {target_id}: one region and "
                "one content — neither auto-selected"
            ),
        )
    if not is_region and not is_content:
        return Selection(
            target_id=target_id,
            status="missing",
            reason=f"no region or content with id {target_id}",
        )
    selectors = _selectors_for(index, target_id)
    if not selectors:
        return Selection(
            target_id=target_id,
            status="missing",
            reason=f"no selector declared for target {target_id}",
        )
    loci = []
    unsupported_reasons = []
    for s in selectors:
        supported, reason = locator_support(index, s)
        if not supported:
            unsupported_reasons.append(f"{s['id']}: {reason}")
            continue
        scheme, _ = classify_locator(s["locator"])
        locus = _build_locus(s["locator"], scheme)
        if locus is not None:
            loci.append(locus)
    evidence = _evidence_for(index, target_id, [s["id"] for s in selectors])
    if not loci and unsupported_reasons:
        return Selection(
            target_id=target_id,
            status="unsupported",
            evidence_ids=evidence,
            reason="; ".join(unsupported_reasons),
        )
    # sunset-xx7.4 (additive): when some selectors were malformed alongside
    # usable ones, the classified reasons are surfaced on the resolved
    # selection too — the malformed selectors are never silently dropped.
    return Selection(
        target_id=target_id,
        status="resolved",
        loci=tuple(loci),
        evidence_ids=evidence,
        reason="; ".join(unsupported_reasons),
    )


def resolve_locator(index, locator: str) -> Selection:
    """Resolve a source locator string to its target(s). If the locator
    matches more than one target the result is ambiguous and neither target
    is auto-selected."""
    matches = sorted(
        {s["target"] for s in index.selectors.values() if s["locator"].strip() == locator.strip()}
    )
    if not matches:
        return Selection(
            target_id=locator,
            status="missing",
            reason=f"no selector declares locator {locator.strip()!r}",
        )
    if len(matches) > 1:
        return Selection(
            target_id=locator,
            status="ambiguous",
            candidates=tuple(matches),
            reason=(
                "multiple matching targets for locator "
                f"{locator.strip()!r}: {', '.join(matches)} — neither auto-selected"
            ),
        )
    return resolve(index, matches[0])


def resolve_scan_page(index, page_region_id: str) -> tuple:
    """Resolve one scan page into its distinct mixed-mode observations.

    Each contained region (native text vs raster origin) stays a separate
    ScanObservation with its own pixel-domain loci and independently
    accessible evidence; observations are never merged across origins.
    """
    page = index.regions.get(page_region_id)
    if page is None:
        return (
            Selection(
                target_id=page_region_id,
                status="missing",
                reason=f"no region with id {page_region_id}",
            ),
        )
    children = index.containment().get(page_region_id, ())
    observations = []
    for cid in children:
        sel = resolve(index, cid)
        if sel.status != "resolved":
            continue
        observations.append(
            ScanObservation(
                region_id=cid,
                origin=index.regions[cid]["kind"],
                loci=sel.loci,
                evidence_ids=sel.evidence_ids,
            )
        )
    return tuple(observations)


def unsupported_diagnostics(index) -> tuple:
    """Typed diagnostics for every selector whose locator cannot serve as a
    persistent source anchor, using the slice-1 unsupported category."""
    out = []
    for s in index.selectors.values():
        supported, reason = locator_support(index, s)
        if not supported:
            out.append(
                Diagnostic(
                    category="unsupported",
                    rule_id=_RULE_LOCATOR_UNSUPPORTED,
                    witness=s["id"],
                    message=reason,
                )
            )
    return tuple(out)


def _all_topo_orders(nodes, edges) -> tuple:
    succ = {n: [] for n in nodes}
    indeg = {n: 0 for n in nodes}
    for u, v in edges:
        succ[u].append(v)
        indeg[v] += 1
    orders = []

    def rec(acc, indeg, remaining):
        if not remaining:
            orders.append(tuple(acc))
            return
        for n in sorted(remaining):
            if indeg[n] == 0:
                new_indeg = dict(indeg)
                for v in succ[n]:
                    new_indeg[v] -= 1
                rec(acc + [n], new_indeg, remaining - {n})

    rec([], indeg, set(nodes))
    return tuple(orders)


def reading_orders(index, view_id: str) -> ReadingOrderView:
    """Enumerate EVERY legal topological sort of the view's precedes edges.

    partial_order: no total order is invented — multiple legal sorts are all
    returned; the display sort is a deterministic convenience ordering that
    is never asserted as unique.
    """
    nodes = sorted(r for r, v in index.regions.items() if v["view_id"] == view_id)
    edges = [
        (a, b)
        for a, b, _ in index.reading_order_edges(view_id)
        if a in nodes and b in nodes
    ]
    orders = _all_topo_orders(nodes, edges)
    if not orders:  # unsatisfiable edge set (cycle): nothing legal to display
        orders = ()
    return ReadingOrderView(
        view_id=view_id,
        orders=orders,
        display_sort=tuple(nodes),
        display_is_unique=False,
    )


def to_display(locus: Locus, zoom: float) -> tuple | None:
    """Explicitly derive display coordinates from an intrinsic locus.

    The only sanctioned intrinsic->display conversion point; the locus itself
    never carries display coordinates.
    """
    if locus.rect is None:
        return None
    return tuple(int(round(v * zoom)) for v in locus.rect)
