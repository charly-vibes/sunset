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


def replay(ev, descriptor, resolved_profiles):
    """Replay one evidence record against its descriptor.

    Returns (status, detail). Status is 'replayed' with resolved content ids and
    per-selector observations, or a typed failure: 'dangling_reference' (bound id
    does not resolve), 'unsupported_profile' (declared profile did not resolve),
    or 'invalid_selector' (malformed/out-of-bounds locator under a known profile).
    """
    contents_by_id = {c["id"]: c for c in descriptor["contents"]}
    selectors_by_id = {s["id"]: s for s in descriptor["selectors"]}
    detail = {"content_ids": list(ev.get("content_ids", [])), "observations": {}}
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
