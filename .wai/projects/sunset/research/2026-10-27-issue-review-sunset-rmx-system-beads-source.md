---
tags: [pipeline-run:epic-orchestrator-2026-10-19-sunset-xx7-lens-mvp-orchestration, pipeline-step:claim]
---

* Issue review: sunset-rmx
System: Beads. Source: openspec/changes/add-iterative-document-digitization/{proposal.md,design.md,tasks.md,specs/document-digitization/spec.md}.
Scope: sunset-rmx and children .1–.14 (15 issues). Advisory; issue bodies/proposal unchanged.
Verdict: NEEDS_UPDATES. 0 CRITICAL, 1 HIGH, 3 MEDIUM, 0 LOW actionable findings.

** Pass 0: mechanical preflight
All 15 tickets have nonempty structured files arrays and base_commit matching HEAD 3f09292; recorded proposal digests match current files. Global bd dep cycles and local blocking-graph traversal find no cycles. Shared docs, pipeline, inspection, CLI and pilot manifest are already covered by co-modification/reanchoring notes, so PRE-002 risk is mitigated rather than a new finding. Proposed test paths are explicitly future files: their absence is expected, not staleness. No missing metadata or stale-touched findings.

** Pass 1: clarity
CLRT-001 MEDIUM — sunset-rmx.9, sunset-rmx.11, sunset-rmx.12: metric computation has no explicit executable owner or positive known-answer fixtures. .9 validates evidence and blocks unsupported conclusions; .11/.12 require reports but scope their files to fixtures. None requires a concrete computation command, reference-region matching implementation, CER arithmetic, layout/relationship scoring or expected numeric vectors. Implementation can finish with a manifest validator and leave pilot measurements to ad hoc work.
Fix: extend .9 to deliver a reproducible evaluation/report operation with known-answer baseline/candidate/reference inputs (e.g. raw ab vs ac => one substitution over two reference characters under the pinned policy, and empty denominator => UNKNOWN), region matching and layout/relationship error witnesses. Pin expected values/denominators and exact command in tests/tracer/test_digitization_evaluation.py; .11/.12 must invoke the same operation and retain config/output digests. Keep all thresholds chosen before candidate inference.

** Pass 2: scope and tracer bullets
No additional finding. Most slices cut across pipeline, artifacts, inspection and behavior tests; cycle and accounting slices have independently testable outcomes. .13 is an explicitly requested final verification checkpoint, not a substitute for the earlier features; no forced merge recommended. .10 mixes evidence preparation and human signoff but can remain a bounded gate if evidence availability is explicit.
Convergence after pass 2: 0 new CRITICAL; 0 new findings vs 1 previous; false-positive rate unmeasured; ITERATE (cannot assert <20% false positives).

** Pass 3: dependencies
DEP-001 MEDIUM — sunset-rmx.10 -> sunset-rmx.11: all-six-page references unnecessarily block the first difficult-page experiment. .10 requires all six text/layout/coverage scopes and the cross-page pair, with missing evidence keeping it open; .11 depends on .10. The design requires difficult-page evidence (and extra feature page if needed) for that assessment, and the larger reference set for the later six-page decision. This also prevents the engineering-run/UNKNOWN path from being scheduled.
Fix: scope .10 to difficult-page reference/config approval; add a separate six-page reference gate blocking .12. Permit separately labeled engineering evaluation-incomplete runs without positive claims. Freeze each stage's scopes/settings before that stage's inference. Wire actual tracker IDs using bd dep add after creating the six-page gate. Preserve the owner and budget gates.
Convergence after pass 3: 0 new CRITICAL; 1 new finding vs 0 previous (ratio undefined); false-positive rate unmeasured; ITERATE.

** Pass 4: source-plan alignment
ALIGN-001 HIGH — sunset-rmx.2, sunset-rmx.7, sunset-rmx.10, sunset-rmx.11: no ticket explicitly connects an actual local detector/OCR route to the new pipeline before the pilot. .2 uses recorded providers and disables real inference; .7 specifies dispatch/accounting but no actual engine integration; .10 selects settings; .11 executes the baseline/loop and lists report-only files. Thus every feature meter can pass with stubs while no real region-first extraction journey exists. Existing dsc03/demo.py:_ocr_pages (around line 126) and dsc03/substrate/oracles.py contain real Tesseract work, but neither their integration/reuse nor a bounded fresh regional call is assigned by the issue set.
Fix: add a vertical local-provider integration slice after .7 (and approved pinned engine configuration), blocking .11. Explicitly reuse/adapt current rendering/Tesseract paths as appropriate; deliver run(source)->region detection->real crop OCR->attributed DSC/text->inspect, and a whole-page baseline route using the selected local engine. Record engine/dependency versions, actual attempts/usage, failure diagnostics and disabled external routes. Test adapter invocation/output with deterministic fakes and require a separately recorded real local smoke run before the pilot; no paid service needed. Add files/metadata and task traceability. Do not require model choice before owner config approval.
Convergence after pass 4: 0 new CRITICAL; 1 new finding vs 1 previous; false-positive rate unmeasured; ITERATE.

** Pass 5: executability
EXEC-001 MEDIUM — sunset-rmx.2, sunset-rmx.7, sunset-rmx.8: command-line resume is left potentially unsupported. .2 explicitly permits unsupported resume; .7 tests accounting restart semantics but does not explicitly replace that CLI state or include __main__.py in its files; .8 owns CLI changes for replay only. Unit tests can pass while the documented resume operation still refuses real runs.
Fix: extend .7 with digitization/__main__.py ownership and a fresh-process CLI fixture: interrupt after durable reservation, invoke documented resume(run-directory), observe original manifest/history/ledger and no reset/double dispatch; assert it returns the specified status/reason and cannot silently create a new run. Retain negative uncertain-provider coverage and no-network stubs. Cover the same public invocation in .13's integration journey.
Convergence after pass 5: 0 new CRITICAL; 1 new finding vs 1 previous; false-positive rate unmeasured; ITERATE. Five passes completed; no convergence claim or independent validation claimed.

** Assessment
Slice quality Good; horizontal leakage Low; AFK/HITL clarity Good. Clarity Fair, scope Good, dependencies Fair, completeness Fair. Existing lanes, complexity grades, test-first/separate-tidy rules, header criteria and anti-goals are present. All feature AFK tickets have planned objective meters; no public API/invariant ticket is incorrectly graded S/M. Epic XL is explicitly not schedulable. Most blockers are genuine feature progression; no cycle or permission bypass found. Approval remains ungranted.

** Quality ledger
Changed: review tracking/research only. Verified: 15 issue bodies vs proposal contracts; files/base/digests; global and scope cycle checks; strict OpenSpec valid; inspected existing OCR and justfile full-suite discovery. Review: self-executed preflight + five passes; no external model/service used. Risks: runtime implementation absent, pilot settings/references absent, false-positive rate unmeasured. Next: fix four findings and rerun issue review before implementation approval. No code, proposal or implementation ticket fixes, commit or push.
