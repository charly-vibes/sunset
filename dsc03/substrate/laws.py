# Purpose: Categorical law checks over DSC 0.3 descriptors for the
#   restore-document-substrate Stage B harness (sunset-7hs).
# Responsibilities: Provide (1) typed_check — a never-raising wrapper around
#   dsc03.validator returning classified rejection, (2) the transformation
#   algebra used by the composition laws — Mapping records declaring source/
#   target schemas, observable scope and loss scope, with compose() rejecting
#   scope-incompatible compositions before applying them, (3) observable
#   extraction (text and sign-column geometry), the sign-bearing-column
#   factorization counterexample and its verdicts, (4) the non-invention
#   scanner flagging derived observations rebound as source evidence, and
#   (5) equivalence_status refusing cross-carrier equivalence without a
#   declared alignment scope, plus (6) synthetic_sha — the shared honest
#   synthetic-digest helper used by the fixture builders. All instances are
#   validated descriptors;
#   failures are classified, never exceptions escaping to callers.
# Rationale: design §4 laws and document-categorical-model deltas; identity
#   uniqueness and canonical-serialization stability are delegated to
#   dsc03.validator + dsc03.canonical (two independent readers).
"""Law checks: typed edges, composition laws, non-invention, factorization."""
import copy
import hashlib

CORE_RELATIONS = {"contains", "precedes", "realizes", "has-content", "derived-from"}
EXPECTED_CORE_RULES = {
    "contains": ("regions", "regions"),
    "precedes": ("regions", "regions"),
    "realizes": ("regions", "regions"),
    "has-content": ("regions", "contents"),
    "derived-from": ("evidence", "evidence"),
}


class TypedError(Exception):
    """A classified, expected rejection (caught by callers; never a crash)."""


def typed_check(desc):
    """Validate a descriptor; returns ('accepted', []) or ('rejected', reasons).

    Parse/shape failures are classified too: this function never raises.
    """
    try:
        from dsc03 import validator
        reasons = validator.validate(desc)
    except Exception as e:  # noqa: BLE001 — classified, by contract
        return "rejected", [f"parse_error:{e}"]
    return ("accepted", []) if not reasons else ("rejected", reasons)


def synthetic_sha(label):
    """Honest synthetic digest: sha256 of the named synthetic payload.

    Fixture digests are never fabricated constants: they name the synthetic
    payload they digest, so provenance stays checkable (sunset-7hs tidy).
    """
    return hashlib.sha256(label.encode()).hexdigest()


# -- synthetic validated instances -------------------------------------------------

def synthetic_instance():
    """A minimal VALID 0.3 descriptor (physical + logical views, text content)."""
    return {
        "version": "0.3",
        "id": "substrate-instance",
        "source": {
            "format": "application/pdf",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "locator": "substrate-instance",
        },
        "views": [
            {"id": "v-phys", "kind": "physical", "root": "r-page"},
            {"id": "v-log", "kind": "logical", "root": "r-art"},
        ],
        "regions": [
            {"id": "r-page", "view_id": "v-phys", "kind": "page"},
            {"id": "r-art", "view_id": "v-log", "kind": "article"},
        ],
        "contents": [{"id": "c0", "kind": "text", "value": "alpha beta"}],
        "relations": [
            {"id": "rel-hc1", "kind": "has-content", "from": "r-page", "to": "c0"},
            {"id": "rel-hc2", "kind": "has-content", "from": "r-art", "to": "c0"},
        ],
        "annotations": [],
        "evidence": [{
            "id": "e0", "origin": "source", "source_ref": "urn:substrate:inst",
            "content_ids": ["c0"], "selector_ids": [],
        }],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "selectors": [],
        "interpretations": [],
        "coverage": [],
        "profiles": [],
    }


def sign_instances():
    """Two instances whose flattened text is identical but whose sign-bearing
    number sits in a different column (geometry x/width differ)."""
    a = synthetic_instance()
    a["id"] = "ledger-layout-a"
    a["regions"][0]["geometry"] = {
        "profile_id": "p-geo", "space": "page-pt", "x": 400, "y": 0, "width": 60,
        "height": 12,
    }
    a["profiles"] = [{"id": "p-geo", "kind": "geometry", "uri": "geometry.json",
                      "version": "1",
                      "sha256": hashlib.sha256(b"geometry").hexdigest()}]
    b = copy.deepcopy(a)
    b["id"] = "ledger-layout-b"
    b["regions"][0]["geometry"]["x"] = 100
    b["regions"][0]["geometry"]["width"] = 55
    return a, b


# -- typed transformation algebra ---------------------------------------------------

class Mapping:
    """A declared transformation: typed domain, observable scope, loss scope.

    observables: keys this mapping CLAIMS to preserve/produce meaningfully.
    loss: features present in inputs this mapping does not carry (no inverse
    is ever assumed; Mapping has no inverse attribute by design).
    """

    def __init__(self, mid, version, source, target, observables, loss, fn):
        self.mid = mid
        self.version = version
        self.source = source
        self.target = target
        self.observables = frozenset(observables)
        self.loss = frozenset(loss)
        self.fn = fn


SCHEMA_KIND = "descriptor-0.3"


def identity_mapping():
    return Mapping("identity", "1", SCHEMA_KIND, SCHEMA_KIND,
                   ("text", "sign-column"), (), lambda d: d)


def uppercase_mapping():
    def fn(d):
        out = copy.deepcopy(d)
        for c in out["contents"]:
            if c["kind"] == "text":
                c["value"] = c["value"].upper()
        return out
    return Mapping("uppercase", "1", SCHEMA_KIND, SCHEMA_KIND,
                   ("text",), (), fn)


def strip_mapping():
    def fn(d):
        out = copy.deepcopy(d)
        for c in out["contents"]:
            if c["kind"] == "text":
                c["value"] = " ".join(c["value"].split())
        return out
    return Mapping("strip-ws", "1", SCHEMA_KIND, SCHEMA_KIND,
                   ("text",), (), fn)


def flatten_mapping():
    """Text-only flattening: keeps text contents only; declares geometry,
    sign columns and annotations as lost. Never invertible."""
    def fn(d):
        texts = [c["value"] for c in d["contents"] if c["kind"] == "text"]
        return {
            "version": "0.3",
            "id": "flattened",   # per-instance identity is itself dropped
            "source": dict(d["source"]),
            "views": [{"id": "v-log", "kind": "logical", "root": "r-art"}],
            "regions": [{"id": "r-art", "view_id": "v-log", "kind": "article"}],
            "contents": [{"id": f"c{i}", "kind": "text", "value": t}
                         for i, t in enumerate(texts)],
            "relations": [{"id": f"rel-hc{i}", "kind": "has-content",
                           "from": "r-art", "to": f"c{i}"}
                          for i in range(len(texts))],
            "annotations": [], "evidence": [], "vocabularies": [{"namespace": "ex", "version": "1"}],
            "selectors": [], "interpretations": [], "coverage": [], "profiles": [],
        }
    return Mapping("text-only-flatten", "1", SCHEMA_KIND, SCHEMA_KIND,
                   ("text",), ("sign-column", "geometry", "annotations"), fn)


def stray_mapping():
    """A mapping whose TARGET schema is not SCHEMA_KIND (incompatible pair)."""
    return Mapping("stray", "1", SCHEMA_KIND, "tokens", ("text",), (), lambda d: d)


def compose(g, f):
    """Compose typed mappings f: A→B then g: B→C; reject before applying when
    scopes do not match. Loss propagates (union). Provenance carries via ids."""
    if f.target != g.source:
        raise TypedError(
            f"incompatible_composition: {f.mid}:{f.target} -> {g.mid}:{g.source}")

    def fn(x):
        return g.fn(f.fn(x))
    return Mapping(f"{g.mid}o{f.mid}", "1", f.source, g.target,
                   f.observables & g.observables, f.loss | g.loss, fn)


# -- observables ---------------------------------------------------------------------

def observable(desc, key):
    if key == "text":
        return tuple(c["value"] for c in desc["contents"] if c["kind"] == "text")
    if key == "sign-column":
        return tuple(
            (r["geometry"]["x"], r["geometry"]["width"])
            for r in desc["regions"] if "geometry" in r
        )
    if key == "geometry":
        return tuple(
            (r["id"], r["geometry"])
            for r in desc["regions"] if "geometry" in r
        )
    if key == "annotations":
        return tuple(sorted(a["term"] for a in desc["annotations"]))
    raise TypedError(f"unknown_observable:{key}")


def factorization_verdict(mapping, a, b):
    """Failure-of-factorization witness (design §4).

    If a and b flatten to identical text but differ in a semantically essential
    sign-bearing column, the verdict is:
    - 'claimed_illegitimately' — the mapping claims an observable that differs
      between the instances yet is not declared lost;
    - 'loss_declared' — every differing observable is in the mapping's loss
      scope (the honest text-only case);
    - 'not_applicable' — the flattening does not even produce identical text.
    """
    ta, tb = mapping.fn(a), mapping.fn(b)
    try:
        same_text = observable(ta, "text") == observable(tb, "text")
    except TypedError:
        same_text = None
    if not same_text:
        return "not_applicable"
    for key in sorted(mapping.observables):
        if observable(a, key) != observable(b, key) and key not in mapping.loss:
            return "claimed_illegitimately"
    for key in sorted(mapping.loss):
        if observable(a, key) != observable(b, key):
            return "loss_declared"
    return "loss_declared"


def text_only_mapping():
    return flatten_mapping()


def sign_claiming_mapping():
    """The dishonest variant: the same flattening behavior, but claiming the
    sign-bearing column survives. Refuted by the counterexample verdict."""
    m = flatten_mapping()
    return Mapping(m.mid, m.version, m.source, m.target,
                   ("text", "sign-column"), (), m.fn)


# -- non-invention -------------------------------------------------------------------

def non_invention_violations(desc):
    """Flag derived observations (outputs of a transform) that any evidence
    record presents as direct source observations (origin == 'source')."""
    derived = set()
    for e in desc["evidence"]:
        if "transform" in e:
            derived.update(e["transform"]["outputs"])
    violations = []
    for e in desc["evidence"]:
        if e["origin"] == "source" and derived & set(e["content_ids"]):
            violations.append(f"derived_marked_as_source:{e['id']}")
    return sorted(violations)


# -- conditional cross-carrier equivalence --------------------------------------------

def equivalence_status(a, b, alignment=None):
    """Cross-carrier equivalence is never assumed: without a declared
    alignment relation and scope the outcome is 'unsupported' — matching ids,
    titles or filenames prove nothing. With a declared scope, only the
    observables inside that scope are compared."""
    if not alignment or "scope" not in alignment:
        return {"status": "unsupported",
                "reason": "no_declared_alignment_relation_and_scope"}
    scope = tuple(alignment["scope"])
    agreed = tuple(k for k in scope if observable(a, k) == observable(b, k))
    return {"status": "compared", "scope": scope, "agreed": agreed}
