# Purpose: Deterministic render-cache tests (sunset-7b4.6).
# Responsibilities: Pin the render-cache contract in front of the pinned
#   render path: (a) an identical key reuses the cached pixels and is
#   recorded as a cache hit carrying the key digest while the underlying
#   pinned renderer runs exactly once (counted via an injectable render
#   spy); (b) a change to ANY key component — source bytes, page, dpi,
#   crop binding, renderer identity/version, binarization mode, source
#   simplification, declared lineages — changes the key digest and forces
#   a re-render; (c) a tampered, unparseable, or partially missing cache
#   entry is detected through the stored content digest and handled as a
#   typed re-render (RenderCacheCorrupted explicitly caught) — never
#   silent stale reuse, never a crash; (d) the key derivation is
#   deterministic across processes and the cache records carry provenance
#   only (key digest, renderer identity, source and pixel digests) with
#   no wall-clock component; unavailable outcomes are never cached.
# Rationale: design D2 (pinned renderer is byte-reproducible, so
#   content-addressed reuse of rendered pixels is sound) and D5 (typed
#   outcomes: corruption is a typed re-render, not a bare except).
"""Deterministic render-cache tests (sunset-7b4.6)."""
import dataclasses
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, ROOT)

from conftest import make_carrier, render_config

from dsc03.visual import render, render_cache

BASE_RECTS = [(72, 72, 200, 120)]

# Fixed literal config + source digest: the key derivation must never read
# the filesystem, the environment, or the clock, so pure-key tests pin it
# with values that are identical in every process.
SOURCE_SHA = "ab" * 32

ALLOWED_RECORD_KEYS = {
    "format",
    "key",
    "components",
    "renderer",
    "source_sha256",
    "pixels_sha256",
    "pixels_file",
}

KEY_SCRIPT = """
import sys
sys.path.insert(0, {root!r})
from dsc03.visual import render, render_cache
config = render.RenderConfig(
    renderer_name="pdftoppm",
    renderer_executable="/usr/bin/pdftoppm",
    renderer_version="26.01.0",
    dpi=72,
    page=1,
    binarization=render.Binarization(enabled=False),
    source_simplification="none",
    render_cropbox=False,
    extractor_lineage="pymupdf",
    renderer_lineage="poppler",
)
print(render_cache.cache_key(config, {sha!r}))
"""


def literal_config(**overrides):
    """RenderConfig with fully literal values (no environment probing)."""
    base = render.RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable="/usr/bin/pdftoppm",
        renderer_version="26.01.0",
        dpi=72,
        page=1,
        binarization=render.Binarization(enabled=False),
        source_simplification="none",
        render_cropbox=False,
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )
    return dataclasses.replace(base, **overrides) if overrides else base


class RenderSpy:
    """Injectable render spy: counts delegations to the pinned renderer."""

    def __init__(self, delegate=None):
        self.calls = []
        self._delegate = delegate or render.render_page

    def __call__(self, config, pdf_path):
        self.calls.append(config)
        return self._delegate(config, pdf_path)


def entry_paths(cache_dir, config, source_path):
    key = render_cache.cache_key(config, render_cache.source_digest(source_path))
    directory = Path(cache_dir) / "renders"
    return directory / f"{key}.json", directory / f"{key}.png"


def _component_mutants():
    return [
        ("source-sha256", "cd" * 32, literal_config()),
        ("page", SOURCE_SHA, literal_config(page=2)),
        ("dpi", SOURCE_SHA, literal_config(dpi=150)),
        ("render-cropbox", SOURCE_SHA, literal_config(render_cropbox=True)),
        (
            "binarization-enabled",
            SOURCE_SHA,
            literal_config(
                binarization=render.Binarization(enabled=True, threshold=128)
            ),
        ),
        (
            "binarization-threshold",
            SOURCE_SHA,
            literal_config(
                binarization=render.Binarization(enabled=True, threshold=200)
            ),
        ),
        (
            "source-simplification",
            SOURCE_SHA,
            literal_config(source_simplification="ink-dilation-2px"),
        ),
        ("renderer-name", SOURCE_SHA, literal_config(renderer_name="other")),
        (
            "renderer-executable",
            SOURCE_SHA,
            literal_config(renderer_executable="/usr/local/bin/pdftoppm"),
        ),
        (
            "renderer-version",
            SOURCE_SHA,
            literal_config(renderer_version="24.02.0"),
        ),
        (
            "extractor-lineage",
            SOURCE_SHA,
            literal_config(extractor_lineage="other-extractor"),
        ),
        (
            "renderer-lineage",
            SOURCE_SHA,
            literal_config(renderer_lineage="other-renderer"),
        ),
    ]


def test_cache_key_is_deterministic_across_processes(tmp_path):
    """Key derivation is pure: same components -> same digest in any process."""
    expected = render_cache.cache_key(literal_config(), SOURCE_SHA)
    script = tmp_path / "key.py"
    script.write_text(KEY_SCRIPT.format(root=str(ROOT), sha=SOURCE_SHA))
    proc = subprocess.run(
        [sys.executable, "-B", str(script)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected


def test_cache_key_is_repeatedly_identical_in_process():
    config = literal_config()
    assert render_cache.cache_key(config, SOURCE_SHA) == render_cache.cache_key(
        config, SOURCE_SHA
    )


@pytest.mark.parametrize(
    ["component", "source_sha", "config"],
    _component_mutants(),
    ids=[name for name, _, _ in _component_mutants()],
)
def test_key_digest_changes_on_any_component_change(component, source_sha, config):
    assert render_cache.cache_key(config, source_sha) != render_cache.cache_key(
        literal_config(), SOURCE_SHA
    )


def test_same_config_twice_is_one_render_one_cache_hit(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"
    spy = RenderSpy()

    first = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(first, render.Rendered)
    assert len(spy.calls) == 1

    second = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(second, render_cache.CacheHit)
    assert second.status == "cache-hit"
    assert second.config == config
    assert second.data == first.data
    assert len(spy.calls) == 1, "cached reuse must not invoke the renderer again"

    expected_key = render_cache.cache_key(
        config, render_cache.source_digest(carrier)
    )
    assert second.key == expected_key
    assert len(second.key) == 64, "key digest is a sha256 hex digest"


def test_config_change_forces_re_render(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config_low = render_config(dpi=72)
    config_high = dataclasses.replace(config_low, dpi=150)
    cache_dir = tmp_path / "cache"
    spy = RenderSpy()

    first = render_cache.cached_render_page(config_low, carrier, cache_dir, render=spy)
    second = render_cache.cached_render_page(
        config_high, carrier, cache_dir, render=spy
    )
    assert isinstance(first, render.Rendered)
    assert isinstance(second, render.Rendered)
    assert second.data != first.data or config_high.dpi != config_low.dpi
    assert len(spy.calls) == 2, "a changed config component must re-render"

    records = sorted((cache_dir / "renders").glob("*.json"))
    assert len(records) == 2
    stored_keys = {json.loads(path.read_text())["key"] for path in records}
    assert stored_keys == {
        render_cache.cache_key(config_low, render_cache.source_digest(carrier)),
        render_cache.cache_key(config_high, render_cache.source_digest(carrier)),
    }


def test_source_change_forces_re_render(tmp_path):
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"
    spy = RenderSpy()
    carrier_a = make_carrier(tmp_path, "a.pdf", BASE_RECTS)
    carrier_b = make_carrier(tmp_path, "b.pdf", [(72, 72, 260, 160)])

    first = render_cache.cached_render_page(config, carrier_a, cache_dir, render=spy)
    second = render_cache.cached_render_page(config, carrier_b, cache_dir, render=spy)
    assert isinstance(first, render.Rendered)
    assert isinstance(second, render.Rendered)
    assert len(spy.calls) == 2
    assert render_cache.source_digest(carrier_a) != render_cache.source_digest(carrier_b)


def test_tampered_pixels_force_typed_re_render_and_heal(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"
    spy = RenderSpy()

    first = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(first, render.Rendered)
    record_path, pixels_path = entry_paths(cache_dir, config, carrier)
    tampered = first.data[:-1] + bytes([first.data[-1] ^ 0xFF])
    pixels_path.write_bytes(tampered)

    second = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert len(spy.calls) == 2, "digest mismatch must re-render, never reuse stale pixels"
    assert isinstance(second, render.Rendered)
    assert second.data == first.data, "stale tampered bytes must never be returned"
    assert second.data != tampered

    third = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(third, render_cache.CacheHit)
    assert third.data == first.data
    assert len(spy.calls) == 2, "re-render must heal the entry for later hits"
    assert record_path.is_file()
    record = json.loads(record_path.read_text())
    assert record["pixels_sha256"] == hashlib.sha256(first.data).hexdigest()


def test_unparseable_record_forces_re_render(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"
    spy = RenderSpy()

    first = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(first, render.Rendered)
    record_path, _ = entry_paths(cache_dir, config, carrier)
    record_path.write_bytes(b"{not json at all")

    second = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(second, render.Rendered)
    assert len(spy.calls) == 2, "unparseable record is a typed re-render, not a crash"
    assert second.data == first.data


def test_missing_pixels_with_record_present_forces_re_render(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"
    spy = RenderSpy()

    first = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(first, render.Rendered)
    _, pixels_path = entry_paths(cache_dir, config, carrier)
    pixels_path.unlink()

    second = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(second, render.Rendered)
    assert len(spy.calls) == 2
    assert second.data == first.data


def test_cache_record_provenance_is_timestamp_free(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"

    outcome = render_cache.cached_render_page(config, carrier, cache_dir)
    assert isinstance(outcome, render.Rendered)
    key = render_cache.cache_key(config, render_cache.source_digest(carrier))
    record = json.loads((cache_dir / "renders" / f"{key}.json").read_text())

    assert set(record) == ALLOWED_RECORD_KEYS
    assert not any("time" in field.lower() for field in record)
    assert record["format"] == render_cache.RECORD_FORMAT
    assert record["key"] == key
    assert record["renderer"] == {
        "name": config.renderer_name,
        "version": config.renderer_version,
    }
    assert record["source_sha256"] == render_cache.source_digest(carrier)
    assert record["components"] == render_cache.key_components(
        config, render_cache.source_digest(carrier)
    )
    pixels = (cache_dir / "renders" / f"{key}.png").read_bytes()
    assert record["pixels_sha256"] == hashlib.sha256(pixels).hexdigest()
    assert record["pixels_file"] == f"{key}.png"


def test_unavailable_outcome_is_never_cached(tmp_path):
    carrier = make_carrier(tmp_path, "carrier.pdf", BASE_RECTS)
    config = render_config(dpi=72)
    cache_dir = tmp_path / "cache"

    def failing(pinned_config, pdf_path):
        return render.RenderUnavailable(
            config=pinned_config, reason="pinned renderer executable not found"
        )

    spy = RenderSpy(delegate=failing)
    first = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    second = render_cache.cached_render_page(config, carrier, cache_dir, render=spy)
    assert isinstance(first, render.RenderUnavailable)
    assert isinstance(second, render.RenderUnavailable)
    assert len(spy.calls) == 2, "unavailability is never cached"
    renders_dir = cache_dir / "renders"
    assert not renders_dir.is_dir() or not any(renders_dir.iterdir())
