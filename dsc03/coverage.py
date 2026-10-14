# Purpose: Coverage inventory/manifest grammar and scoped disposition verification
#   for DSC 0.3 (sunset-r68.6, tasks.md 2.2 + 3.2).
# Responsibilities: Validate carrier-inventory and adapter-manifest profile
#   artifacts (exact shapes, minimum feature inventories per source format,
#   manifest features within the inventory, version/source_format agreement);
#   verify descriptor coverage: paired profile declarations, exactly one
#   disposition per (inventory, feature, scope), scope grammar matching the
#   feature's scope_kind, manifest membership for preserved/transformed/
#   approximated claims, one adapter run and configuration, enumeration
#   completeness (single `*` unexamined replacement when enumeration cannot
#   complete; empty domains reported as empty), and least-preserving feature
#   summaries (unexamined > unsupported > omitted > approximated > transformed >
#   preserved).
# Rationale: add-dsc-03 document-adapters "Independent coverage inventory" and
#   "Scoped coverage dispositions". Enumeration is injected per source; without
#   an enumerator that can complete, only the `*` unexamined form is accepted.
"""Scoped coverage verification: inventories, manifests, dispositions, summaries."""
import re

PAGE_SCOPE_RE = re.compile("page:(0|[1-9][0-9]*)")
INVENTORY_MINIMUMS = {
    "application/pdf": (
        ("pdf:glyphs", "pdf-page"), ("pdf:images", "pdf-page"),
        ("pdf:vectors", "pdf-page"), ("pdf:annotations", "pdf-page"),
        ("pdf:attachments", "document"),
    ),
    "application/epub+zip": (
        ("epub:manifest", "document"), ("epub:spine", "document"),
        ("epub:navigation", "document"), ("epub:resources", "epub-resource"),
    ),
    "application/json": (
        ("json:regions", "document"), ("json:contents", "document"),
        ("json:relations", "document"), ("json:evidence", "document"),
    ),
}
# least-preserving first
PRECEDENCE = ["unexamined", "unsupported", "omitted", "approximated", "transformed", "preserved"]
PRESERVING = {"preserved", "transformed", "approximated"}


def _artifact_errors(artifact, required, what):
    if not isinstance(artifact, dict) or set(artifact) != set(required):
        return [what]
    return []


def inventory_errors(artifact):
    errs = _artifact_errors(artifact, ["version", "source_format", "features"], "invalid_coverage_inventory")
    if errs:
        return errs
    if not (isinstance(artifact["version"], str) and artifact["version"]) or not (
        isinstance(artifact["source_format"], str) and artifact["source_format"]
    ):
        return ["invalid_coverage_inventory"]
    feats = artifact["features"]
    if not (isinstance(feats, list) and feats):
        return ["invalid_coverage_inventory"]
    names = set()
    for f in feats:
        if not isinstance(f, dict) or set(f) != {"name", "scope_kind"}:
            return ["invalid_coverage_inventory"]
        if f["scope_kind"] not in ("document", "pdf-page", "epub-resource"):
            return ["invalid_coverage_inventory"]
        n = f["name"]
        if not (isinstance(n, str) and n and ":" in n) or n in names:
            return ["invalid_coverage_inventory"]
        names.add(n)
    minimum = INVENTORY_MINIMUMS.get(artifact["source_format"])
    if minimum and not all(n in names and dict((f["name"], f["scope_kind"]) for f in feats)[n] == k for n, k in minimum):
        return ["invalid_coverage_inventory"]
    return []


def manifest_errors(artifact, inventory, inv_version, man_version, source_format):
    errs = _artifact_errors(
        artifact,
        ["version", "adapter_id", "adapter_version", "source_format", "features"],
        "invalid_coverage",
    )
    if errs:
        return errs
    if not all(isinstance(artifact[k], str) and artifact[k] for k in ("version", "adapter_id", "adapter_version", "source_format")):
        return ["invalid_coverage"]
    if artifact["version"] != man_version or artifact["version"] != inv_version:
        return ["invalid_coverage"]  # profile and artifact versions SHALL match
    if artifact["source_format"] != source_format:
        return ["invalid_coverage"]
    if inventory is not None and artifact["source_format"] != inventory["source_format"]:
        return ["invalid_coverage"]
    feats = artifact["features"]
    if not (isinstance(feats, list) and feats and all(isinstance(x, str) and x for x in feats)):
        return ["invalid_coverage"]
    if len(set(feats)) != len(feats):
        return ["invalid_coverage"]
    if inventory is not None:
        inv_names = {f["name"] for f in inventory["features"]}
        if not set(feats) <= inv_names:
            return ["invalid_coverage"]  # manifest features outside the inventory
    return []


def _least(statuses):
    best = "preserved"
    for s in statuses:
        if PRECEDENCE.index(s) < PRECEDENCE.index(best):
            best = s
    return best


def verify(descriptor, resolved_profiles, enumerator=None):
    """Verify scoped coverage. Returns a report dict:

    {"status": "verified"|"invalid", "reasons": sorted codes,
     "summaries": {feature: status}, "source_coverage": overall status}
    """
    reasons = set()
    errors = reasons.add
    inv_profiles = [p for p in descriptor["profiles"] if p.get("kind") == "carrier-inventory"]
    man_profiles = [p for p in descriptor["profiles"] if p.get("kind") == "adapter-manifest"]
    has_run = bool(descriptor["coverage"]) or inv_profiles or man_profiles
    if not has_run:
        # a descriptor without an adapter run MAY have neither, with empty coverage
        return {"status": "verified", "reasons": [], "summaries": {}, "source_coverage": "unexamined"}
    if len(inv_profiles) != 1 or len(man_profiles) != 1:
        errors("invalid_coverage")
        return {"status": "invalid", "reasons": sorted(reasons), "summaries": {}, "source_coverage": "unexamined"}
    inv_status, inventory = resolved_profiles.get(inv_profiles[0]["id"], ("unavailable", None))
    man_status, manifest = resolved_profiles.get(man_profiles[0]["id"], ("unavailable", None))
    if inv_status != "resolved" or man_status != "resolved":
        errors("unsupported_profile")
        return {"status": "invalid", "reasons": sorted(reasons), "summaries": {}, "source_coverage": "unexamined"}
    reasons.update(inventory_errors(inventory))
    reasons.update(manifest_errors(
        manifest, inventory, inv_profiles[0]["version"], man_profiles[0]["version"],
        descriptor["source"]["format"],
    ))
    if reasons:
        return {"status": "invalid", "reasons": sorted(reasons), "summaries": {}, "source_coverage": "unexamined"}

    inv_by_name = {f["name"]: f for f in inventory["features"]}
    manifest_features = set(manifest["features"])
    adapter_id = manifest["adapter_id"]
    adapter_version = manifest["adapter_version"]

    # group entries per (inventory_id, feature); validate entry-level rules
    entries = {}
    config_seen = set()
    ids_seen = set()
    for c in descriptor["coverage"]:
        key = (c["inventory_id"], c["feature"], c["scope"])
        if key in entries:
            errors("invalid_coverage")  # exactly one disposition per key
            continue
        entries[key] = c
        if c["inventory_id"] != inv_profiles[0]["id"] or c["manifest_id"] != man_profiles[0]["id"]:
            errors("invalid_coverage")
        feature = c["feature"]
        scope = c["scope"]
        fk = inv_by_name.get(feature, {}).get("scope_kind")
        if fk is None:
            errors("invalid_coverage")  # feature not in the inventory
        elif scope == "*":
            pass  # sentinel scope, validated by the enumeration branch
        elif fk == "document" and scope != "document":
            errors("invalid_coverage")
        elif fk == "pdf-page" and not PAGE_SCOPE_RE.fullmatch(scope):
            errors("invalid_coverage")
        elif fk == "epub-resource" and not (isinstance(scope, str) and scope.startswith("resource:")):
            errors("invalid_coverage")
        if c["adapter_id"] != adapter_id or c["adapter_version"] != adapter_version:
            errors("invalid_coverage")
        if c["config_sha256"] != "unavailable":
            config_seen.add(c["config_sha256"])
        if len(config_seen) > 1:
            errors("invalid_coverage")  # one adapter run, one configuration
        if c["status"] in PRESERVING and feature not in manifest_features:
            errors("invalid_coverage")
        if c["status"] == "preserved" and c["reason"]:
            pass  # reason optional for preserved
        ids_seen.add((feature, scope))

    # enumeration completeness + summaries
    summaries = {}
    overall = []
    for feature, f in inv_by_name.items():
        scopes = None
        if enumerator is not None:
            scopes = enumerator(descriptor["source"]["format"], f["scope_kind"])
        if scopes is None:
            # enumeration cannot be completed: exactly one `*` unexamined entry
            star = [c for (i, ft, sc), c in entries.items() if ft == feature and sc == "*"]
            finite = [sc for (i, ft, sc) in entries if ft == feature and sc != "*"]
            if len(star) == 1 and star[0]["status"] == "unexamined" and not finite:
                summaries[feature] = "unexamined"
            else:
                errors("invalid_coverage")
                summaries[feature] = "unexamined"
            overall.append(summaries[feature])
            continue
        if not scopes:
            summaries[feature] = "empty"  # enumerated empty domain, not observed content
            overall.append("empty")
            continue
        got = []
        for scope in scopes:
            c = entries.get((inv_profiles[0]["id"], feature, scope))
            if c is None:
                errors("invalid_coverage")  # a required scope's coverage is absent
                got.append("unexamined")
            else:
                got.append(c["status"])
        summaries[feature] = _least(got)
        overall.append(summaries[feature])
    source_coverage = _least(overall) if overall else "unexamined"
    status = "invalid" if reasons else "verified"
    return {"status": status, "reasons": sorted(reasons), "summaries": summaries, "source_coverage": source_coverage}
