---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-v0j-anchor-derived-identity, pipeline-step:fix-review]
---

RO5U-FIXES: both low findings reviewed for cheapness — (1) profiles.py identity digest grammar float-equality: deferred, deliberately mirrors sibling resolve() ==-style checks; tightening to type-is-int would diverge from the additive-branch convention this file uses for every kind; (2) validator unreachable typed branch: kept intentionally so future wire changes degrade to typed invalid_shape rather than a guessed comparison (collision-refusal never guesses). No behavior-impacting fixes; no new tests needed. Tests pass: .venv/bin/python -B -m pytest tests/tracer/test_identity.py -q -> 22 passed; commands run after review confirm no regression.
