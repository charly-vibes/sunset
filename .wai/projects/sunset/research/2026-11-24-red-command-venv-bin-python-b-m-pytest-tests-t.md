---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-v0j-anchor-derived-identity, pipeline-step:red]
---

RED: command=.venv/bin/python -B -m pytest tests/tracer/test_identity.py -q; result=1 failed in 0.11s; expected failure confirmed=both fresh interpreter processes exit 1 with ModuleNotFoundError: No module named 'dsc03.identity' (derive_id absent), parent asserts subprocess.CalledProcessError; failure is the missing behavior, not setup breakage (collection ok, stdlib-only imports).
