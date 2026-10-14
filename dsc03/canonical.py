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


# -- reader A: generic recursive canonicalization ----------------------------------
def _canon_a(x):
    if isinstance(x, dict):
        return {k: _canon_a(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [_canon_a(v) for v in x]
    return x


def reader_a(descriptor):
    """Reader A: sort object keys recursively, preserve array order and text."""
    return json.dumps(
        _canon_a(descriptor), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


# -- reader B: independent top-level-driven emission ---------------------------------
def _item_bytes(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _section_bytes(x):
    if isinstance(x, list):
        return "[" + ",".join(_item_bytes(item) for item in x) + "]"
    return _item_bytes(x)


def reader_b(descriptor):
    """Reader B: emit each section through its own serializer, key-set checked
    against TOP_LEVEL, ordering fixed to the sorted-key canonical form."""
    if set(descriptor) != set(TOP_LEVEL):
        raise ValueError("descriptor keys do not match TOP_LEVEL")
    parts = []
    for key in sorted(descriptor):
        parts.append(json.dumps(key) + ":" + _section_bytes(descriptor[key]))
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
