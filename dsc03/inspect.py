# Purpose: Read-only DSC 0.3 descriptor inspection layer for the document
#   structural debugger (sunset-xx7.1, slice 1 of add-document-structural-debugger).
# Responsibilities: Load a 0.3 descriptor via dsc03.validator (two-phase
#   lexical/type + semantic validation) without writing anything; build a
#   validated inspection index over regions/containment, reading-order edges,
#   evidence records, provenance/annotations, selectors, interpretations and
#   coverage with O(1)-ish id lookup; emit a typed diagnostics model whose
#   categories are exactly pass/violated/disputed/unsupported/unexamined, where
#   every violation carries a stable rule ID and the smallest available witness,
#   and unexamined content is never reported as pass (evidence_truth_boundary);
#   enforce the read_only invariant by hashing the descriptor file and any
#   referenced source artifact before and after inspection (unchanged_bytes).
# Rationale: document-debugger spec deltas. No implicit OCR, no network access,
#   no writes: the module only reads bytes and computes hashes. Carrier locator
#   adapters (slice 2), comparators/counterexamples (slice 3) and a11y
#   (slice 4) are intentionally out of scope. No DSC core wire changes.
"""Read-only descriptor loader, inspection index and typed diagnostics (sunset-xx7.1)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from dsc03 import validator

__all__ = [
    "CATEGORIES",
    "DescriptorParseError",
    "Diagnostic",
    "InspectionIndex",
    "InspectionResult",
    "build_index",
    "diagnose",
    "inspect",
    "load_descriptor",
]

# typed_diagnostics invariant: exactly these result categories.
CATEGORIES = ("pass", "violated", "disputed", "unsupported", "unexamined")

# Stable rule ID prefixes: validator-derived codes keep the dsc03.* namespace;
# inspector-derived checks use the dbg.* namespace (stable across runs).
_RULE_ANNOTATION_DISPUTED = "dbg.annotation.disputed"
_RULE_ANNOTATION_UNSUPPORTED = "dbg.annotation.unsupported"
_RULE_INTERPRETATION_UNSUPPORTED = "dbg.interpretation.unsupported"
_RULE_COVERAGE_UNEXAMINED = "dbg.coverage.unexamined"
_RULE_COVERAGE_UNSUPPORTED = "dbg.coverage.unsupported"
_RULE_STRUCTURE_CHECKED = "dbg.structure.checked"


class DescriptorParseError(Exception):
    """The input file is not a parsable JSON document (parse_error state)."""


@dataclass(frozen=True)
class Diagnostic:
    """One typed inspection result.

    category is one of CATEGORIES; rule_id is stable; witness is the smallest
    available identifying link (element/edge/scope id), never None when a
    witness exists.
    """

    category: str
    rule_id: str
    witness: str | None = None
    message: str = ""

    def __post_init__(self):
        if self.category not in CATEGORIES:
            raise ValueError(f"invalid diagnostic category: {self.category!r}")


@dataclass
class InspectionIndex:
    """O(1)-ish by-id indexes over a loaded 0.3 descriptor (read-only views)."""

    descriptor: dict
    views: dict = field(default_factory=dict)
    regions: dict = field(default_factory=dict)
    contents: dict = field(default_factory=dict)
    relations: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)
    interpretations: dict = field(default_factory=dict)
    coverage: tuple = ()

    def region(self, region_id: str):
        return self.regions.get(region_id)

    def content(self, content_id: str):
        return self.contents.get(content_id)

    def annotation(self, annotation_id: str):
        return self.annotations.get(annotation_id)

    def relation(self, relation_id: str):
        return self.relations.get(relation_id)

    def containment(self, view_id: str | None = None) -> dict:
        """parent region id -> ordered tuple of contained region ids."""
        out: dict[str, list] = {}
        for r in self.relations.values():
            if r["kind"] != "contains":
                continue
            if view_id is not None:
                a, b = self.regions.get(r["from"]), self.regions.get(r["to"])
                if a is None or b is None or a["view_id"] != view_id:
                    continue
            out.setdefault(r["from"], []).append(r["to"])
        return {k: tuple(v) for k, v in out.items()}

    def reading_order_edges(self, view_id: str | None = None) -> tuple:
        """(from_region, to_region, interpretation_id) precedes edges."""
        out = []
        for r in self.relations.values():
            if r["kind"] != "precedes":
                continue
            if view_id is not None:
                a, b = self.regions.get(r["from"]), self.regions.get(r["to"])
                if a is None or b is None or a["view_id"] != view_id:
                    continue
            out.append((r["from"], r["to"], r["interpretation_id"]))
        return tuple(out)

    def evidence_for_content(self, content_id: str) -> tuple:
        """Evidence record ids attributing the given content id."""
        return tuple(
            e["id"]
            for e in self.evidence.values()
            if content_id in e["content_ids"]
        )

    def annotations_for(self, target_id: str) -> tuple:
        return tuple(
            a["id"] for a in self.annotations.values() if a["target"] == target_id
        )


@dataclass
class InspectionResult:
    """Outcome of one read-only inspection pass."""

    descriptor_path: Path
    descriptor_sha256: str
    source_sha256: str | None
    index: InspectionIndex
    diagnostics: tuple
    _unchanged: bool = True

    @property
    def unchanged_bytes(self) -> bool:
        """read_only invariant: input bytes identical before/after inspection."""
        return self._unchanged


def load_descriptor(path) -> dict:
    """Load and parse a descriptor document; raises DescriptorParseError on
    unparsable input. Validation outcome is reported separately by inspect()."""
    raw = Path(path).read_bytes()
    try:
        return validator.loads(raw.decode("utf-8"))
    except (validator.Duplicate, ValueError, json.JSONDecodeError, UnicodeError) as e:
        raise DescriptorParseError(str(e)) from e


def build_index(descriptor: dict) -> InspectionIndex:
    """Index a loaded descriptor by id for O(1)-ish lookup. Read-only."""
    idx = InspectionIndex(descriptor=descriptor)
    # sunset-xx7.4 (additive): tolerate malformed shapes so inspect() can emit
    # the classified dsc03.invalid_shape diagnostic instead of crashing —
    # missing sections index as empty, non-dict/id-less items are skipped and
    # left to the validator's invalid_shape classification (never silent pass).
    for key in ("views", "regions", "contents", "relations", "evidence",
                "annotations", "selectors", "interpretations"):
        items = descriptor.get(key) or []
        setattr(idx, key, {
            item["id"]: item for item in items
            if isinstance(item, dict) and "id" in item
        })
    idx.coverage = tuple(
        c for c in (descriptor.get("coverage") or [])
        if isinstance(c, dict) and "feature" in c and "scope" in c
        and "status" in c
    )
    return idx


def _minimal_witness(index: InspectionIndex, reason: str) -> str | None:
    """Smallest available witness for a validator-level reason code: scan
    relations first (they carry per-edge ids), then fall back to the
    descriptor id. Never invents a witness that is not in the document."""
    if reason == "dangling_reference":
        regions_contents = set(index.regions) | set(index.contents)
        evidence_ids = set(index.evidence)
        selector_ids = set(index.selectors)
        for r in index.relations.values():
            if r["from"] not in regions_contents or r["to"] not in regions_contents:
                return r["id"]
        for a in index.annotations.values():
            if any(x not in evidence_ids for x in a["evidence"]):
                return a["id"]
        for e in index.evidence.values():
            contents = set(index.contents)
            if any(x not in contents for x in e["content_ids"]) or any(
                x not in selector_ids for x in e["selector_ids"]
            ):
                return e["id"]
    # sunset-xx7.4 (additive): malformed descriptors may lack an id entirely;
    # witness is then None (no witness exists in the document — never invented).
    return index.descriptor.get("id")


def diagnose(index: InspectionIndex, validator_reasons) -> tuple:
    """Emit typed diagnostics for a loaded descriptor.

    - validator reason codes -> violated with rule_id dsc03.<code>
    - disputed annotations -> disputed (attributed claims, not auto-true)
    - asserted_without_evidence annotations/interpretations -> unsupported
    - unexamined coverage scopes -> unexamined
    - unsupported coverage features -> unsupported
    - a fully clean check yields exactly one pass diagnostic
    (unexamined content therefore can never be reported as pass).
    """
    diagnostics: list[Diagnostic] = []

    for code in validator_reasons:
        diagnostics.append(
            Diagnostic(
                category="violated",
                rule_id=f"dsc03.{code}",
                witness=_minimal_witness(index, code),
                message=f"validator outcome: {code}",
            )
        )

    for a in index.annotations.values():
        if a["status"] == "disputed":
            diagnostics.append(
                Diagnostic(
                    category="disputed",
                    rule_id=_RULE_ANNOTATION_DISPUTED,
                    witness=a["id"],
                    message="disputed annotation claim (attribution, not truth)",
                )
            )
        elif a["status"] == "asserted_without_evidence":
            diagnostics.append(
                Diagnostic(
                    category="unsupported",
                    rule_id=_RULE_ANNOTATION_UNSUPPORTED,
                    witness=a["id"],
                    message="annotation asserted without evidence",
                )
            )

    for i in index.interpretations.values():
        if i["status"] == "asserted_without_evidence":
            diagnostics.append(
                Diagnostic(
                    category="unsupported",
                    rule_id=_RULE_INTERPRETATION_UNSUPPORTED,
                    witness=i["id"],
                    message="interpretation asserted without evidence",
                )
            )

    for c in index.coverage:
        witness = f"{c['feature']}@{c['scope']}"
        if c["status"] == "unexamined":
            diagnostics.append(
                Diagnostic(
                    category="unexamined",
                    rule_id=_RULE_COVERAGE_UNEXAMINED,
                    witness=witness,
                    message="coverage scope not examined; never reported as pass",
                )
            )
        elif c["status"] == "unsupported":
            diagnostics.append(
                Diagnostic(
                    category="unsupported",
                    rule_id=_RULE_COVERAGE_UNSUPPORTED,
                    witness=witness,
                    message="coverage feature has no supporting adapter",
                )
            )

    if not any(d.category != "pass" for d in diagnostics):
        root = index.views[index.descriptor["views"][0]["id"]]["root"] if index.views else None
        diagnostics.append(
            Diagnostic(
                category="pass",
                rule_id=_RULE_STRUCTURE_CHECKED,
                witness=root or index.descriptor["id"],
                message="structural inspection found no findings",
            )
        )

    return tuple(diagnostics)


def _sha_of(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(path) -> InspectionResult:
    """Run one full read-only inspection pass over a descriptor file.

    Hashes the descriptor file and its referenced source artifact (if present
    on disk) before loading and re-hashes after indexing/diagnosis; the result
    exposes the unchanged_bytes property. This function never writes.
    """
    path = Path(path)
    descriptor_sha_before = hashlib.sha256(path.read_bytes()).hexdigest()
    source_path = None
    descriptor = load_descriptor(path)
    locator = descriptor.get("source", {}).get("locator")
    if locator:
        candidate = (path.parent / locator).resolve()
        if candidate.is_file():
            source_path = candidate
    source_sha_before = _sha_of(source_path) if source_path else None

    reasons = validator.validate(descriptor)
    index = build_index(descriptor)
    diagnostics = diagnose(index, reasons)

    # read_only invariant check: identical bytes after the full pass.
    unchanged = hashlib.sha256(path.read_bytes()).hexdigest() == descriptor_sha_before
    if source_path is not None:
        unchanged = unchanged and _sha_of(source_path) == source_sha_before

    return InspectionResult(
        descriptor_path=path,
        descriptor_sha256=descriptor_sha_before,
        source_sha256=source_sha_before,
        index=index,
        diagnostics=diagnostics,
        _unchanged=unchanged,
    )
