# Purpose: Typed agent tool surface (sunset-14b, add-agent-tool-surface): the
#   small, typed, stable surface models use instead of running modules from a
#   checkout. One outcome envelope {status, reason, data, cursor?,
#   provider_calls} with a closed status vocabulary and stable reason codes;
#   read tools (open, words, crop, zoom_in, zoom_out, queue) that never mutate
#   claims or run artifacts; write tools (propose, decide) that are idempotent
#   through claim ids; gated export.
# Responsibilities: (1) ToolSurface — a workspace-bound session over a
#   digitization run (or a source carrier digitized through the pinned native
#   path), addressing scopes and claims by anchor-derived ids only; (2) the
#   six read tools, pure over session claims; (3) propose/decide persisting
#   idempotent claims; (4) export admitting only autonomy-gated or
#   human-accepted claims, never rejected ones; (5) deterministic cursors
#   encoding tool, scope, offset and run digest, refusing stale runs.
# Rationale: change design decisions 1-8. Document text is data: it appears
#   only under data.text fields marked untrusted:true, never in status,
#   reason or message fields (refusal details are deliberately not echoed).
#   The core is adapter-agnostic: CLI (phase 1) and MCP (phase 2, deferred)
#   adapters sit on top of these functions with a parity requirement.
"""Typed agent tool surface: one envelope, one reason vocabulary, one core."""
import base64
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

from dsc03.audit_gate import gate_open
from dsc03.claims import (REJECTED, Refusal, add_claim, export_record,
                          submit_claim)
from dsc03.review_queue import decide as review_decide
from dsc03.review_queue import review_queue
from dsc03.verify.registry import run_ladder
from dsc03.zoom import zoom_in as zoom_restrict

# -- closed vocabularies ----------------------------------------------------------

# status: exactly this set (spec: closed vocabulary, asserted exhaustively).
STATUSES = ("ok", "refused", "error")

# reason: stable codes; every envelope carries exactly one. Codes prefixed
# claim.* are passed through from dsc03.claims.Refusal verbatim.
REASONS = (
    "action.unknown",
    "address.missing",
    "address.not-anchor",
    "bounds.exceeded",
    "claim.anchor.unresolved",
    "claim.exists",
    "claim.unknown",
    "claim.value.mismatch",
    "claim.value.unparseable",
    "crop.geometry-missing",
    "cursor.invalid",
    "cursor.stale",
    "internal.error",
    "ok",
    "scope.no-parent",
    "scope.unknown",
    "session.unopened",
    "source.unreadable",
    "spec.invalid",
)

OK, REFUSED, ERROR = STATUSES

# Addresses are anchor-derived ids only (design decision 3): the identity
# profile's `a:<128-bit hex>` form for scopes/regions, `c:` for claims.
ANCHOR_ID = re.compile(r"a:[0-9a-f]{32}\Z")
CLAIM_ID = re.compile(r"c:[0-9a-f]{32}\Z")
# word/line/block locators carry a trailing quantized box; page locators do
# not ("page:1") — both forms resolve the page and, where present, offsets.
LOCATOR_BOX = re.compile(r"page:(\d+)/(?:word|line|block):\[(\d+),(\d+)\)")
LOCATOR_PAGE = re.compile(r"page:(\d+)\Z")
LOCATOR_QUANTIZED_BOX = re.compile(
    r"box=\[(-?\d+),(-?\d+),(-?\d+),(-?\d+)\]")

# Declared size bounds (design decision 5).
DEFAULT_PAGE_WORDS = 100
MAX_PAGE_WORDS = 1000
MAX_RENDER_PIXELS = 16_000_000
DEFAULT_DPI = 72

SESSION_VERSION = 1
SESSION_FILE = "sunset-session.json"
CURSOR_VERSION = 1

WRITE_ACTIONS = ("accept", "reject", "edit")


def json_bytes(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# -- envelope ---------------------------------------------------------------------

def envelope(status, reason, data, cursor=None):
    """The one outcome shape. No message field exists by construction:
    document text cannot leak into status/reason/messages (design 4)."""
    out = {"status": status, "reason": reason, "data": data,
           "provider_calls": 0}
    if cursor is not None:
        out["cursor"] = cursor
    return out


def _tool(fn):
    """Never raise to the caller (spec: typed outcomes). Refusal detail is
    deliberately dropped: refusal messages may embed anchored document text."""
    def wrapped(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Refusal as refusal:
            return envelope(REFUSED, refusal.reason_code, {})
        except Exception as error:  # noqa: BLE001 - the surface never raises
            return envelope(ERROR, "internal.error",
                            {"exception": type(error).__name__})
    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


# -- cursors ------------------------------------------------------------------------

def _cursor_encode(tool, scope, offset, run_digest):
    payload = {"v": CURSOR_VERSION, "tool": tool, "scope": scope,
               "offset": offset, "run": run_digest}
    return base64.urlsafe_b64encode(json_bytes(payload)).decode("ascii")


def _cursor_decode(cursor):
    """Structural cursor validation; None when malformed."""
    if not isinstance(cursor, str):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
    except Exception:  # noqa: BLE001 - any decode failure is one refusal
        return None
    if not isinstance(payload, dict) or set(payload) != {
            "v", "tool", "scope", "offset", "run"}:
        return None
    if payload["v"] != CURSOR_VERSION or payload["offset"] < 0:
        return None
    if not all(isinstance(payload[k], str)
               for k in ("tool", "scope", "run")):
        return None
    if type(payload["offset"]) is not int:
        return None
    return payload


# -- helpers ------------------------------------------------------------------------

def _is_int(value):
    return type(value) is int


def _quantum_scale(quantization):
    """The declared box quantum ("1/1000 pt") as an integer divisor."""
    quantum = (quantization or {}).get("quantum", "")
    match = re.fullmatch(r"1/(\d+) ?pt", quantum.strip())
    return int(match.group(1)) if match else 1000


def _locator_page_offsets(region):
    """(page, start, end) from a native locator path, else None."""
    match = LOCATOR_BOX.match(
        (region.get("anchor") or {}).get("locator_path", ""))
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))) \
        if match else None


def _locator_page(region):
    match = _locator_page_offsets(region)
    if match:
        return match[0]
    match = LOCATOR_PAGE.match(
        (region.get("anchor") or {}).get("locator_path", ""))
    return int(match.group(1)) if match else None


def _canonical_box(box):
    """A page-pt frame box with float coordinates, or None."""
    if not isinstance(box, dict):
        return None
    try:
        return {"page": int(box["page"]), "x": float(box["x"]),
                "y": float(box["y"]), "w": float(box["w"]),
                "h": float(box["h"])}
    except (KeyError, TypeError, ValueError):
        return None


# -- the surface ---------------------------------------------------------------------

class ToolSurface:
    """Workspace-bound session over one digitization run.

    The run directory is immutable document state; `claims` live in the
    workspace session store and change only through propose/decide. Read
    tools are pure over both.
    """

    def __init__(self, workspace):
        self.workspace = Path(workspace)
        self.session_path = self.workspace / SESSION_FILE
        self.run_dir = None
        self.descriptor = None
        self.manifest = None
        self.claims = []
        self.run_digest = None
        self._word_map = {}
        self._frames = {}
        self._source_bytes = None
        self._quantum = 1000
        self._load_session()

    # -- session ------------------------------------------------------------------

    def _load_session(self):
        if not self.session_path.is_file():
            return
        try:
            session = json.loads(self.session_path.read_bytes())
            if session.get("version") != SESSION_VERSION:
                return
            self._load_run(Path(session["run"]))
            self.claims = list(session.get("claims", []))
        except (OSError, ValueError, KeyError):
            self.run_dir = None
            self.descriptor = None
            self.manifest = None
            self.run_digest = None
            self.claims = []

    def _load_run(self, run_dir):
        """Bind the session to a run directory, verifying pinned digests."""
        manifest_bytes = (run_dir / "manifest.json").read_bytes()
        descriptor_bytes = (run_dir / "descriptor.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        descriptor = json.loads(descriptor_bytes)
        ref = manifest.get("descriptor") or {}
        if ref.get("sha256") and ref["sha256"] != sha256(descriptor_bytes):
            raise ValueError("descriptor digest mismatch")
        run_digest = manifest.get("semantic_sha256")
        if not run_digest:
            raise ValueError("run manifest lacks a semantic digest")
        artifacts = manifest.get("artifacts", {})

        def artifact_bytes(name):
            ref = artifacts.get(name)
            if not ref:
                return None
            data = (run_dir / name).read_bytes()
            if ref.get("sha256") and ref["sha256"] != sha256(data):
                raise ValueError(f"artifact digest mismatch: {name}")
            return data

        self._word_map = {}
        word_bytes = artifact_bytes("word-map.json")
        if word_bytes:
            for entry in json.loads(word_bytes):
                key = (entry["page"], entry["raw_start"], entry["raw_end"])
                self._word_map[key] = entry
        self._frames = {}
        geometry_bytes = artifact_bytes("carrier/geometry.json")
        if geometry_bytes:
            for frame in json.loads(geometry_bytes).get("frames", []):
                self._frames[frame.get("name")] = frame
        quantization_bytes = artifact_bytes("carrier/quantization.json")
        self._quantum = _quantum_scale(
            json.loads(quantization_bytes) if quantization_bytes else None)
        source = artifact_bytes("source.pdf")
        if source is None:
            raise ValueError("run lacks its source artifact")
        self._source_bytes = source
        self.run_dir = run_dir
        self.manifest = manifest
        self.descriptor = descriptor
        self.run_digest = run_digest

    def _persist(self):
        """Write tools only: atomic canonical session store write."""
        payload = {"version": SESSION_VERSION, "run": str(self.run_dir),
                   "run_digest": self.run_digest, "claims": self.claims}
        self.workspace.mkdir(parents=True, exist_ok=True)
        tmp = self.session_path.with_suffix(".tmp")
        tmp.write_bytes(json_bytes(payload))
        os.replace(tmp, self.session_path)

    def _opened(self):
        return self.descriptor is not None

    def _regions_by_id(self):
        return {r["id"]: r for r in self.descriptor.get("regions", [])}

    def _spec_refused(self, reason):
        return envelope(REFUSED, reason, {})

    def _anchor(self, value, field):
        """Anchor-form address check (task 3.3): labels and indexes refused."""
        if value is None:
            return self._spec_refused("address.missing")
        if not isinstance(value, str) or not ANCHOR_ID.fullmatch(value):
            return self._spec_refused("address.not-anchor")
        return None

    # -- open ---------------------------------------------------------------------

    @_tool
    def open(self, run=None, source=None):
        """Establish the session over a run directory or a source carrier."""
        if bool(run) == bool(source):
            return self._spec_refused("address.missing")
        if source is not None:
            extracted = self._extract_source(source)
            if extracted["status"] != OK:
                return extracted
            run = extracted["data"]["run"]
        run_dir = Path(run)
        if not run_dir.is_dir():
            return envelope(REFUSED, "source.unreadable", {"run": str(run)})
        try:
            self._load_run(run_dir)
        except (OSError, ValueError):
            return envelope(REFUSED, "source.unreadable", {"run": str(run)})
        previous = None
        if self.session_path.is_file():
            try:
                previous = json.loads(self.session_path.read_bytes())
            except (OSError, ValueError):
                previous = None
        if previous and previous.get("run_digest") == self.run_digest:
            self.claims = list(previous.get("claims", []))
        else:
            self.claims = []
        self._persist()
        regions = self.descriptor.get("regions", [])
        return envelope(OK, "ok", {
            "run_digest": self.run_digest,
            "source_sha256": self.manifest.get("source", {}).get("sha256"),
            "pages": len(self.manifest.get("pages", [])) or
            sum(1 for r in regions if r.get("kind") == "page"),
            "regions_by_kind": dict(sorted(Counter(
                r.get("kind") for r in regions).items())),
        })

    def _extract_source(self, source):
        """Digitize a raw carrier through the pinned native path into the
        workspace run store (deterministic dir keyed by source digest)."""
        from digitization.native import NativeInputError, extract
        try:
            data = Path(source).read_bytes()
        except OSError:
            return envelope(REFUSED, "source.unreadable",
                            {"source": str(source)})
        target = self.workspace / "runs" / sha256(data)[:16]
        if not target.is_dir():
            try:
                extract(source, target)
            except (NativeInputError, OSError, ValueError):
                return envelope(REFUSED, "source.unreadable",
                                {"source": str(source)})
        return envelope(OK, "ok", {"run": str(target)})

    # -- read tools -----------------------------------------------------------------

    def _closure(self, scope_id):
        """The scope and its descendant closure over contains edges."""
        children = {}
        for rel in self.descriptor.get("relations", []):
            if rel.get("kind") == "contains":
                children.setdefault(rel["from"], set()).add(rel["to"])
        keep, frontier = {scope_id}, [scope_id]
        while frontier:
            node = frontier.pop()
            for child in children.get(node, ()):
                if child not in keep:
                    keep.add(child)
                    frontier.append(child)
        return keep

    def _restrict(self, scope_id):
        """zoom.restrict with the selector/evidence/interpretation cascade the
        landed scoped projection leaves to its callers: selectors outside the
        closure, evidence over dropped selectors, interpretations over
        dropped evidence, and precedes edges over dropped interpretations are
        dropped first and counted (they would otherwise dangle and refuse the
        projection on native descriptors). The ladder law itself stays
        dsc03.zoom."""
        result = zoom_restrict(self.descriptor, scope_id)
        if result["status"] == "restricted" or \
                result.get("reason") != "projected_invalid":
            return result, 0
        regions = self._regions_by_id()
        keep = self._closure(scope_id) | {v["root"]
                                          for v in self.descriptor["views"]
                                          if v["root"] in regions}
        contents = {rel["to"] for rel in self.descriptor.get("relations", [])
                    if rel.get("kind") == "has-content"
                    and rel.get("from") in keep}
        selectors = [s for s in self.descriptor.get("selectors", [])
                     if s.get("target") in keep | contents]
        selector_ids = {s["id"] for s in selectors}
        evidence = [e for e in self.descriptor.get("evidence", [])
                    if set(e.get("content_ids", [])) <= contents
                    and set(e.get("selector_ids", [])) <= selector_ids]
        evidence_ids = {e["id"] for e in evidence}
        interpretations = [i for i in self.descriptor.get("interpretations",
                                                           [])
                           if set(i.get("evidence", [])) <= evidence_ids]
        interp_ids = {i["id"] for i in interpretations}
        before_rels = len(self.descriptor.get("relations", []))
        relations = [r for r in self.descriptor.get("relations", [])
                     if "interpretation_id" not in r
                     or r["interpretation_id"] in interp_ids]
        dropped = (len(self.descriptor.get("selectors", [])) - len(selectors)
                   + len(self.descriptor.get("evidence", [])) - len(evidence)
                   + len(self.descriptor.get("interpretations", []))
                   - len(interpretations)
                   + before_rels - len(relations))
        if dropped == 0:
            return result, 0
        desc = dict(self.descriptor, selectors=selectors, evidence=evidence,
                    interpretations=interpretations, relations=relations)
        return zoom_restrict(desc, scope_id), dropped

    def _word_entries(self, scope_id):
        """Word entries under the scope, in deterministic reading order."""
        regions = self._regions_by_id()
        closure = self._closure(scope_id)
        entries = []
        word_regions = [regions[i] for i in sorted(closure)
                        if i in regions and regions[i].get("kind") == "word"]
        for region in word_regions:
            locator = _locator_page_offsets(region)
            entry = self._word_map.get(locator) if locator else None
            if entry:
                x0, y0 = entry["source_box"][0], entry["source_box"][1]
                entries.append({"region_id": region["id"],
                                "page": entry["page"],
                                "text": entry["text"],
                                "order": (entry["page"], y0, x0,
                                          region["id"])})
        if entries or self._word_map:
            entries.sort(key=lambda e: e.pop("order"))
            return entries
        # descriptors without word maps (recorded runs): fall back to
        # has-content text contents of the closure, ordered by region id
        contents = {c["id"]: c for c in self.descriptor.get("contents", [])
                    if c.get("kind") == "text"}
        for rel in sorted(self.descriptor.get("relations", []),
                          key=lambda r: (r.get("from", ""), r.get("to", ""))):
            if rel.get("kind") != "has-content" or rel["from"] not in closure:
                continue
            content = contents.get(rel["to"])
            if content:
                region = regions.get(rel["from"], {})
                entries.append({"region_id": rel["from"],
                                "content_id": rel["to"],
                                "page": _locator_page(region)
                                or (region.get("geometry") or {}).get("page", 0),
                                "text": content["value"]})
        entries.sort(key=lambda e: (e["page"], e["region_id"], e["content_id"]))
        return entries

    @_tool
    def words(self, scope=None, page_size=None, cursor=None):
        """Page-bounded document text of a scope; text lives only in
        data.text, marked untrusted (design decision 4)."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        if scope is None and cursor is None:
            return self._spec_refused("address.missing")
        offset = 0
        if cursor is not None:
            payload = _cursor_decode(cursor)
            if payload is None or payload["tool"] != "words" or \
                    (scope is not None and payload["scope"] != scope):
                return envelope(REFUSED, "cursor.invalid", {})
            if payload["run"] != self.run_digest:
                return envelope(REFUSED, "cursor.stale",
                                {"cursor_run": payload["run"]})
            scope = payload["scope"]
            offset = payload["offset"]
        refused = self._anchor(scope, "scope")
        if refused:
            return refused
        if scope not in self._regions_by_id():
            return envelope(REFUSED, "scope.unknown", {"scope": scope})
        if page_size is None:
            page_size = DEFAULT_PAGE_WORDS
        if not _is_int(page_size) or not 1 <= page_size <= MAX_PAGE_WORDS:
            return envelope(REFUSED, "bounds.exceeded",
                            {"page_size": page_size,
                             "max_page_words": MAX_PAGE_WORDS})
        entries = self._word_entries(scope)
        if offset > len(entries):
            return envelope(REFUSED, "cursor.invalid", {})
        page = entries[offset:offset + page_size]
        cursor_next = None
        if offset + page_size < len(entries):
            cursor_next = _cursor_encode("words", scope, offset + page_size,
                                         self.run_digest)
        return envelope(OK, "ok", {
            "scope": scope, "count": len(page), "total": len(entries),
            "text": {"untrusted": True, "items": page},
        }, cursor=cursor_next)

    @_tool
    def crop(self, anchor=None, dpi=None):
        """Pinned crop reference plus in-memory raster of one region."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        refused = self._anchor(anchor, "anchor")
        if refused:
            return refused
        regions = self._regions_by_id()
        region = regions.get(anchor)
        if region is None:
            return envelope(REFUSED, "scope.unknown", {"anchor": anchor})
        if dpi is None:
            dpi = DEFAULT_DPI
        if not _is_int(dpi) or dpi < 1:
            return envelope(REFUSED, "bounds.exceeded", {"dpi": dpi})
        box = self._crop_box(region)
        if box is None:
            return envelope(REFUSED, "crop.geometry-missing",
                            {"anchor": anchor})
        pixels = -(-box["w"] * dpi // 72) * -(-box["h"] * dpi // 72)
        if pixels > MAX_RENDER_PIXELS:
            return envelope(REFUSED, "bounds.exceeded",
                            {"pixels": pixels,
                             "max_render_pixels": MAX_RENDER_PIXELS})
        from digitization.render import crop_reference, render_crop
        png, record = render_crop(self._source_bytes, box["page"], dpi, box)
        digest = self._geometry_profile_digest()
        reference = crop_reference(digest, record, box)
        return envelope(OK, "ok", {
            "anchor": anchor,
            "crop_reference": reference,
            "render": {"png_base64": base64.b64encode(png).decode("ascii"),
                       "meta": record},
            "text": {"untrusted": True, "format": "raster-png"},
        })

    def _geometry_profile_digest(self):
        for profile in self.descriptor.get("profiles", []):
            if profile.get("kind") == "geometry":
                return profile.get("sha256")
        return None

    def _crop_box(self, region):
        """Page-pt frame box of a region: declared geometry, locator box
        (scaled by the declared quantum), or the whole page frame."""
        box = _canonical_box(region.get("geometry"))
        if box:
            return box
        page = _locator_page(region)
        quantized = LOCATOR_QUANTIZED_BOX.search(
            (region.get("anchor") or {}).get("locator_path", ""))
        if quantized:
            x0, y0, x1, y1 = (int(v) / self._quantum
                              for v in quantized.groups())
            return {"page": page, "x": x0, "y": y0,
                    "w": x1 - x0, "h": y1 - y0}
        if region.get("kind") == "page" and page:
            frame = self._frames.get(f"page-{page}-pt")
            if frame:
                cropbox = frame.get("cropbox") or frame.get(
                    "source_dimensions") or [0, 0]
                return {"page": page, "x": 0.0, "y": 0.0,
                        "w": float(cropbox[2]), "h": float(cropbox[3])}
        return None

    @_tool
    def zoom_in(self, scope=None):
        """Restriction of the view to one ladder scope (pure; dsc03.zoom)."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        refused = self._anchor(scope, "scope")
        if refused:
            return refused
        result, dropped_refs = self._restrict(scope)
        if result["status"] != "restricted":
            reason = "scope.unknown" if result.get("reason") == "unknown-scope" \
                else "internal.error"
            return envelope(REFUSED, reason, {"scope": scope})
        restricted = result["descriptor"]
        return envelope(OK, "ok", {
            "scope": scope,
            "scale": next((r["kind"] for r in restricted["regions"]
                           if r["id"] == scope), None),
            "region_count": len(restricted["regions"]),
            "region_ids": sorted(r["id"] for r in restricted["regions"]),
            "coverage_loss": len(result.get("coverage_loss", []))
            + len(result.get("excluded", [])),
            "dropped_refs": dropped_refs,
        })

    @_tool
    def zoom_out(self, scope=None):
        """The parent scopes of one scope on the containment ladder."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        refused = self._anchor(scope, "scope")
        if refused:
            return refused
        regions = self._regions_by_id()
        if scope not in regions:
            return envelope(REFUSED, "scope.unknown", {"scope": scope})
        parents = sorted({rel["from"] for rel in
                          self.descriptor.get("relations", [])
                          if rel.get("kind") == "contains"
                          and rel.get("to") == scope and rel["from"] in regions})
        if not parents:
            return envelope(REFUSED, "scope.no-parent", {"scope": scope})
        return envelope(OK, "ok", {
            "scope": scope,
            "parents": [{"id": p, "scale": regions[p].get("kind")}
                        for p in parents],
        })

    @_tool
    def queue(self):
        """The derived review queue over session claims (pure)."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        from digitization.review import crop_references
        refs = crop_references(self.descriptor, self._source_bytes,
                               DEFAULT_DPI)
        items = review_queue(self.claims, crop_references=refs)
        return envelope(OK, "ok", {"items": items, "count": len(items)})

    # -- write tools ----------------------------------------------------------------

    def _valid_spec(self, spec):
        """Structure check only; anchor FORM is an addressing refusal."""
        if not isinstance(spec, dict):
            return False
        if not set(("type", "anchors", "value", "origin")) <= set(spec):
            return False
        if not all(isinstance(spec[k], str) and spec[k]
                   for k in ("type", "value", "origin")):
            return False
        anchors = spec["anchors"]
        return isinstance(anchors, list) and bool(anchors)

    @_tool
    def propose(self, spec=None):
        """Idempotent claim admission (task 3.2): identity is the claim id."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        if spec is None:
            return self._spec_refused("address.missing")
        if isinstance(spec, dict) and "anchors" in spec and (
                not isinstance(spec["anchors"], list) or not spec["anchors"]
                or any(not isinstance(a, str) or not ANCHOR_ID.fullmatch(a)
                       for a in spec["anchors"])):
            # anchor-shaped address fields are addressing refusals first
            # (task 3.3): labels, indexes and malformed anchor lists are
            # never a generic spec error
            return self._spec_refused("address.not-anchor")
        if not self._valid_spec(spec):
            return self._spec_refused("spec.invalid")
        try:
            claim = submit_claim(self.descriptor, spec)
        except Refusal as refusal:
            return envelope(REFUSED, refusal.reason_code, {})
        existing = next((c for c in self.claims
                         if c["id"] == claim["id"]), None)
        if existing is not None:
            return envelope(OK, "claim.exists", {
                "claim_id": claim["id"], "already_present": True,
                "status": existing["status"]})
        self.claims = run_ladder(add_claim(self.claims, claim),
                                 descriptor=self.descriptor)
        self._persist()
        stored = next(c for c in self.claims if c["id"] == claim["id"])
        return envelope(OK, "ok", {
            "claim_id": claim["id"], "already_present": False,
            "status": stored["status"]})

    @_tool
    def decide(self, claim_id=None, action=None, value=None, reviewer=None):
        """Idempotent human decision through claim ids (task 3.2)."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        if claim_id is None or action is None:
            return self._spec_refused("address.missing")
        if not isinstance(claim_id, str) or not CLAIM_ID.fullmatch(claim_id):
            return self._spec_refused("address.not-anchor")
        claim = next((c for c in self.claims if c["id"] == claim_id), None)
        if claim is None:
            return envelope(REFUSED, "claim.unknown", {"claim_id": claim_id})
        if action not in WRITE_ACTIONS:
            return envelope(REFUSED, "action.unknown", {"action": action})
        if action == "edit" and value is None:
            return self._spec_refused("spec.invalid")
        try:
            human = review_decide(self.descriptor, claim, action,
                                  value=value, reviewer=reviewer)
        except Refusal as refusal:
            return envelope(REFUSED, refusal.reason_code, {})
        existing = next((c for c in self.claims
                         if c["id"] == human["id"]), None)
        if existing is not None:
            return envelope(OK, "claim.exists", {
                "claim_id": human["id"], "already_present": True,
                "status": existing["status"]})
        self.claims = run_ladder(add_claim(self.claims, human),
                                 descriptor=self.descriptor)
        self._persist()
        stored = next(c for c in self.claims if c["id"] == human["id"])
        return envelope(OK, "ok", {
            "claim_id": human["id"], "already_present": False,
            "status": stored["status"]})

    # -- export ---------------------------------------------------------------------

    @_tool
    def export(self, audit_records=()):
        """Gated export (design decision 7): autonomy-gated types or human
        accepts only; rejected claims never; anchors, checks, coverage and
        the run semantic digest always."""
        if not self._opened():
            return envelope(REFUSED, "session.unopened", {})
        audits = list(audit_records or ())
        for record in audits:
            if not isinstance(record, dict) or not {
                    "claim_type", "evidence_class", "n", "errors"} <= set(record):
                return self._spec_refused("spec.invalid")
            if not isinstance(record["claim_type"], str) or \
                    not _is_int(record["n"]) or not _is_int(record["errors"]):
                return self._spec_refused("spec.invalid")
        accepted = {
            (c["type"], tuple(sorted(c["anchors"])), c["value"])
            for c in self.claims
            if c.get("origin") == "human"
            and (c.get("digest_input") or {}).get("decision") == "accept"}
        types = {c["type"] for c in self.claims}
        gated = {t for t in types if gate_open(t, audits)}
        records, rejected, ungated = [], 0, 0
        for claim in sorted(self.claims, key=lambda c: c["id"]):
            key = (claim["type"], tuple(sorted(claim["anchors"])),
                   claim["value"])
            if claim["status"] == REJECTED:
                rejected += 1
                continue
            if claim["type"] not in gated and key not in accepted:
                ungated += 1
                continue
            record = export_record(claim)
            record["anchors"] = claim["anchors"]
            record["value"] = claim["digest_input"]["value"]
            records.append(record)
        coverage = self.descriptor.get("coverage", [])
        regions = self.descriptor.get("regions", [])
        return envelope(OK, "ok", {
            "claims": records,
            "excluded": {"rejected": rejected, "ungated": ungated},
            "coverage": {
                "declared": dict(sorted(Counter(
                    f"{c.get('feature')}/{c.get('status')}"
                    for c in coverage).items())),
                "regions_by_kind": dict(sorted(Counter(
                    r.get("kind") for r in regions).items())),
                "exported_anchors": sorted(
                    {a for record in records for a in record["anchors"]}),
            },
            "run_digest": self.run_digest,
            "checks_passed_total": sum(r["checks_passed"] for r in records),
        })
