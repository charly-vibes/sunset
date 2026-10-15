# Purpose: Consumer-side law fixtures for the document-context spec delta
#   (define-document-composition-semantics, sunset-905.2) — scoped semantic
#   context: attributed claims, inheritance vs direct observation, disputes,
#   deterministic replay, no truth laundering, no generic meaning union.
# Responsibilities: Provide (1) issue_fixture and dispute_fixture — synthetic
#   validated magazine descriptors whose claims are wire annotations
#   (target/term/value/origin/status/evidence), (2) claims_for and
#   claim_classification — attributed claim reading, publication context vs
#   narrated claim (publication_date), (3) inherited_bindings — bindings
#   inherited ONLY under a declared policy and ALWAYS marked "inherited",
#   never assigned automatically (quoted_author), (4) resolve_bindings —
#   incompatible active bindings stay DISPUTED unless a declared precedence
#   rule deterministically applies (context_dispute), (5) evaluate_claims +
#   canonically_equal_claims — deterministic replay on pinned inputs
#   (same_pinned_input), (6) uncertain_fixture + elected_winner — extractor
#   interpretations keep their disputed status and evidence; no winner is
#   elected (uncertain_ocr), (7) two_claim_parts + assembled_meaning —
#   assembly does not union semantic truth; composed meaning requires a
#   pinned domain rule (no_union_on_assembly). Synthetic, validated fixtures
#   only; classified outcomes, never exceptions; no real-carrier conformance
#   claims.
# Rationale: the deployed wire already carries attributed annotations
#   (origin/status/evidence) but has no context-resolution semantics; these
#   fixtures witness the proposed context laws machinery-side under
#   dsc03/substrate/ beside assembly.py (whose compose() the no-union law
#   reuses directly) — no wire change, no conformance claim.
"""Context laws: attributed claims, inheritance, disputes, replay, no union."""
import copy
import hashlib

from dsc03.substrate.laws import typed_check

# Terms that describe the PUBLICATION (issue metadata), not the narrated
# content; anything else observed on a content-bearing region is narrated.
METADATA_TERMS = {"mag:publication-date"}


def issue_fixture():
    """A validated magazine issue: an issue container, a poem and an article
    carrying a quote — with attributed claims as wire annotations.

    Claims:
    - a-issue-date   on r-issue   mag:publication-date  (publication context)
    - a-poem-theme   on r-poem    mag:theme             (the poem's own claim)
    - a-author       on r-article mag:author            (the article's author)
    The quote content c-quote carries NO annotation of its own.
    """
    return {
        "version": "0.3",
        "id": "ctx-issue",
        "source": {"format": "application/pdf",
                   "sha256": sha("ctx-issue-source"),
                   "locator": "urn:sub:magazine"},
        "views": [{"id": "v-log", "kind": "logical", "root": "r-issue"}],
        "regions": [
            {"id": "r-issue", "view_id": "v-log", "kind": "issue"},
            {"id": "r-poem", "view_id": "v-log", "kind": "poem"},
            {"id": "r-article", "view_id": "v-log", "kind": "article"},
        ],
        "contents": [
            {"id": "c-poem-text", "kind": "text", "value": "poem text"},
            {"id": "c-quote", "kind": "text", "value": "quoted line"},
        ],
        "relations": [
            {"id": "rel-i1", "kind": "contains", "from": "r-issue",
             "to": "r-poem"},
            {"id": "rel-i2", "kind": "contains", "from": "r-issue",
             "to": "r-article"},
            {"id": "rel-hc1", "kind": "has-content", "from": "r-poem",
             "to": "c-poem-text"},
            {"id": "rel-hc2", "kind": "has-content", "from": "r-article",
             "to": "c-quote"},
        ],
        "annotations": [
            {"id": "a-issue-date", "target": "r-issue",
             "term": "mag:publication-date", "value": "1991-03",
             "origin": "source", "status": "supported", "evidence": ["e-iss"],
             "view_id": "v-log"},
            {"id": "a-poem-theme", "target": "r-poem", "term": "mag:theme",
             "value": "sea", "origin": "source", "status": "supported",
             "evidence": ["e-poem"], "view_id": "v-log"},
            {"id": "a-author", "target": "r-article", "term": "mag:author",
             "value": "A. Poet", "origin": "source", "status": "supported",
             "evidence": ["e-auth"], "view_id": "v-log"},
        ],
        "evidence": [
            {"id": "e-iss", "origin": "source",
             "source_ref": "urn:sub:magazine#issue", "content_ids": [],
             "selector_ids": []},
            {"id": "e-poem", "origin": "source",
             "source_ref": "urn:sub:magazine#page:4",
             "content_ids": ["c-poem-text"], "selector_ids": []},
            {"id": "e-auth", "origin": "source",
             "source_ref": "urn:sub:magazine#page:4",
             "content_ids": ["c-quote"], "selector_ids": []},
        ],
        "vocabularies": [{"namespace": "mag", "version": "1"}],
        "selectors": [],
        "interpretations": [],
        "coverage": [],
        "profiles": [],
    }


def dispute_fixture():
    """issue_fixture with the issue date DISPUTED: an OCR reading (origin
    extracted, status disputed) and a manual reading (origin manual,
    status supported) both claim mag:publication-date on r-issue."""
    desc = issue_fixture()
    desc["id"] = "ctx-dispute"
    desc["annotations"] = [
        {"id": "a-date-ocr", "target": "r-issue",
         "term": "mag:publication-date", "value": "1991-04",
         "origin": "extracted", "status": "disputed", "evidence": ["e-d-ocr"],
         "view_id": "v-log"},
        {"id": "a-date-manual", "target": "r-issue",
         "term": "mag:publication-date", "value": "1991-03",
         "origin": "manual", "status": "supported", "evidence": ["e-d-man"],
         "view_id": "v-log"},
        desc["annotations"][1],
        desc["annotations"][2],
    ]
    desc["evidence"].extend([
        {"id": "e-d-ocr", "origin": "source",
         "source_ref": "urn:sub:magazine#cover", "content_ids": [],
         "selector_ids": []},
        {"id": "e-d-man", "origin": "source",
         "source_ref": "urn:sub:magazine#colophon", "content_ids": [],
         "selector_ids": []},
    ])
    return desc


def uncertain_fixture():
    """issue_fixture where the poem text carries TWO attributed
    transcriptions: an OCR one (extracted, disputed, declared transform
    lineage from the scanned image) and a manual one (supported). Neither
    is elected."""
    desc = issue_fixture()
    desc["id"] = "ctx-uncertain"
    desc["contents"] = [
        {"id": "c-scan-img", "kind": "image", "value": "poem page scan"},
        {"id": "c-poem-text", "kind": "text", "value": "poem text"},
        {"id": "c-quote", "kind": "text", "value": "quoted line"},
    ]
    desc["relations"] = [
        desc["relations"][0], desc["relations"][1],
        {"id": "rel-hc-s", "kind": "has-content", "from": "r-poem",
         "to": "c-scan-img"},
        {"id": "rel-hc1", "kind": "has-content", "from": "r-poem",
         "to": "c-poem-text"},
        {"id": "rel-hc2", "kind": "has-content", "from": "r-article",
         "to": "c-quote"},
        {"id": "rel-df-tr", "kind": "derived-from", "from": "e-ocr2",
         "to": "e-scan"},
    ]
    desc["annotations"] = [
        {"id": "a-ocr-trans", "target": "c-poem-text",
         "term": "mag:transcription", "value": "poem tekt",
         "origin": "extracted", "status": "disputed", "evidence": ["e-ocr2"],
         "view_id": "v-log"},
        {"id": "a-manual-trans", "target": "c-poem-text",
         "term": "mag:transcription", "value": "poem text",
         "origin": "manual", "status": "supported", "evidence": ["e-man2"],
         "view_id": "v-log"},
        {"id": "a-author", "target": "r-article", "term": "mag:author",
         "value": "A. Poet", "origin": "source", "status": "supported",
         "evidence": ["e-auth"], "view_id": "v-log"},
    ]
    desc["evidence"] = [
        {"id": "e-scan", "origin": "source",
         "source_ref": "urn:sub:magazine#page:4",
         "content_ids": ["c-scan-img"], "selector_ids": []},
        {"id": "e-ocr2", "origin": "extracted",
         "source_ref": "urn:sub:magazine#page:4",
         "content_ids": ["c-poem-text"], "selector_ids": [],
         "transform": {"id": "transcribe", "version": "1",
                       "config_sha256": sha("ctx-transcribe-config"),
                       "dependencies": ["ocr-sim"],
                       "inputs": ["c-scan-img"], "outputs": ["c-poem-text"]}},
        {"id": "e-man2", "origin": "source",
         "source_ref": "urn:sub:magazine#collation", "content_ids": [],
         "selector_ids": []},
        {"id": "e-auth", "origin": "source",
         "source_ref": "urn:sub:magazine#page:4",
         "content_ids": ["c-quote"], "selector_ids": []},
    ]
    return desc


def sha(label):
    """Honest synthetic digest: sha256 of the named synthetic payload."""
    return hashlib.sha256(label.encode()).hexdigest()


def _annotation(a):
    """Attributed claim record: target, term, value, origin, status,
    evidence — exactly the fields the claims_attributed invariant names."""
    return {"id": a["id"], "target": a["target"], "term": a["term"],
            "value": a["value"], "origin": a["origin"], "status": a["status"],
            "evidence": list(a["evidence"])}


def claims_for(desc, target):
    """Every attributed claim on one target, with its origin, status and
    evidence retained — unsupported and disputed claims stay visible."""
    return [_annotation(a) for a in desc["annotations"] if a["target"] == target]


def _binders(desc, content_id):
    return [r["from"] for r in desc["relations"]
            if r["kind"] == "has-content" and r["to"] == content_id]


def _contains_children(desc):
    out = {}
    for r in desc["relations"]:
        if r["kind"] == "contains":
            out.setdefault(r["from"], set()).add(r["to"])
    return out


def claim_classification(desc, annotation_id):
    """publication_context vs narrated_claim.

    A claim is publication context when it is metadata about a container
    region (an ancestor that binds no content itself); a claim on a
    content-bearing region is that region's own narrated claim. The issue
    date therefore stays ISSUE METADATA — it is never a date narrated by
    the poem.
    """
    ann = next(a for a in desc["annotations"] if a["id"] == annotation_id)
    children = _contains_children(desc)
    binds_content = any(r["kind"] == "has-content" and r["from"] == ann["target"]
                        for r in desc["relations"])
    if not binds_content and ann["term"] in METADATA_TERMS:
        return {"status": "publication_context", "target": ann["target"],
                "container_of": sorted(children.get(ann["target"], ()))}
    return {"status": "narrated_claim", "target": ann["target"]}


def inherited_bindings(desc, target, policy=None):
    """Bindings inherited onto target — ONLY when a declared policy permits.

    Default (no declared policy): [] — nothing is inherited automatically.
    With a policy (inherit_terms + along=contains), inherited bindings are
    collected from ancestor regions and ALWAYS marked provenance:
    "inherited" rather than directly observed.
    """
    if not policy:
        return []  # no automatic inheritance: quoted_author's core refusal
    terms = set(policy["inherit_terms"])
    ancestors = set()
    if target in {c["id"] for c in desc["contents"]}:
        ancestors.update(_binders(desc, target))
    children = _contains_children(desc)
    frontier = set(ancestors)
    while frontier:
        node = frontier.pop()
        parents = [src for src, kids in children.items() if node in kids]
        for p in parents:
            if p not in ancestors:
                ancestors.add(p)
                frontier.add(p)
    out = []
    for a in desc["annotations"]:
        if a["target"] in ancestors and a["term"] in terms:
            out.append({"term": a["term"], "value": a["value"],
                        "provenance": "inherited", "via_region": a["target"]})
    return sorted(out, key=lambda b: (b["via_region"], b["term"]))


def resolve_bindings(desc, term, target, precedence=None):
    """Shadow/conflict resolution: incompatible active bindings stay
    DISPUTED — both claims retained — unless a declared precedence rule
    deterministically applies (then the winner is recorded and the losing
    claims stay retained, never deleted).
    """
    claims = [a for a in desc["annotations"]
              if a["term"] == term and a["target"] == target]
    ids = sorted(a["id"] for a in claims)
    if not claims:
        return {"status": "unavailable", "claims": []}
    if len(claims) == 1:
        return {"status": "resolved", "winner": ids[0], "retained": ids}
    if not precedence:
        return {"status": "disputed", "claims": ids}
    prefer = precedence["prefer_origin"]
    winners = sorted(a["id"] for a in claims if a["origin"] == prefer)
    if not winners:
        return {"status": "disputed", "claims": ids,
                "reason": "no_claim_matches_precedence"}
    return {"status": "resolved", "winner": winners[0], "retained": ids,
            "policy": precedence["policy"]}


def evaluate_claims(desc):
    """Deterministic claim evaluation on a pinned input: same observations,
    scopes and rule version in -> same claim set out. The rule version is
    pinned by this module ("1"); the claim set is the canonical record of
    every attributed annotation, sorted by claim id.
    """
    claims = sorted((_annotation(a) for a in desc["annotations"]),
                    key=lambda c: c["id"])
    return {"rule_version": "1", "claims": claims}


def canonically_equal_claims(a, b):
    """Canonical equality for claim envelopes.

    Claim envelopes are not wire descriptors, so the deployed two-reader
    contract (dsc03.canonical: reader_a + reader_b, key-set checked against
    TOP_LEVEL) does not apply to them directly; replay equality is measured
    with reader_a's canonical bytes (the descriptor-level two-reader
    equality remains available via assembly.canonically_equal and is
    exercised by the assembly slice).
    """
    from dsc03 import canonical
    return canonical.reader_a(a) == canonical.reader_a(b)


def elected_winner(claims):
    """No truth laundering: with more than one attributed claim on a target
    no winner is elected — the claims keep their statuses (including
    disputed) and their evidence. Returns the winner id only when a single
    claim exists."""
    return claims[0]["id"] if len(claims) == 1 else None


def two_claim_parts():
    """Two assembly-compatible magazine parts, each attributing its OWN
    publication-date claim to its own poem region. Sources align; ids are
    disjoint; vocabulary namespaces match."""
    def part(n, value):
        return {
            "version": "0.3",
            "id": f"ctx-part-{n}",
            "source": {"format": "application/pdf",
                       "sha256": sha("ctx-parts-source"),
                       "locator": "urn:sub:magazine"},
            "views": [{"id": f"v-ctx-{n}", "kind": "logical",
                       "root": f"r-issue-{n}"}],
            "regions": [
                {"id": f"r-issue-{n}", "view_id": f"v-ctx-{n}",
                 "kind": "issue"},
                {"id": f"r-poem-{n}", "view_id": f"v-ctx-{n}",
                 "kind": "poem"},
            ],
            "contents": [{"id": f"c-ann-{n}", "kind": "text",
                          "value": f"poem {n}"}],
            "relations": [
                {"id": f"rel-iss-{n}", "kind": "contains",
                 "from": f"r-issue-{n}", "to": f"r-poem-{n}"},
                {"id": f"rel-hc-{n}", "kind": "has-content",
                 "from": f"r-poem-{n}", "to": f"c-ann-{n}"},
            ],
            "annotations": [{
                "id": f"a-date-{n}", "target": f"r-poem-{n}",
                "term": "mag:publication-date", "value": value,
                "origin": "source", "status": "supported",
                "evidence": [f"e-ann-{n}"], "view_id": f"v-ctx-{n}",
            }],
            "evidence": [{"id": f"e-ann-{n}", "origin": "source",
                          "source_ref": f"urn:sub:magazine#part:{n}",
                          "content_ids": [f"c-ann-{n}"],
                          "selector_ids": []}],
            "vocabularies": [{"namespace": "mag", "version": "1"}],
            "selectors": [], "interpretations": [], "coverage": [],
            "profiles": [],
        }
    return part(1, "1991-03"), part(2, "1991-04")


def assembled_meaning(desc):
    """no_generic_meaning_union: assembly composes REGIONS and their
    attributed claims; it does not union semantic truth. This check reports
    the composed claims exactly as attributed (each scoped to its own
    part's region — no merged claim, no shared target) and states that
    composed meaning would require a PINNED DOMAIN RULE, which none of the
    operands declares.
    """
    claims = [{"target": a["target"], "value": a["value"]}
              for a in desc["annotations"]]
    merged = [a for a in desc["annotations"]
              if a["term"] == "mag:publication-date"
              and a["target"] not in ("r-poem-1", "r-poem-2")]
    if merged:
        return {"status": "union_detected", "claims": claims,
                "merged_targets": sorted({a["target"] for a in merged})}
    return {"status": "no_generic_union",
            "reason": "requires_pinned_domain_rule", "claims": claims}
