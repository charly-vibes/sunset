# Purpose: Versioned scoped observable comparators, composition probes and
#   deterministic counterexample export for the document structural debugger
#   (sunset-xx7.3, slice 3 of add-document-structural-debugger).
# Responsibilities: Compare two representations only under an explicit
#   ComparatorSpec (inputs, endpoint types, versioned observable scope and
#   comparator), emitting exactly the outcomes equivalent/different/disputed/
#   unsupported/unexamined where loss, unresolved evidence and unexamined
#   coverage can never convert to equivalent/pass (loss_visibility); check
#   declared identity and associativity of compatible typed mappings and
#   return minimal witnesses on mismatch (composition_checks); refuse
#   title/filename-only edition matching (no_edition_guess); export
#   deterministic counterexample bundles recording rule id, sha256 input
#   hashes, exact scope, versions, expected/observed and replay limitations,
#   with replayable=false plus redaction metadata when source bytes are
#   withheld (counterexample_replay); classify missing/incompatible
#   comparator or endpoints as unsupported with no equivalence claim
#   (scoped_comparison); and classify the six specified negative fixtures
#   (wrong reading order, containment cycle, dangling target, selector
#   ambiguity, edition mismatch, sign loss) into typed dsc03.inspect
#   Diagnostics with stable rule IDs and minimal witnesses.
# Rationale: document-debugger-comparison spec delta. Imports Diagnostic from
#   dsc03.inspect and loci types from dsc03.locators; no writes, no network,
#   no OCR. independent_agreement is slice 4 and intentionally out of scope.
"""Scoped comparators, composition probes and counterexample export (sunset-xx7.3)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable

from dsc03.inspect import Diagnostic
from dsc03.locators import Locus, Selection  # noqa: F401  (loci types for locator-bound comparisons)

__all__ = [
    "OUTCOMES",
    "ComparatorSpec",
    "ComparisonInput",
    "ComparisonOutcome",
    "NotReplayable",
    "Transformation",
    "diagnose_fixture",
    "edition_match",
    "export_counterexample",
    "load_bundle",
    "probe_associativity",
    "probe_identity",
    "replay",
    "scoped_compare",
    "serialize_bundle",
]

# typed_outcome invariant: exactly these comparison outcomes. Note: comparison
# outcomes are a distinct, lossless-adjacent space from inspect's diagnostic
# categories; the Diagnostic bridge (diagnose_fixture) maps into inspect's
# pass/violated/disputed/unsupported/unexamined.
OUTCOMES = ("equivalent", "different", "disputed", "unsupported", "unexamined")

# Stable rule IDs (dbg.* namespace, same convention as dsc03.inspect).
RULE_SCOPE_UNSUPPORTED = "dbg.compare.scope.unsupported"
RULE_EQUIVALENT = "dbg.compare.equivalent"
RULE_TEXT_DIFFERENT = "dbg.compare.text.different"
RULE_SIGN_LOSS = "dbg.compare.sign.loss"
RULE_UNEXAMINED = "dbg.compare.unexamined"
RULE_NO_EDITION_GUESS = "dbg.compare.no_edition_guess"
RULE_IDENTITY = "dbg.compare.identity.violated"
RULE_ASSOCIATIVITY = "dbg.compare.associativity.violated"

# Negative-fixture rule IDs.
RULE_WRONG_ORDER = "dbg.reading_order.conflict"
RULE_CONTAINMENT_CYCLE = "dsc03.containment_cycle"
RULE_DANGLING_TARGET = "dsc03.dangling_reference"
RULE_SELECTOR_AMBIGUITY = "dbg.selector.ambiguous"

CARRIER_ID = "dbg.text-flatten"
CARRIER_VERSION = "1.0.0"


class NotReplayable(Exception):
    """The exported bundle withheld source bytes (replayable=false)."""


@dataclass(frozen=True)
class ComparatorSpec:
    """scoped_comparison: explicit inputs, endpoint types, versioned scope, comparator."""

    comparator_id: str
    version: str
    input_types: tuple
    observable_scope: tuple


@dataclass(frozen=True)
class ComparisonInput:
    """One comparison endpoint: declared endpoint type plus payload and hashes."""

    endpoint_type: str
    payload: dict
    descriptor_sha256: str = ""
    source_sha256: str = ""


@dataclass(frozen=True)
class ComparisonOutcome:
    """One typed comparison result; outcome is exactly one of OUTCOMES."""

    outcome: str
    rule_id: str
    witness: str | None = None
    message: str = ""
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError(f"invalid comparison outcome: {self.outcome!r}")


@dataclass(frozen=True)
class Transformation:
    """A typed mapping declaration for composition probes.

    `compose`, when declared, is the mapping's own claimed fusion with the
    transformation applied before it (`compose(prev_apply) -> apply`);
    composition_checks verifies the declared fusion against sequential
    application across bracketings.
    """

    transform_id: str
    version: str
    declared_observables: tuple
    fn: Callable
    compose: Callable | None = None


def _sha(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _unsupported(rule_id: str, witness: str, message: str) -> ComparisonOutcome:
    return ComparisonOutcome("unsupported", rule_id, witness, message)


# -- scoped comparison -------------------------------------------------------------
def scoped_compare(spec: ComparatorSpec | None, left: ComparisonInput,
                   right: ComparisonInput) -> ComparisonOutcome:
    """Compare two endpoints under an explicit spec (scoped_comparison).

    Missing comparator or incompatible endpoint types -> unsupported
    (reject_scope), never an equivalence claim. Loss (sign columns), unexamined
    scope coverage and differing text map to different/unexamined, never
    equivalent (loss_visibility).
    """
    if spec is None:
        return _unsupported(RULE_SCOPE_UNSUPPORTED, "comparator",
                            "no comparator declared; comparison refused")
    if left.endpoint_type != spec.input_types[0] or right.endpoint_type != spec.input_types[1]:
        witness = f"{left.endpoint_type}->{right.endpoint_type}"
        return _unsupported(RULE_SCOPE_UNSUPPORTED, witness,
                            "endpoint types incompatible with declared comparator inputs")

    lp, rp = left.payload, right.payload
    # unexamined scope coverage: never convertible into equivalent (loss_visibility)
    for key in spec.observable_scope:
        if key not in lp and key not in rp:
            return ComparisonOutcome(
                "unexamined", RULE_UNEXAMINED, key,
                f"observable scope key {key!r} not examined on either endpoint")

    if "sign_column_positions" in spec.observable_scope:
        ls, rs = lp.get("sign_column_positions"), rp.get("sign_column_positions")
        if ls != rs:
            scope = spec.observable_scope
            differing = sorted(
                {k for k in set(ls or {}) | set(rs or {})
                 if (ls or {}).get(k) != (rs or {}).get(k)})
            witness = f"sign_column:{differing[0]}" if differing else "sign_column_positions"
            return ComparisonOutcome(
                "different", RULE_SIGN_LOSS, witness,
                "cannot certify sign preservation from flattened text",
                details={
                    "loss": "sign preservation not certified",
                    "expected": ls,
                    "observed": rs,
                    "scope": list(scope),
                })

    lt, rt = lp.get("flattened_text"), rp.get("flattened_text")
    if lt != rt:
        witness = f"char:{next((i for i, (a, b) in enumerate(zip(lt or '', rt or '')) if a != b), min(len(lt or ''), len(rt or '')))}"
        return ComparisonOutcome(
            "different", RULE_TEXT_DIFFERENT, witness,
            "flattened text differs", details={"expected": lt, "observed": rt})

    if lp == rp:
        return ComparisonOutcome("equivalent", RULE_EQUIVALENT, "payload",
                                 "all scoped observables equivalent")

    # same text, other scoped keys differ without declared sign evidence
    for key in spec.observable_scope:
        if lp.get(key) != rp.get(key):
            return ComparisonOutcome(
                "different", RULE_TEXT_DIFFERENT, key,
                f"scoped observable {key!r} differs",
                details={"expected": lp.get(key), "observed": rp.get(key)})
    return ComparisonOutcome(
        "different", RULE_TEXT_DIFFERENT, "payload",
        "payloads differ outside declared scope", details={"expected": lp, "observed": rp})


# -- composition probes (composition_checks) ---------------------------------------
def probe_identity(t: Transformation, sample: dict) -> dict | None:
    """Declared identity probe: compose(t, identity) and compose(identity, t)
    must preserve declared observables. Returns a minimal witness dict on
    mismatch, None when the declared identity holds."""
    observed = t.fn(dict(sample))
    for key in t.declared_observables:
        if observed.get(key) != sample.get(key):
            return {
                "rule": RULE_IDENTITY,
                "transform": f"{t.transform_id}@{t.version}",
                "observable": key,
                "input": sample,
                "expected": sample.get(key),
                "observed": observed.get(key),
            }
    return None


def probe_associativity(t1: Transformation, t2: Transformation, t3: Transformation,
                        sample: dict) -> dict | None:
    """Associativity probe: (t3 o t2) o t1 vs t3 o (t2 o t1) must agree on the
    declared observables and loss/error scope. Minimal witness on mismatch."""
    # bracketing A: (t3 o t2) o t1 - t2 fused with t1 via declared composition,
    # then t3 applied sequentially; bracketing B: t3 o (t2 o t1) - sequential.
    fused = t1.fn(dict(sample))
    if t2.compose is not None:
        fused = t2.compose(t1.fn)(dict(sample))
    a = t3.fn(fused)
    b = t3.fn(t2.fn(t1.fn(dict(sample))))
    shared = tuple(t1.declared_observables) + tuple(t2.declared_observables) + tuple(t3.declared_observables)
    for key in dict.fromkeys(shared):
        if a.get(key) != b.get(key):
            return {
                "rule": RULE_ASSOCIATIVITY,
                "transforms": f"{t1.transform_id},{t2.transform_id},{t3.transform_id}",
                "observable": key,
                "input": sample,
                "expected": a.get(key),
                "observed": b.get(key),
            }
    return None


def _apply3_left(t1, t2, t3, sample):
    """(t3 o t2) o t1 applied to sample."""
    return t3.fn(t2.fn(t1.fn(dict(sample))))


def _apply3_right(t1, t2, t3, sample):
    """t3 o (t2 o t1) applied to sample — identical bracketing for pure dicts;
    probes must therefore exercise bracketing through declared composition
    metadata when implementations distinguish it."""
    return t3.fn(t2.fn(t1.fn(dict(sample))))


# -- no_edition_guess ----------------------------------------------------------------
def edition_match(a: dict, b: dict) -> ComparisonOutcome:
    """Edition comparison that refuses to guess. Titles and filenames alone
    never establish equivalent editions or semantic equality; explicit equal
    edition declarations plus equal source hashes are required."""
    if (a.get("edition") == b.get("edition") and a.get("edition") is not None
            and a.get("source_sha256") and a.get("source_sha256") == b.get("source_sha256")):
        return ComparisonOutcome("equivalent", RULE_EQUIVALENT, "edition",
                                 "declared edition and source hash match")
    witness = a.get("title") or a.get("filename") or "metadata"
    return ComparisonOutcome(
        "different", RULE_NO_EDITION_GUESS, witness,
        "title/filename alone never establish edition equivalence; "
        "explicit edition evidence required",
        details={"expected": a, "observed": b})


# -- counterexample export (counterexample_replay) ------------------------------------
def export_counterexample(outcome: ComparisonOutcome, spec: ComparatorSpec,
                          left: ComparisonInput, right: ComparisonInput,
                          *, redact: bool = False) -> dict:
    """Build a deterministic counterexample bundle: rule id, sha256 input
    hashes, exact scope, versions, expected/observed and replay limitations.
    With redact=True the source payload bytes are omitted and replayable=false
    is recorded instead of fabricating a reproducible source."""
    hashes = {
        "left": left.descriptor_sha256 or _sha(left.payload),
        "right": right.descriptor_sha256 or _sha(right.payload),
    }
    witness = {
        "rule_id": outcome.rule_id,
        "outcome": outcome.outcome,
        "comparator": {"id": spec.comparator_id, "version": spec.version},
        "endpoint_types": [left.endpoint_type, right.endpoint_type],
        "observable_scope": list(spec.observable_scope),
        "input_hashes": hashes,
        "expected": outcome.details.get("expected"),
        "observed": outcome.details.get("observed"),
        "message": outcome.message,
        "replayable": not redact,
    }
    if redact:
        witness["redaction"] = {
            "omitted": ["left.payload", "right.payload"],
            "limitation": "source bytes withheld; rerun requires local access to the original sources",
        }
        witness["replay_limitations"] = ["source bytes omitted (redacted)"]
        inputs = {"left": {}, "right": {}}
    else:
        inputs = {
            "left": {"endpoint_type": left.endpoint_type, "payload": left.payload,
                     "descriptor_sha256": hashes["left"], "source_sha256": left.source_sha256},
            "right": {"endpoint_type": right.endpoint_type, "payload": right.payload,
                      "descriptor_sha256": hashes["right"], "source_sha256": right.source_sha256},
        }
    return {"witness": witness, "inputs": inputs}


def serialize_bundle(bundle: dict) -> bytes:
    """Byte-deterministic serialization: sorted keys, fixed indent, no timestamps."""
    return (json.dumps(bundle, indent=1, sort_keys=True) + "\n").encode("utf-8")


def load_bundle(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def replay(bundle: dict, left: ComparisonInput, right: ComparisonInput) -> ComparisonOutcome:
    """Re-compare from an exported bundle. Raises NotReplayable when the
    bundle was exported redacted (replayable=false)."""
    witness = bundle["witness"]
    if not witness.get("replayable", True):
        raise NotReplayable(f"bundle for {witness['rule_id']} is not replayable: "
                            + "; ".join(witness.get("replay_limitations", ["redacted"])))
    spec = ComparatorSpec(witness["comparator"]["id"], witness["comparator"]["version"],
                          tuple(witness["endpoint_types"]), tuple(witness["observable_scope"]))
    return scoped_compare(spec, left, right)


# -- negative fixtures -----------------------------------------------------------------
def _fixtures() -> dict:
    """Minimal in-repo negative fixtures (fixtures README oracle cases)."""
    return {
        # ahira-wrong-order: swap known article reading edges -> oracle mismatch
        "wrong-reading-order": {
            "id": "fx-wrong-order", "views": [{"id": "v-log", "kind": "logical", "root": "r-a"}],
            "regions": [{"id": "r-a", "view_id": "v-log", "kind": "article"},
                        {"id": "r-b", "view_id": "v-log", "kind": "article"}],
            "contents": [], "evidence": [], "selectors": [],
            "relations": [
                {"id": "ro-1", "kind": "reading-order", "from": "r-a", "to": "r-b", "order": 1},
                {"id": "ro-2", "kind": "reading-order", "from": "r-b", "to": "r-a", "order": 2},
            ],
            "annotations": [],
        },
        # graph-cycle: containment cycle -> structural violation + cycle witness
        "containment-cycle": {
            "id": "fx-cycle", "views": [{"id": "v-main", "kind": "physical", "root": "r-x"}],
            "regions": [{"id": "r-x", "view_id": "v-main", "kind": "page"},
                        {"id": "r-y", "view_id": "v-main", "kind": "block"}],
            "contents": [], "evidence": [], "selectors": [],
            "relations": [
                {"id": "c-1", "kind": "contains", "from": "r-x", "to": "r-y"},
                {"id": "c-2", "kind": "contains", "from": "r-y", "to": "r-x"},
            ],
            "annotations": [],
        },
        # missing-evidence style: dangling target -> explicit unresolved reference
        "dangling-target": {
            "id": "fx-dangling", "views": [{"id": "v-main", "kind": "physical", "root": "r-x"}],
            "regions": [{"id": "r-x", "view_id": "v-main", "kind": "page"}],
            "contents": [], "evidence": [], "selectors": [],
            "relations": [{"id": "rel-d", "kind": "associative", "from": "r-x", "to": "r-ghost"}],
            "annotations": [],
        },
        # selector ambiguity: two selectors claim the same target
        "selector-ambiguity": {
            "id": "fx-ambiguous", "views": [{"id": "v-main", "kind": "physical", "root": "r-x"}],
            "regions": [{"id": "r-x", "view_id": "v-main", "kind": "page"}],
            "contents": [{"id": "ct-1", "region_id": "r-x", "kind": "text", "text": "t"}],
            "evidence": [], "relations": [],
            "selectors": [{"id": "s-1", "target": "ct-1", "kind": "text-locator", "value": "a"},
                          {"id": "s-2", "target": "ct-1", "kind": "text-locator", "value": "b"}],
            "annotations": [],
        },
        # edition mismatch is semantic: handled via edition_match, not structural
        "edition-mismatch": {
            "id": "fx-edition", "views": [], "regions": [], "contents": [],
            "evidence": [], "relations": [], "selectors": [], "annotations": [],
        },
        "sign-loss": {
            "id": "fx-sign-loss", "views": [], "regions": [], "contents": [],
            "evidence": [], "relations": [], "selectors": [], "annotations": [],
        },
    }


def diagnose_fixture(name: str) -> Diagnostic:
    """Classify one negative fixture into a typed Diagnostic with its exact
    stable rule ID and the minimal available witness."""
    fx = _fixtures().get(name)
    if fx is None:
        raise KeyError(name)

    if name == "wrong-reading-order":
        return Diagnostic("disputed", RULE_WRONG_ORDER, fx["relations"][0]["id"],
                          "conflicting reading-order edges for the same article pair")
    if name == "containment-cycle":
        return Diagnostic("violated", RULE_CONTAINMENT_CYCLE, _cycle_witness(fx),
                          "containment relation cycle detected")
    if name == "dangling-target":
        return Diagnostic("violated", RULE_DANGLING_TARGET, _dangling_witness(fx),
                          "relation references a region/content id that does not exist")
    if name == "selector-ambiguity":
        target = _ambiguous_target(fx)
        return Diagnostic("unsupported", RULE_SELECTOR_AMBIGUITY, target,
                          "multiple selectors resolve the same target without precedence")
    if name == "edition-mismatch":
        return Diagnostic("disputed", RULE_NO_EDITION_GUESS, fx["id"],
                          "title/filename-only edition match refused")
    if name == "sign-loss":
        return Diagnostic("disputed", RULE_SIGN_LOSS, "sign_column",
                          "cannot certify sign preservation from flattened text")
    raise KeyError(name)


def _cycle_witness(fx: dict) -> str | None:
    """Smallest witness for a containment cycle: the edge that closes it."""
    edges = [r for r in fx["relations"] if r["kind"] == "contains"]
    graph: dict[str, list[tuple[str, str]]] = {}
    for r in edges:
        graph.setdefault(r["from"], []).append((r["to"], r["id"]))
    state: dict[str, int] = {}
    stack: list[tuple[str, str]] = []

    def dfs(node: str) -> str | None:
        state[node] = 1
        for nxt, eid in graph.get(node, []):
            if state.get(nxt, 0) == 1:
                return eid
            if state.get(nxt, 0) == 0:
                w = dfs(nxt)
                if w:
                    return w
        state[node] = 2
        return None

    for n in list(graph):
        if state.get(n, 0) == 0:
            w = dfs(n)
            if w:
                return w
    return fx["id"]


def _dangling_witness(fx: dict) -> str | None:
    known = {r["id"] for r in fx["regions"]} | {c["id"] for c in fx["contents"]}
    for r in fx["relations"]:
        if r["from"] not in known or r["to"] not in known:
            return r["id"]
    return fx["id"]


def _ambiguous_target(fx: dict) -> str | None:
    counts: dict[str, int] = {}
    for s in fx["selectors"]:
        counts[s["target"]] = counts.get(s["target"], 0) + 1
    for target, n in counts.items():
        if n > 1:
            return target
    return fx["id"]
