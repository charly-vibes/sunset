"""Verifier contract and pinned registry (design decision 5).

Each verifier declares id, version, digest and applicable types, and its
`check` returns {outcome, reason_code} as a pure function of the claim and
the descriptor facts passed to it — no network, no clock, no randomness.
"""
import hashlib
import math

from dsc03.claims import REJECTED, json_bytes

TIER0, TIER1, TIER3 = 0, 1, 3


class Verifier:
    def __init__(self, id, version, tier, applies_to, check):
        self.id = id
        self.version = version
        self.tier = tier
        self.applies_to = frozenset(applies_to)
        self._check = check
        self.digest = hashlib.sha256(json_bytes(
            {"id": id, "version": version, "tier": tier,
             "applies_to": sorted(applies_to)})).hexdigest()

    def applies(self, claim_type):
        return claim_type in self.applies_to or "*" in self.applies_to

    def check(self, claim, *, descriptor_claims=()):
        return self._check(claim, descriptor_claims=descriptor_claims)


def pass_(code):
    return {"outcome": "pass", "reason_code": code}


def fail(code):
    return {"outcome": "fail", "reason_code": code}


def unsupported(code):
    return {"outcome": "unsupported", "reason_code": code}


# -- tier 0: anchor and value checks ---------------------------------------------

def _tier0_anchors(claim, *, descriptor_claims=()):
    # the claim was submitted only after anchor resolution; tier 0 re-asserts
    # the invariant on the record itself
    if not claim.get("anchors"):
        return fail("claim.anchor.unresolved")
    return pass_("verify.anchor.resolved")


def _tier0_value(claim, *, descriptor_claims=()):
    if claim.get("value_origin") == "model":
        # generative: no anchored span to compare; never value-verified here
        return unsupported("verify.value.generative")
    reasons = {r["code"] for r in claim.get("reasons", [])}
    if "claim.normalization.unregistered" in reasons:
        return unsupported("claim.normalization.unregistered")
    return pass_("verify.value.match")


# -- tier 1: Argentine domain pack (design decision 9) ---------------------------

def _decimals(claims, types):
    """Canonical decimal values of sibling claims of the given types.

    Returns (values, None), or (None, problem) with problem:
    "missing" — no sibling claim for some type (or an unparseable value);
    "conflicted" — multiple DISTINCT canonical values for one sibling type.
    A conflict is an undeclared election: reporting it as a typed unknown
    keeps the exported check from flipping with claim order.
    """
    out = []
    for t in types:
        found = [c for c in claims if c["type"] == t]
        if not found:
            return None, "missing"
        try:
            vals = [float(c["value"]) for c in found]
        except (TypeError, ValueError):
            return None, "missing"
        if len(set(vals)) > 1:
            return None, "conflicted"
        out.append(vals[0])
    return out, None


_CUIT_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _cuit_check_digit(digits):
    check = sum(d * w for d, w in zip(digits, _CUIT_WEIGHTS)) % 11
    mod = 11 - check
    if mod == 11:
        return 0
    if mod == 10:
        return 9
    return mod


def _rule_cuit(claim, *, descriptor_claims=()):
    raw = str(claim["value"]).replace("-", "")
    if len(raw) != 11 or not raw.isdigit():
        return fail("verify.cuit.parse.invalid")
    if _cuit_check_digit([int(d) for d in raw[:10]]) != int(raw[10]):
        return fail("verify.cuit.check-digit.invalid")
    return pass_("verify.cuit.check-digit.valid")


def _rule_total_sum(claim, *, descriptor_claims=()):
    parts, problem = _decimals(descriptor_claims,
                               ("field:subtotal", "field:tax"))
    if problem is not None:
        return unsupported(f"verify.total-sum.siblings-{problem}")
    try:
        total = float(claim["value"])
    except (TypeError, ValueError):
        return fail("verify.currency.parse.invalid")
    if abs(total - (parts[0] + parts[1])) > 0.005:
        return fail("verify.total-sum.mismatch")
    return pass_("verify.total-sum.match")


def _rule_running_balance(claim, *, descriptor_claims=()):
    parts, problem = _decimals(descriptor_claims,
                               ("field:prior-balance", "field:amount"))
    if problem is not None:
        return unsupported(f"verify.running-balance.siblings-{problem}")
    try:
        balance = float(claim["value"])
    except (TypeError, ValueError):
        return fail("verify.currency.parse.invalid")
    if abs(balance - (parts[0] + parts[1])) > 0.005:
        return fail("verify.running-balance.broken")
    return pass_("verify.running-balance.continuous")


def _rule_date(claim, *, descriptor_claims=()):
    from dsc03.claims import normalize_date
    if normalize_date(str(claim["value"])) is None:
        return fail("verify.date.parse.invalid")
    return pass_("verify.date.parse.valid")


_CURRENCY_TYPES = ("field:total", "field:subtotal", "field:tax",
                   "field:amount", "field:balance", "field:prior-balance")


def _rule_currency(claim, *, descriptor_claims=()):
    from dsc03.claims import normalize_currency
    if normalize_currency(str(claim["value"])) is None:
        return fail("verify.currency.parse.invalid")
    return pass_("verify.currency.parse.valid")


def _rule_visual(claim, *, descriptor_claims=()):
    """Tier 3 adapter over the dsc03.visual raster oracles (tasks 4.5).

    Independent ink check of a claim whose anchors carry a quantized box
    (zoom.py region shape, descriptor pt, y-up bottom-left origin) against
    a rendered page supplied as a `visual:render:page` descriptor fact
    ({rendered, config} — the pinned RenderConfig machinery). Verifiers
    stay pure: the render is a descriptor fact passed to check, never
    module state, never carried on the claim record.

    Per anchor: map the box to the raster with the snap.py convention
    (pt -> px at the declared dpi, y flip, floor/ceil edges — sub-pixel
    edge overhang accepted, the zoom.py sub-tolerance discipline; edges
    clamp to the raster), count ink in the RAW binarized mask (strict
    gray < threshold; the declared dilation stays a comparison tolerance,
    not an ink source — same measurement surface as snap.py) and compare
    its fraction against the DECLARED INK_FRACTION_THRESHOLD. Every
    anchored box must hold ink: any ink-free box is a typed fail with a
    witness (anchor, declared box, measured fraction, threshold); all
    boxes inked is a typed pass. A missing render fact, an anchor without
    a box, a malformed fact or box, or a box falling entirely outside the
    raster each surface as a typed `unsupported`; MaskUnavailable from the
    shared pixel gate becomes a typed `unsupported` naming the shared
    reason — never swallowed, never a bare exception. Deterministic across
    processes: pure integer pixel counting over decoded bytes.
    """
    try:
        from dsc03.visual._pixels import comparison_mask, MaskUnavailable
    except ImportError:
        return unsupported("verify.visual.oracle-unavailable")
    fact = None
    for entry in descriptor_claims:
        if isinstance(entry, dict) and entry.get("type") == RENDER_FACT_TYPE:
            fact = entry
            break
    if fact is None:
        # The pixel comparison needs a pinned render result for the anchored
        # region; no render result is carried on the claim record itself, so
        # the adapter reports the typed unknown until a render is supplied.
        return unsupported("verify.visual.render-result-missing")
    if not (hasattr(fact.get("rendered"), "data")
            and hasattr(fact.get("config"), "binarization")):
        return unsupported("verify.visual.render-fact-invalid")
    rendered, config = fact["rendered"], fact["config"]
    boxes = []
    for anchor in claim.get("anchors") or ():
        box, problem = _anchor_box(anchor)
        if problem is not None:
            return unsupported("verify.visual." + problem)
        boxes.append((anchor.get("id"), box, list(anchor["box"])))
    try:
        width, height, raw, _simplified = comparison_mask(rendered, config)
    except MaskUnavailable as unavailable:
        return unsupported("verify.visual." + unavailable.reason)
    scale = config.dpi / 72.0  # pt -> px; raster y is top-down
    for anchor_id, (x0, y0, x1, y1), declared in boxes:
        px0, px1 = x0 * scale, x1 * scale
        py0, py1 = height - y1 * scale, height - y0 * scale  # top, bottom rows
        sx0 = max(0, int(math.floor(px0)))
        sx1 = min(width, int(math.ceil(px1)))
        sy0 = max(0, int(math.floor(py0)))
        sy1 = min(height, int(math.ceil(py1)))
        if sx1 <= sx0 or sy1 <= sy0:
            # no raster pixel lies under the box: there is no measurement
            # surface, so the honest answer is a typed unknown, not a fail
            return unsupported("verify.visual.box-outside-render")
        total = (sx1 - sx0) * (sy1 - sy0)
        ink = 0
        for row in range(sy0, sy1):
            ink += raw[row * width + sx0:row * width + sx1].count(1)
        fraction = ink / total
        if fraction < INK_FRACTION_THRESHOLD:
            return {"outcome": "fail",
                    "reason_code": "verify.visual.ink-absent",
                    "witness": {"anchor": anchor_id, "box": declared,
                                "fraction": fraction,
                                "threshold": INK_FRACTION_THRESHOLD}}
    return pass_("verify.visual.ink-present")


# Declared ink-presence threshold for the tier-3 ink-agreement oracle.
# Derivation (declared once here, never inferred at check time): the
# box->raster mapping follows the snap.py convention (floor/ceil on each
# edge, raster clamp), so a sub-pixel edge overhang is accepted — the same
# zoom.py sub-tolerance containment discipline. The measured ink is the RAW
# binarized mask (strict gray < threshold, no dilation), whose noise floor
# on an ink-free box is exactly 0.0. The thinnest ink a legitimately
# anchored span contributes at the pinned 72 dpi is a full-span 1 px
# hairline inside a text-line-height region (~12 px tall): fraction >=
# 1/12 ≈ 0.083. INK_FRACTION_THRESHOLD sits between the two bounds: any
# full-span hairline in a region up to 100 px tall still clears it
# (1/100 = 0.01); measured ink below that in a claimed span is reported as
# a typed fail with the measured fraction as witness.
INK_FRACTION_THRESHOLD = 0.01

# The descriptor fact type carrying the pinned render for tier-3 checks:
# {"type": "visual:render:page", "rendered": <render.Rendered>,
#  "config": <render.RenderConfig>} — a descriptor fact passed to check
# (design decision 5: pure function of claim + descriptor facts), never
# claim payload, never module state.
RENDER_FACT_TYPE = "visual:render:page"


def _anchor_box(anchor):
    """The quantized box of one anchor, plus a typed problem name.

    Returns ((x0, y0, x1, y1), None) — finite numbers in descriptor pt,
    positive extent, the zoom.py region-box shape — or (None, problem)
    with problem "anchor-box-missing" | "anchor-box-invalid". The box is
    never re-quantized (quantization is idempotent on the operative box).
    """
    if not isinstance(anchor, dict) or "box" not in anchor:
        return None, "anchor-box-missing"
    box = anchor["box"]
    if not (isinstance(box, (list, tuple)) and len(box) == 4
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) for v in box)):
        return None, "anchor-box-invalid"
    x0, y0, x1, y1 = (float(v) for v in box)
    if not (x1 > x0 and y1 > y0):
        return None, "anchor-box-invalid"
    return (x0, y0, x1, y1), None


VERIFIERS = [
    Verifier("verify.anchor.resolved", "1", TIER0, {"*"}, _tier0_anchors),
    Verifier("verify.value.match", "1", TIER0, {"*"}, _tier0_value),
    Verifier("ar.cuit.check-digit", "1", TIER1, {"field:cuit"}, _rule_cuit),
    Verifier("ar.invoice.total-sum", "1", TIER1, {"field:total"},
             _rule_total_sum),
    Verifier("ar.bank.running-balance", "1", TIER1, {"field:balance"},
             _rule_running_balance),
    Verifier("ar.date.parse", "1", TIER1, {"field:date"}, _rule_date),
    Verifier("ar.currency.parse", "1", TIER1, set(_CURRENCY_TYPES),
             _rule_currency),
    Verifier("visual.ink-agreement", "1", TIER3, {"*"}, _rule_visual),
]

REGISTRY = {v.id: v for v in VERIFIERS}


def verifier(id):
    return REGISTRY[id]


REGISTRY_DIGEST = hashlib.sha256(json_bytes(
    [{"id": v.id, "version": v.version, "digest": v.digest}
     for v in sorted(VERIFIERS, key=lambda v: v.id)])).hexdigest()


# -- ladder execution -------------------------------------------------------------

def run_ladder(claims, *, descriptor=None):
    """Run tiers 0 and 1 over a claim set; return claims with `checks` filled
    and statuses recomputed.

    `verified` requires both tier 0 checks to pass AND at least one
    applicable tier 1 rule to pass; absence of an applicable rule never
    yields `verified`. `conflicted` is set before the ladder runs and is
    never promoted (conflict semantics owned by document-context). Tier 2 is
    deferred (no producer); tier 3 is adapter-only and not auto-run.
    """
    from dsc03.claims import mark_conflicts, meet_status  # noqa: F401

    if claims and "type" in claims[0]:
        from dsc03.claims import STATUS_ORDER  # noqa: F401

    out = []
    claims = mark_conflicts(claims)
    for claim in claims:
        c = dict(claim)
        checks = []
        t0_results = [verifier("verify.anchor.resolved").check(c),
                      verifier("verify.value.match").check(c)]
        for v, res in ((verifier("verify.anchor.resolved"), t0_results[0]),
                       (verifier("verify.value.match"), t0_results[1])):
            checks.append({"id": v.id, "version": v.version, "tier": v.tier,
                           **res})
        t1_results = []
        for v in VERIFIERS:
            if v.tier != 1 or not v.applies(c["type"]):
                continue
            res = v.check(c, descriptor_claims=claims)
            t1_results.append((v, res))
            checks.append({"id": v.id, "version": v.version, "tier": v.tier,
                           **res})
        if c["status"] == "conflicted":
            pass  # never promoted
        elif c["status"] == REJECTED:
            pass  # a human rejection stands; the ladder never overrides it
        elif (all(r["outcome"] == "pass" for r in t0_results)
              and any(r["outcome"] == "pass" for _, r in t1_results)):
            c["status"] = "verified"
        else:
            if c["status"] not in ("conflicted", REJECTED):
                c["status"] = "unverified"
        c["checks"] = checks
        out.append(c)
    return out
