# Purpose: Consumer-side partial assembly (A ⊕ B) for the document-assembly
#   spec delta — define-document-composition-semantics, sunset-905.1.
# Responsibilities: Provide compose() — a deterministic, partial operation
#   combining two "parts_ready" descriptors into one "assembled" descriptor or
#   a classified refusal (never an exception, never a silent merge): source
#   alignment, ID-namespace collision behavior (shared ID under identical
#   claims merges into a single identity; conflicting source or claims refuses
#   with the smallest known witness; vocabulary namespace version mismatch
#   refuses), reference resolution against the union, no invented edges or
#   ordering (only operand-declared edges are carried). Also empty_part() —
#   the assembly-layer identity element — and canonically_equal() — equality
#   under BOTH independent canonical readers from dsc03.canonical. Validated
#   synthetic fixtures only; this is machinery-level witnessing, NOT a
#   deployed-kernel conformance claim.
# Rationale: design §2 ("Part assembly is not morphism composition") and the
#   delta's assembly_compatible / assembly_identity / assembly_associative /
#   order_not_implicit / boundaries_preserved invariants. Placement: the
#   deployed kernel has no composition checker (restore-document-substrate
#   mapping.md, law 5 = partial), so the laws are witnessed harness-side under
#   dsc03/substrate/ beside the existing Mapping algebra — no wire change, no
#   conformance-label change.
"""Partial assembly: deterministic merge, classified refusal, laws."""
import copy

from dsc03.substrate.laws import TypedError, typed_check

# Sections merged per assembly; coverage entries are keyed by their validator
# uniqueness triple, everything else by id. Order matters for canonical bytes:
# left operand's items first (first occurrence wins), then the right's new ones.
_BY_ID = ("views", "regions", "contents", "relations", "annotations",
          "evidence", "selectors", "interpretations", "profiles")
_EMPTY_KEYS = _BY_ID + ("coverage",)
_COVERAGE_KEY = ("inventory_id", "feature", "scope")


def empty_part():
    """The assembly identity element: a scoped, structurally empty skeleton.

    The deployed 0.3 wire cannot represent a fully empty descriptor (a
    logical view with an existing root region is mandatory), so emptiness is
    defined at the assembly layer: a part carrying no regions, contents,
    relations, evidence, views or other scoped payload. compose() admits it
    without descriptor-level validation — there is nothing to validate —
    and returns the other operand unchanged up to canonical representation.
    """
    return {
        "version": "0.3", "id": "empty-part",
        "source": {"format": "", "sha256": "0" * 64, "locator": ""},
        "views": [], "regions": [], "contents": [], "relations": [],
        "annotations": [], "evidence": [], "vocabularies": [],
        "selectors": [], "interpretations": [], "coverage": [], "profiles": [],
    }


def is_empty(desc):
    return not any(desc[k] for k in _EMPTY_KEYS)


def canonically_equal(a, b):
    """Canonical equality: BOTH independent readers emit identical bytes.

    reader_a (generic sorted-key walk) and reader_b (independent top-level
    emission, key-set checked) must agree; disagreement is never collapsed
    into a winner.
    """
    from dsc03 import canonical
    return (canonical.reader_a(a) == canonical.reader_a(b)
            and canonical.reader_b(a) == canonical.reader_b(b))


def _ids(desc, sections):
    out = set()
    for s in sections:
        out.update(i["id"] for i in desc[s])
    return out


def _refused(rule, smallest, **detail):
    return {"status": "refused", "rule": rule, "smallest": sorted(smallest),
            "detail": detail}


def _merge_by_key(a_items, b_items, key_of, rule, section):
    """Left-first merge: identical records dedupe to a single identity,
    conflicting records refuse with the smallest witness (the key)."""
    merged, index = [], {}
    for item in a_items + b_items:
        k = key_of(item)
        if k not in index:
            index[k] = copy.deepcopy(item)
            merged.append(index[k])
        elif index[k] != item:
            return None, _refused(rule, [k if isinstance(k, str) else str(k)],
                                  section=section)
    return merged, None


def compose(a, b):
    """Assemble parts a and b (design §2: A ⊕ B, not morphism composition).

    Either operand may be a part descriptor or a prior compose() result —
    nested notation compose(compose(A,B),C) composes envelopes directly, and
    a refusal on either side propagates (composition of a refusal is refused,
    never a crash). Returns {"status": "assembled", "descriptor": d} or
    {"status": "refused", "rule": ..., "smallest": [...], "detail": {...}}.
    The empty part is the identity on either side. For non-empty operands:
    sources must agree; shared IDs must carry identical records (else refuse
    with the smallest witness); namespaces must be version-aligned; only
    operand-declared edges are carried (nothing is invented); the assembled
    result must validate (typed_check) — an invalid union refuses.
    """
    try:
        a = _operand(a)
        if a is None:
            return b  # b is already a refusal envelope — propagate
        b = _operand(b)
        if b is None:
            return a
        if is_empty(a):
            return {"status": "assembled", "descriptor": copy.deepcopy(b)}
        if is_empty(b):
            return {"status": "assembled", "descriptor": copy.deepcopy(a)}
        return _compose_nonempty(a, b)
    except TypedError as e:  # classified, by contract; never a crash
        return _refused("assembly_error", ["compose"], reason=str(e))


def _operand(x):
    """Unwrap a prior compose() result; None marks a refusal to propagate."""
    if isinstance(x, dict) and x.get("status") == "refused":
        return None
    if isinstance(x, dict) and "descriptor" in x:
        return x["descriptor"]
    return x


def _compose_nonempty(a, b):
    # 1. Source alignment: one source record per descriptor on this wire.
    if a["source"] != b["source"]:
        shared = _ids(a, _BY_ID) & _ids(b, _BY_ID)
        rule = "same_id_conflicting_source" if shared else "source_mismatch"
        return _refused(rule, shared if shared else ["source"],
                        source_a=a["source"]["sha256"],
                        source_b=b["source"]["sha256"])

    # 2. Namespace alignment: same namespace under different versions refuses.
    ns_a = {v["namespace"]: v["version"] for v in a["vocabularies"]}
    ns_b = {v["namespace"]: v["version"] for v in b["vocabularies"]}
    for ns in sorted(set(ns_a) & set(ns_b)):
        if ns_a[ns] != ns_b[ns]:
            return _refused("namespace_mismatch", [ns],
                            version_a=ns_a[ns], version_b=ns_b[ns])

    # 3. Section merge: shared ID with identical record → single identity.
    out = {"version": a["version"], "id": a["id"], "source": copy.deepcopy(a["source"])}
    out["vocabularies"] = copy.deepcopy(a["vocabularies"])
    for v in b["vocabularies"]:
        if v["namespace"] not in ns_a:
            out["vocabularies"].append(copy.deepcopy(v))
    for section in _BY_ID:
        merged, refusal = _merge_by_key(a[section], b[section],
                                        lambda i: i["id"],
                                        "same_id_conflicting_claims", section)
        if refusal:
            return refusal
        out[section] = merged
    merged, refusal = _merge_by_key(
        a["coverage"], b["coverage"],
        lambda c: tuple(c[k] for k in _COVERAGE_KEY),
        "same_id_conflicting_claims", "coverage")
    if refusal:
        return refusal
    out["coverage"] = merged

    # 4. The assembled union must itself be a valid descriptor.
    status, reasons = typed_check(out)
    if status != "accepted":
        return _refused("assembled_invalid", reasons, phase="union_validation")
    return {"status": "assembled", "descriptor": out}
