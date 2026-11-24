# Purpose: Two independently implemented descriptor readers emitting canonical
#   bytes for DSC 0.3 (sunset-r68.12, task 5.2).
# Responsibilities: For the SAME valid DSC input, both readers preserve ids,
#   array order and exact text (including non-NFC text content values, which the
#   schema explicitly exempts from normalization) and emit identical canonical
#   bytes. reader_a canonicalizes by a generic recursive walk (object keys
#   sorted at every level, arrays kept in order). reader_b is written
#   independently: it walks the document top-level-by-top-level over the
#   TOP_LEVEL key list and re-emits each item with its own serializer; it never
#   reuses reader_a's walk. Roundtrip stability (parse canonical bytes ->
#   re-serialize -> identical bytes) is part of the contract.
# Rationale: add-dsc-03 document-conformance "Reader independence" — this tests
#   serialization determinism, not extraction quality.
"""Canonical-byte readers: two independent implementations, one output."""
import json

TOP_LEVEL = [
    "version", "id", "source", "regions", "contents", "relations", "annotations",
    "evidence", "vocabularies", "views", "selectors", "interpretations",
    "coverage", "profiles",
]


# Set-like sections per add-anchor-derived-identity design Decision 3. Only
# meaningful under a declared identity profile; relations are deliberately
# absent (sequence meaning lives in precedes relations, never array position).
_SET_LIKE_SECTIONS_A = frozenset(
    ("regions", "contents", "selectors", "evidence", "annotations",
     "coverage", "interpretations", "profiles")
)


def _declares_identity_profile(descriptor):
    """Same detection semantics as the validator: any declared profile entry
    whose kind is "identity" activates the identity-profile rules."""
    profiles = descriptor.get("profiles", [])
    return isinstance(profiles, list) and any(
        isinstance(p, dict) and p.get("kind") == "identity" for p in profiles
    )


# -- reader A: generic recursive canonicalization ----------------------------------
def _canon_a(x):
    if isinstance(x, dict):
        return {k: _canon_a(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [_canon_a(v) for v in x]
    return x


def reader_a(descriptor):
    """Reader A: sort object keys recursively, preserve array order and text.

    Under a declared identity profile, the top-level set-like sections of
    design Decision 3 are ordered ascending by record id (coverage by its
    uniqueness triple inventory_id/feature/scope) before the walk; nested
    arrays and the relations section keep array order."""
    sections = descriptor
    if _declares_identity_profile(descriptor):
        sections = dict(descriptor)
        for name in descriptor:
            if name in _SET_LIKE_SECTIONS_A and isinstance(descriptor[name], list):
                if name == "coverage":
                    sections[name] = sorted(
                        descriptor[name],
                        key=lambda c: (c["inventory_id"], c["feature"], c["scope"]),
                    )
                else:
                    sections[name] = sorted(descriptor[name], key=lambda r: r["id"])
    return json.dumps(
        _canon_a(sections), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


# -- reader B: independent top-level-driven emission ---------------------------------
def _item_bytes(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# reader_b's own view of the set-like sections (design Decision 3). Written
# independently of reader_a: this reader re-implements both the section list
# and the ordering rule rather than importing them.
_SET_LIKE_SECTIONS_B = [
    "regions", "contents", "selectors", "evidence", "annotations",
    "coverage", "interpretations", "profiles",
]


def _b_order_section(section, items):
    """reader_b's independent ordering rule: ascending id, or for coverage the
    ascending uniqueness triple (inventory_id, feature, scope). Non-identity
    descriptors never reach this."""
    ordered = list(items)
    if section == "coverage":
        ordered.sort(key=lambda c: (c["inventory_id"], c["feature"], c["scope"]))
    else:
        ordered.sort(key=lambda r: r["id"])
    return ordered


def _section_bytes(x, section=None, sort_sections=False):
    if isinstance(x, list):
        items = x
        if sort_sections and section in _SET_LIKE_SECTIONS_B:
            items = _b_order_section(section, x)
        return "[" + ",".join(_item_bytes(item) for item in items) + "]"
    return _item_bytes(x)


def reader_b(descriptor):
    """Reader B: emit each section through its own serializer, key-set checked
    against TOP_LEVEL, ordering fixed to the sorted-key canonical form.
    Under a declared identity profile (its own detection, same semantics as
    the validator: a profiles entry with kind "identity"), reader_b orders the
    set-like sections ascending by id / coverage triple."""
    if set(descriptor) != set(TOP_LEVEL):
        raise ValueError("descriptor keys do not match TOP_LEVEL")
    declared_identity = any(
        isinstance(p, dict) and p.get("kind") == "identity"
        for p in descriptor["profiles"]
    )
    parts = []
    for key in sorted(descriptor):
        parts.append(
            json.dumps(key)
            + ":"
            + _section_bytes(descriptor[key], key, sort_sections=declared_identity)
        )
    return ("{" + ",".join(parts) + "}").encode("utf-8")


def agree(descriptor):
    """True when both readers emit identical canonical bytes for one snapshot."""
    return reader_a(descriptor) == reader_b(descriptor)


def roundtrip_stable(reader=reader_a):
    """True when parsing the reader's own bytes and re-serializing is a fixpoint."""
    def check(descriptor):
        raw = reader(descriptor)
        reparsed = json.loads(raw.decode("utf-8"))
        return reader(reparsed) == raw

    return check
