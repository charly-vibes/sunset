# Purpose: Recognize text from one rendered-page crop with pinned tesseract.
# Responsibilities: Pin the crop transform math (y-down pt bbox -> clamped px
#   rect with declared padding), extract the crop pixels, run one tesseract
#   txt invocation per crop through an injectable runner, and expose a
#   dispatch-compatible local provider that settles its durable attempt at
#   zero monetary charge. Missing engine, nonzero exit and timeout raise
#   typed LocalProviderFailure — never an empty success.
# Rationale: sunset-rmx.15 regional route (tasks 2.4): recognition is per
#   proposed region; the whole-corpus demo is never invoked for a crop
#   (design: reuse decision, recorded here). The process-safety pattern is
#   adapted from dsc03.demo.run_pinned (file-backed stdout, WNOHANG polling,
#   timeout kill — the recorded pipe-deadlock lesson) with one deliberate
#   difference: the child exit status is surfaced, which the demo path
#   discards, because a nonzero tesseract exit must be a provider failure
#   rather than a silent empty result. Raw txt bytes are returned as-is —
#   no stripping or word-joining that would lose poem spacing (design:
#   preserve raw/layout over inheriting demo text cleanup).
"""Per-crop pinned tesseract adapter behind the dispatch boundary."""
import hashlib
import io
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path

PROVIDER_ID = 'tesseract-ocr'   # same identity as the whole-page configs
DEFAULT_LANG = 'spa'            # same approved language data
PADDING_PT = 2                  # declared crop context, design line "retain
                                # declared padding/context"
CROP_TIMEOUT_S = 120            # per-crop kill deadline


class LocalProviderFailure(RuntimeError):
    """Typed refusal: the engine ran (or could not start) without usable text."""

    def __init__(self, reason, *, detail=''):
        self.reason = reason
        self.detail = detail
        super().__init__(reason + (f': {detail}' if detail else ''))


def crop_transform(bbox, dpi, source_px, padding_pt=PADDING_PT):
    """Pin the crop rect: y-down pt bbox + padding -> clamped px rect.

    Floors the leading edges and ceils the trailing edges so padding is
    never clipped by rounding, then clamps to the actual render extent.
    """
    scale = dpi / 72.0
    x, y, w, h = bbox
    width_px, height_px = source_px
    x0 = max(0, math.floor((x - padding_pt) * scale))
    y0 = max(0, math.floor((y - padding_pt) * scale))
    x1 = min(width_px, math.ceil((x + w + padding_pt) * scale))
    y1 = min(height_px, math.ceil((y + h + padding_pt) * scale))
    if x1 <= x0:
        x1 = min(width_px, x0 + 1)
    if y1 <= y0:
        y1 = min(height_px, y0 + 1)
    return {'bbox_pt': [int(v) for v in bbox], 'padding_pt': padding_pt,
            'dpi': dpi, 'crop_px': [x0, y0, x1, y1],
            'source_px': [width_px, height_px]}


def crop_png(page_png_bytes, transform):
    """Extract the pinned px rect from a rendered page PNG as crop PNG bytes."""
    import pymupdf

    # direct Pixmap decode: the PNG is already the pinned render, and routing
    # it through an image PDF page would rescale pixels (observed 20x10 -> 12x6)
    pix = pymupdf.Pixmap(io.BytesIO(page_png_bytes))
    x0, y0, x1, y1 = transform['crop_px']
    width = max(1, min(pix.width, x1) - x0)
    height = max(1, min(pix.height, y1) - y0)
    stride = pix.width * pix.n
    buf = bytearray()
    for row in range(height):
        base = (y0 + row) * stride + x0 * pix.n
        buf += pix.samples[base:base + width * pix.n]
    cropped = pymupdf.Pixmap(pix.colorspace, width, height, bytes(buf), pix.alpha)
    return cropped.tobytes('png')


def _pinned_run(cmd, timeout):
    """Run one pinned child safely; return (stdout_text, exit_code).

    Adapted from dsc03.demo.run_pinned: stdout goes to a temp file, never a
    pipe (the child blocks writing past the pipe buffer while the parent
    blocks in os.wait4 — the recorded deadlock); WNOHANG polling with a hard
    timeout kill so a hung tesseract can never stall the caller. Unlike the
    demo path the exit status is surfaced.
    """
    fd, out_path = tempfile.mkstemp(suffix='.out')
    os.close(fd)
    try:
        with open(out_path, 'wb') as out_f:
            child = subprocess.Popen(cmd, stdout=out_f, stderr=subprocess.PIPE)
            deadline = time.monotonic() + timeout
            while True:
                pid, status, _ = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    child.returncode = os.waitstatus_to_exitcode(status)
                    with open(out_path, 'rb') as r_f:
                        return r_f.read().decode('utf-8', 'replace'), child.returncode
                if time.monotonic() > deadline:
                    child.kill()
                    os.wait4(child.pid, 0)
                    raise subprocess.TimeoutExpired(cmd, timeout)
                time.sleep(0.05)
    finally:
        os.unlink(out_path)


def engine_identity():
    """Pin the provider identity: same engine/version as whole-page configs."""
    try:
        result = subprocess.run(['tesseract', '--version'],
                                capture_output=True, text=True)
    except FileNotFoundError as error:
        raise LocalProviderFailure('engine-unavailable', detail=str(error)) from error
    first = (result.stdout or result.stderr).splitlines()[0]
    return {'id': PROVIDER_ID, 'version': first.split()[-1]}


def recognize_crop(crop_png_bytes, *, lang=DEFAULT_LANG, runner=_pinned_run,
                   timeout=CROP_TIMEOUT_S):
    """Run pinned tesseract over one crop; return raw txt bytes, layout kept."""
    with tempfile.TemporaryDirectory(prefix='.crop-ocr-') as tmp:
        crop_path = Path(tmp) / 'crop.png'
        base = Path(tmp) / 'out'
        crop_path.write_bytes(crop_png_bytes)
        argv = ['tesseract', str(crop_path), str(base), '-l', lang]
        try:
            _stdout, exit_code = runner(argv, timeout)
        except subprocess.TimeoutExpired:
            raise LocalProviderFailure('engine-timeout', detail=f'argv={argv}') from None
        except FileNotFoundError as error:
            raise LocalProviderFailure('engine-unavailable', detail=str(error)) from None
        out_path = Path(str(base) + '.txt')
        if exit_code != 0:
            raise LocalProviderFailure('engine-nonzero-exit',
                                       detail=f'exit {exit_code} argv={argv}')
        if not out_path.is_file():
            raise LocalProviderFailure('engine-no-output',
                                       detail=f'missing txt argv={argv}')
        return out_path.read_bytes()   # raw bytes: whitespace/stanzas preserved


def local_provider(ledger, *, lang=DEFAULT_LANG, runner=_pinned_run,
                   timeout=CROP_TIMEOUT_S):
    """Dispatch-compatible provider for per-crop recognition.

    The payload is the exact crop PNG bytes (the reserved attempt binds to
    them). Receipts are deterministic per request key, charge zero: local
    compute obeys the durable attempt rules without monetary cost.
    """
    def provider(request_key, payload):
        attempt = next((item for item in ledger.attempts
                        if item['request_key'] == request_key), None)
        if attempt is None:
            raise ValueError('unknown-request-key')
        raw = recognize_crop(payload, lang=lang, runner=runner, timeout=timeout)
        receipt = {'receipt_id': 'receipt-' + hashlib.sha256(
                       request_key.encode('utf-8')).hexdigest()[:24],
                   'attempt_id': attempt['id'], 'charge': 0,
                   'outcome': 'completed'}
        return raw, receipt
    return provider
