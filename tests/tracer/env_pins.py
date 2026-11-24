# Purpose: Centralized pin detection for the suites that shell out to pinned
#   native binaries (sunset-2uo).
# Responsibilities: Probe pdftoppm/pdftotext/pdfinfo (poppler 26.01),
#   tesseract + spa traineddata, and playwright; expose require_* gates that
#   SKIP with a precise reason on machines missing a pin and FAIL under
#   SUNSET_STRICT_ENV=1 (canonical CI). The pins here mirror the SUNSET_*
#   env vars centralized in .github/workflows/ci.yml.
# Rationale: the pinned-env suites previously hard-failed on mismatched
#   environments. Contract (sunset-2uo): a stock machine running plain
#   `uv run pytest` sees skips with reasons, never failures; the same skips
#   become failures under SUNSET_STRICT_ENV=1, so a mis-pinned canonical
#   environment cannot pass silently. Lives beside the tracer suites so the
#   three consumers import it as `import env_pins` without touching
#   tests/tracer/conftest.py.
# Pin notes: poppler 26.01 is the recorded render pin (fixtures/visual/
#   calibration.json renderer_version 26.01.0; the demo's pdftotext_version
#   assertion) and is built from the sha256-pinned freedesktop tarball in CI
#   — the Ubuntu archive (noble: 24.08) and conda-forge (starts at 26.02)
#   have no 26.01. Tesseract is gated on presence + spa because the suites
#   record but never compare the OCR version (the canonical workstation runs
#   5.5.4; canonical CI pins the Ubuntu 24.04 default 5.3.4).
import importlib
import os
import re
import shutil
import subprocess

import pytest

POPPLER_VERSION = "26.01"
TESSERACT_VERSION = "5.3.4"  # enforced in CI; recorded, never compared, here
OCR_LANG = "spa"
PLAYWRIGHT_VERSION = "1.65.2"
STRICT_ENV_VAR = "SUNSET_STRICT_ENV"


def strict_env():
    """True when every pin skip must surface as a failure (canonical CI)."""
    return os.environ.get(STRICT_ENV_VAR) == "1"


def skip_or_fail(reason):
    """Skip with `reason` on stock machines; FAIL with it under strict env."""
    if strict_env():
        pytest.fail(f"{STRICT_ENV_VAR}=1 (canonical CI): {reason}",
                    pytrace=False)
    pytest.skip(reason)


def _tool_version(argv, pattern):
    """First capture group the pattern matches in a pinned tool's output.

    Version banners of the poppler/tesseract CLIs land on stderr (and
    pdftoppm -v exits nonzero), so stdout+stderr are scanned and the exit
    status ignored.
    """
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in ((r.stdout or "") + (r.stderr or "")).splitlines():
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def poppler_status():
    """(ok, detail) for the pinned poppler: CLIs present AND 26.01.x."""
    missing = [t for t in ("pdftoppm", "pdftotext", "pdfinfo")
               if shutil.which(t) is None]
    if missing:
        return False, f"{', '.join(missing)} not on PATH (poppler-utils)"
    version = _tool_version(["pdftoppm", "-v"], r"pdftoppm version (\S+)")
    if version is None:
        return False, "pdftoppm on PATH but did not report a version"
    if not version.startswith(POPPLER_VERSION):
        return False, (f"poppler mismatch: pdftoppm {version} on PATH, "
                       f"pin requires {POPPLER_VERSION}.x")
    return True, f"pdftoppm {version} on PATH (pin {POPPLER_VERSION}.x)"


def tesseract_status():
    """(ok, detail) for the pinned OCR pass: tesseract present AND spa pack."""
    if shutil.which("tesseract") is None:
        return False, "tesseract not on PATH"
    version = _tool_version(["tesseract", "--version"], r"tesseract (v?\S+)")
    try:
        r = subprocess.run(["tesseract", "--list-langs"],
                           capture_output=True, text=True, timeout=60)
        langs = set((r.stdout or "").split())
    except (OSError, subprocess.SubprocessError):
        langs = set()
    if OCR_LANG not in langs:
        return False, (f"tesseract {version or 'unknown'} present but "
                       f"'{OCR_LANG}' traineddata missing (listable langs: "
                       f"{sorted(langs) or 'none'})")
    return True, f"tesseract {version or 'unknown'} with '{OCR_LANG}' pack"


def native_toolchain_status():
    """(ok, detail) for everything demo.run_extractors shells out to."""
    checks = (("poppler (pdftoppm/pdftotext/pdfinfo)", poppler_status()),
              (f"tesseract + {OCR_LANG}", tesseract_status()))
    bad = [f"{name}: {detail}" for name, (ok, detail) in checks if not ok]
    return (not bad), "; ".join(bad) or "all pinned native tools present"


def require_pinned_poppler():
    """Gate for suites that re-render or compare the recorded render config."""
    ok, detail = poppler_status()
    if not ok:
        skip_or_fail(f"pinned poppler unavailable: {detail}")


def require_native_toolchain():
    """Gate for the first-consumer demo suite (extractors + OCR + snapshots)."""
    ok, detail = native_toolchain_status()
    if not ok:
        skip_or_fail(f"pinned native toolchain unavailable: {detail}")


def import_playwright():
    """playwright.sync_api, or the strict-aware skip naming the missing dep."""
    try:
        return importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        skip_or_fail(
            f"playwright is not installed in this environment "
            f"(canonical CI: pip install playwright=={PLAYWRIGHT_VERSION} "
            f"+ playwright install chromium): {exc}")
        raise  # skip_or_fail always raises; unreachable
