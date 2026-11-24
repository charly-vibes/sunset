# Purpose: Deterministic render cache in front of the pinned render path
#   (sunset-7b4.6).
# Responsibilities: Derive a timestamp-free cache key covering EVERY
#   component that changes pixels — source sha256, page, dpi, crop binding
#   (render_cropbox), renderer identity (name/executable/version),
#   binarization mode, source simplification, and the declared extractor/
#   renderer lineages — so any component change forces a re-render while an
#   identical key reuses the stored pixels as a CacheHit carrying the key
#   digest; store rendered pixels beside a provenance record (format, key
#   digest, full key components, renderer identity, source sha256, stored-
#   bytes sha256) with no wall-clock field; verify stored pixels against the
#   recorded content digest on every load so a tampered, unparseable, or
#   partially missing entry is raised as the typed RenderCacheCorrupted and
#   handled as an explicit re-render — never silent stale reuse, never a
#   crash; and never cache RenderUnavailable outcomes (a missing renderer
#   may be installed later).
# Rationale: design D2 — the pinned renderer is byte-reproducible
#   (test_visual_render.py pins byte-identity), so content-addressed reuse
#   of rendered pixels is sound; design D5 — corrupted cache state is a
#   typed, explicitly-handled re-render (RenderCacheCorrupted caught at the
#   single call site), not a bare except. The cache is opt-in: callers route
#   through cached_render_page(..., render=...) with an injectable render
#   callable (the seam used by tests to count renders); review.py's existing
#   render.render_page call path is unchanged. Cache identity is timestamp-
#   free by construction: keys and records contain only digests and the
#   pinned config fields.
"""Deterministic, content-addressed render cache in front of render_page."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dsc03.visual.render import RenderConfig, Rendered, render_page

KEY_FORMAT = "sunset-render-cache-key-1"
RECORD_FORMAT = "sunset-render-cache-1"


class RenderCacheCorrupted(RuntimeError):
    """A stored cache entry failed verification and must not be reused.

    Distinct from render.RenderUnavailable and render.RenderCommandError:
    the renderer never ran for this outcome — the stored entry itself is
    tampered, unparseable, or incomplete. cached_render_page catches this
    typed exception at its single call site and re-renders; nothing else
    may swallow it.
    """


@dataclass(frozen=True)
class CacheHit:
    """Reused cached pixels: provenance is the key digest, not the clock."""

    config: RenderConfig
    data: bytes
    key: str
    status: str = "cache-hit"


def source_digest(pdf_path) -> str:
    """sha256 hex digest of the source document bytes (key component)."""
    return hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()


def key_components(config: RenderConfig, source_sha256: str) -> dict:
    """Every key component, named: any pixel-affecting change lands here.

    Pure function of the arguments — no filesystem, environment, or clock
    access — which is what makes the derived key deterministic across
    processes.
    """
    return {
        "format": KEY_FORMAT,
        "source_sha256": source_sha256,
        "renderer": {
            "name": config.renderer_name,
            "executable": config.renderer_executable,
            "version": config.renderer_version,
        },
        "page": config.page,
        "dpi": config.dpi,
        "crop": {"render_cropbox": config.render_cropbox},
        "mode": config.binarization.to_dict(),
        "source_simplification": config.source_simplification,
        "lineages": {
            "extractor": config.extractor_lineage,
            "renderer": config.renderer_lineage,
        },
    }


def cache_key(config: RenderConfig, source_sha256: str) -> str:
    """Deterministic sha256 key digest over the named key components."""
    blob = json.dumps(
        key_components(config, source_sha256),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _renders_dir(cache_dir) -> Path:
    return Path(cache_dir) / "renders"


def _entry_paths(cache_dir, key: str):
    directory = _renders_dir(cache_dir)
    return directory / f"{key}.json", directory / f"{key}.png"


def _atomic_write(path: Path, payload: bytes) -> None:
    """Write via a sibling temp file + rename so no torn entry is readable."""
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_bytes(payload)
    os.replace(tmp, path)


def _verify_record(record, key, config, source_sha256, pixels) -> None:
    """Raise RenderCacheCorrupted unless every stored field verifies."""
    if not isinstance(record, dict):
        raise RenderCacheCorrupted(f"cache record is not an object: {key}")
    if record.get("format") != RECORD_FORMAT:
        raise RenderCacheCorrupted(
            f"cache record format mismatch: {record.get('format')!r}"
        )
    if record.get("key") != key:
        raise RenderCacheCorrupted("cache record key does not match derived key")
    if record.get("components") != key_components(config, source_sha256):
        raise RenderCacheCorrupted("cache record components do not match derived key")
    if record.get("renderer") != {
        "name": config.renderer_name,
        "version": config.renderer_version,
    }:
        raise RenderCacheCorrupted("cache record renderer identity mismatch")
    if record.get("source_sha256") != source_sha256:
        raise RenderCacheCorrupted("cache record source digest mismatch")
    if record.get("pixels_sha256") != hashlib.sha256(pixels).hexdigest():
        raise RenderCacheCorrupted(
            "cache record pixels digest mismatch: stored pixels are stale or tampered"
        )


def _load_entry(cache_dir, config, source_sha256):
    """Stored pixels for this key, or None on a plain miss.

    Any verification failure raises the typed RenderCacheCorrupted; the
    caller re-renders. Never returns unverified bytes.
    """
    key = cache_key(config, source_sha256)
    record_path, pixels_path = _entry_paths(cache_dir, key)
    if not record_path.is_file() or not pixels_path.is_file():
        return None
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RenderCacheCorrupted(
            f"cache record unparseable: {record_path}"
        ) from exc
    pixels = pixels_path.read_bytes()
    _verify_record(record, key, config, source_sha256, pixels)
    return pixels


def _store_entry(cache_dir, config, source_sha256, data: bytes) -> str:
    """Persist pixels + provenance record; pixels first, record last."""
    key = cache_key(config, source_sha256)
    directory = _renders_dir(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    record_path, pixels_path = _entry_paths(cache_dir, key)
    record = {
        "format": RECORD_FORMAT,
        "key": key,
        "components": key_components(config, source_sha256),
        "renderer": {
            "name": config.renderer_name,
            "version": config.renderer_version,
        },
        "source_sha256": source_sha256,
        "pixels_sha256": hashlib.sha256(data).hexdigest(),
        "pixels_file": f"{key}.png",
    }
    _atomic_write(pixels_path, data)
    _atomic_write(
        record_path,
        (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8"),
    )
    return key


def cached_render_page(
    config: RenderConfig,
    pdf_path,
    cache_dir,
    render: Callable[[RenderConfig, object], "Rendered | object"] | None = None,
):
    """Render through the cache: CacheHit on a verified reuse, otherwise
    whatever the render callable returns (Rendered — also stored — or the
    typed RenderUnavailable, which is never cached).

    The render callable is injectable (default: the pinned
    render.render_page) so callers — and tests — can count or stub the
    underlying renders. A corrupted or missing entry yields a re-render
    through the typed RenderCacheCorrupted path, never stale bytes.
    """
    delegate = render if render is not None else render_page
    source_sha256 = source_digest(pdf_path)
    try:
        cached = _load_entry(cache_dir, config, source_sha256)
    except RenderCacheCorrupted:
        cached = None  # typed corruption handling: explicit re-render below
    if cached is not None:
        return CacheHit(
            config=config,
            data=cached,
            key=cache_key(config, source_sha256),
        )
    outcome = delegate(config, pdf_path)
    if isinstance(outcome, Rendered):
        _store_entry(cache_dir, config, source_sha256, outcome.data)
    return outcome
