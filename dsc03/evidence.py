# Purpose: Evidence link replay for DSC 0.3 (sunset-r68.1.4).
# Responsibilities: Replay one evidence record — resolve its bound content and
#   selector ids, use the resolved (pinned) selector profile, and reproduce the
#   anchored observation by applying the profile-declared text-range grammar
#   (offset unit, endpoint convention) to the exact target value without
#   normalization; return typed outcomes (replayed / dangling_reference /
#   invalid_selector / unsupported_profile), never guessed interpretation.
# Rationale: add-dsc-03 document-evidence "Evidence link resolution" and
#   "Typed profile-defined source selectors". Byte-unit profiles and transform
#   replay arrive with later tickets (sunset-r68.2, sunset-r68 tasks 2.x/3.x).
"""Evidence replay: resolve the link, apply its anchors, report typed outcomes."""
from dsc03 import profiles


def replay(ev, descriptor, resolved_profiles, transform_fns=None, _visiting=None):
    """Replay one evidence record against its descriptor.

    Source links (no transform): resolve bound ids and reproduce each selector
    anchor's observation. Transform records: replay the inputs' producers, apply
    the pinned transform callable (registry keyed by config_sha256) to the exact
    input values, and require the result to equal the recorded output value —
    mismatches are 'replay_mismatch'; a missing callable is 'unreplayable', never
    guessed. Statuses: replayed / dangling_reference / unsupported_profile /
    invalid_selector / unreplayable / replay_mismatch / lineage_cycle.
    """
    transform_fns = transform_fns or {}
    _visiting = set() if _visiting is None else _visiting
    contents_by_id = {c["id"]: c for c in descriptor["contents"]}
    selectors_by_id = {s["id"]: s for s in descriptor["selectors"]}
    detail = {"content_ids": list(ev.get("content_ids", [])), "observations": {}}
    if "transform" in ev:
        if ev["id"] in _visiting:
            return "lineage_cycle", detail
        _visiting.add(ev["id"])
        t = ev["transform"]
        fn = transform_fns.get(t["config_sha256"])
        if fn is None:
            return "unreplayable", detail
        input_values = []
        for cid in t["inputs"]:
            if cid not in contents_by_id:
                return "dangling_reference", detail
            producer = next(
                (x for x in descriptor["evidence"] if cid in x.get("content_ids", [])),
                None,
            )
            if producer is None:
                return "dangling_reference", detail
            status_p, _ = replay(producer, descriptor, resolved_profiles, transform_fns, _visiting)
            if status_p != "replayed":
                return status_p, detail
            input_values.append(contents_by_id[cid]["value"])
        result = fn(input_values[0] if len(input_values) == 1 else input_values)
        for cid in t["outputs"]:
            if cid not in contents_by_id:
                return "dangling_reference", detail
            if result != contents_by_id[cid]["value"]:
                return "replay_mismatch", detail
            detail["observations"][cid] = result
            detail.setdefault("chain", []).append(cid)
        return "replayed", detail
    for cid in ev.get("content_ids", []):
        if cid not in contents_by_id:
            return "dangling_reference", detail
    for sid in ev.get("selector_ids", []):
        sel = selectors_by_id.get(sid)
        if sel is None:
            return "dangling_reference", detail
        status, artifact = resolved_profiles.get(sel["profile_id"], ("unsupported_profile", None))
        if status != "resolved":
            return "unsupported_profile", detail
        target = sel["target"]
        if target not in contents_by_id:
            return "dangling_reference", detail
        if sel["kind"] != "text-range":
            return "invalid_selector", detail  # only text-range replay is implemented
        value = contents_by_id[target]["value"]
        status_r, obs = profiles.apply_text_range(value, sel["locator"], artifact)
        if status_r != "selected":
            return "invalid_selector", detail
        detail["observations"][sid] = obs
    return "replayed", detail
