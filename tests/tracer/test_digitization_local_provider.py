"""Contract tests for the per-crop local OCR provider (sunset-rmx.15 slice B).

The regional route of tasks 2.4 recognizes text per proposed region: the crop
adapter must pin its transform math, its engine argv, raw-byte output and its
failure behavior (missing engine, nonzero exit, timeout -> typed
provider-failure, never a fabricated empty success) BEFORE the real smoke.
Deterministic fake runners prove wiring; fakes never launch a real engine and
the default suite spawns no subprocess of its own beyond test drivers.
Integration runs through digitization.providers.dispatch: the settled attempt
carries a zero monetary charge (local adapter, same durable attempt rules),
and an adapter failure must leave the reservation dispatch-uncertain.
"""

import io
import math
import subprocess
from pathlib import Path

import pytest

from digitization.budget import BudgetLedger
from digitization.providers import dispatch

ROOT = Path(__file__).resolve().parents[2]

POLICY = {'version': '1', 'currency': 'USD', 'max_refinement_rounds': 2,
          'max_provider_attempts': 4, 'max_estimated_cost_microunits': 100,
          'max_request_bytes': 4096, 'max_output_bytes': 8192,
          'price_schedule_sha256': 'c' * 64}


def fake_runner(outputs, exit_code=0):
    """Runner writing each argv's txt output; records argv for pinning."""
    calls = []

    def run(cmd, timeout):
        calls.append((list(cmd), timeout))
        Path(cmd[2] + '.txt').write_bytes(outputs.pop(0))
        return 'ignored-stdout', exit_code
    run.calls = calls
    return run


def raising_runner(error):
    def run(cmd, timeout):
        raise error
    return run


def test_crop_transform_pins_px_rect_clamped_with_padding():
    from digitization.crop_ocr import crop_transform
    # 300x400pt page rendered at 96dpi = 400x533px extent (floor of extent)
    transform = crop_transform([30, 40, 100, 20], 96, [400, 533], padding_pt=2)
    scale = 96 / 72.0
    x, y, w, h = 30, 40, 100, 20
    assert transform['crop_px'] == [
        max(0, math.floor((x - 2) * scale)), max(0, math.floor((y - 2) * scale)),
        min(400, math.ceil((x + w + 2) * scale)),
        min(533, math.ceil((y + h + 2) * scale))]
    assert transform['bbox_pt'] == [30, 40, 100, 20]
    assert transform['padding_pt'] == 2 and transform['dpi'] == 96
    assert transform['source_px'] == [400, 533]


def test_crop_transform_clamps_to_page_at_every_edge():
    from digitization.crop_ocr import crop_transform
    # region touching all four page edges: padding must be clipped, not wrapped
    transform = crop_transform([0, 0, 400, 533], 96, [400, 533], padding_pt=2)
    x0, y0, x1, y1 = transform['crop_px']
    assert (x0, y0) == (0, 0) and (x1, y1) == (400, 533)
    # degenerate one-point-tall box still yields a nonempty crop
    transform = crop_transform([10, 10, 5, 0], 96, [400, 533])
    assert transform['crop_px'][3] > transform['crop_px'][1]


def test_crop_png_extracts_exact_pixels():
    import pymupdf
    from digitization.crop_ocr import crop_png, crop_transform
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 10))
    pix.set_rect(pymupdf.IRect(0, 0, 20, 10), (255, 0, 0))
    pix.set_rect(pymupdf.IRect(10, 0, 20, 10), (0, 0, 255))
    transform = crop_transform([0, 0, 15, 10], 96, [20, 10], padding_pt=0)
    # 15pt at 96dpi = 20px: transform covers the whole strip 0..20px
    assert transform['crop_px'] == [0, 0, 20, 10]
    crop = crop_png(pix.tobytes('png'), transform)
    # inspect via direct Pixmap decode: an image-PDF roundtrip rescales pixels
    cropped = pymupdf.Pixmap(io.BytesIO(crop))
    assert cropped.width == 20 and cropped.height == 10
    assert cropped.pixel(2, 5) == (255, 0, 0)   # left half kept red
    assert cropped.pixel(12, 5) == (0, 0, 255)  # right half kept blue


def test_recognize_pins_argv_and_preserves_raw_layout_bytes():
    from digitization.crop_ocr import DEFAULT_LANG, recognize_crop
    poem = b"  Poes\xeda con  espacio\n\n\n    sangrado   intacto  \n"
    runner = fake_runner([poem])
    raw = recognize_crop(b'crop-bytes', lang=DEFAULT_LANG, runner=runner)
    assert raw == poem  # no stripping, no word-joining, stanza breaks intact
    (cmd, timeout), = runner.calls
    assert cmd[0] == 'tesseract'
    assert cmd[3] == '-l' and cmd[4] == DEFAULT_LANG
    assert isinstance(timeout, int) and timeout > 0


def test_recognize_feeds_crop_bytes_to_the_engine(tmp_path):
    """The engine receives exactly the crop PNG bytes it is handed."""
    from digitization.crop_ocr import recognize_crop
    seen = {}
    def run(cmd, timeout):
        seen['crop'] = Path(cmd[1]).read_bytes()
        Path(cmd[2] + '.txt').write_bytes(b'texto')
        return '', 0
    recognize_crop(b'exact-crop-png-bytes', runner=run)
    assert seen['crop'] == b'exact-crop-png-bytes'


def test_missing_engine_is_typed_provider_failure(monkeypatch):
    from digitization import crop_ocr
    # nothing in the default suite may reach a real process: Popen forbidden
    monkeypatch.setattr(subprocess, 'Popen',
                        lambda *a, **k: pytest.fail('real engine launched'))
    with pytest.raises(crop_ocr.LocalProviderFailure) as excinfo:
        crop_ocr.recognize_crop(b'crop', runner=raising_runner(FileNotFoundError(2, 'tesseract')))
    assert excinfo.value.reason == 'engine-unavailable'
    assert 'tesseract' in excinfo.value.detail


def test_nonzero_exit_is_provider_failure_without_empty_success():
    from digitization.crop_ocr import recognize_crop
    # language data missing: tesseract exits nonzero having written nothing
    runner = fake_runner([b''], exit_code=3)
    with pytest.raises(RuntimeError) as excinfo:
        recognize_crop(b'crop', runner=runner)
    failure = excinfo.value
    assert getattr(failure, 'reason', '') == 'engine-nonzero-exit'
    assert 'tesseract' in failure.detail


def test_timeout_is_typed_provider_failure():
    from digitization.crop_ocr import recognize_crop
    with pytest.raises(RuntimeError) as excinfo:
        recognize_crop(b'crop',
                       runner=raising_runner(subprocess.TimeoutExpired('tesseract', 120)))
    assert excinfo.value.reason == 'engine-timeout'


def test_engine_identity_pins_same_provider_as_whole_page_configs(monkeypatch):
    from digitization import crop_ocr
    calls = []
    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        class Result:
            stdout = 'tesseract 5.5.1\n leptonica-1.86.0\n'
            stderr = ''
        return Result()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    identity = crop_ocr.engine_identity()
    assert calls == [['tesseract', '--version']]
    assert identity['id'] == 'tesseract-ocr'
    assert identity['version'] == '5.5.1'


def test_local_provider_settles_dispatch_attempt_at_zero_charge(tmp_path, monkeypatch):
    from digitization.crop_ocr import local_provider
    monkeypatch.setattr(subprocess, 'Popen',
                        lambda *a, **k: pytest.fail('real engine launched'))
    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD',
                                 policy=POLICY)
    provider = local_provider(ledger, runner=fake_runner([b'region text']))
    receipt = dispatch(ledger, request_key='region-key-1',
                       payload=b'crop-png-bytes', maximum_charge=10,
                       provider=provider)
    assert receipt['charge'] == 0
    assert receipt['outcome'] == 'completed'
    assert receipt['attempt_id'] == 'attempt-1'
    reopened = BudgetLedger.open(tmp_path / 'ledger.json')
    assert reopened.attempts[0]['state'] == 'completed'
    assert reopened.settled == 0
    assert reopened.receipts[0]['receipt_id'].startswith('receipt-')


def test_local_provider_returns_raw_bytes_and_is_deterministic(tmp_path):
    from digitization.crop_ocr import local_provider
    poem = b'  l\xednea una\n\n  estrofa nueva  \n'
    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD',
                                 policy=POLICY)
    # a provider assumes dispatch already reserved its request key
    ledger.reserve(request_key='region-key-2', payload_sha256='a' * 64,
                   maximum_charge=10)
    provider = local_provider(ledger, runner=fake_runner([poem]))
    output, receipt = provider('region-key-2', b'crop-bytes')
    assert output == poem
    same = local_provider(ledger, runner=fake_runner([poem]))
    assert same('region-key-2', b'crop-bytes')[1]['receipt_id'] == receipt['receipt_id']


def test_local_provider_failure_leaves_dispatch_uncertain(tmp_path):
    from digitization.crop_ocr import local_provider
    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD',
                                 policy=POLICY)
    provider = local_provider(ledger, runner=fake_runner([b''], exit_code=3))
    with pytest.raises(RuntimeError):
        dispatch(ledger, request_key='region-key-3', payload=b'crop-bytes',
                 maximum_charge=10, provider=provider)
    reopened = BudgetLedger.open(tmp_path / 'ledger.json')
    assert reopened.attempts[0]['state'] == 'dispatch-uncertain'
    assert reopened.receipts == []
