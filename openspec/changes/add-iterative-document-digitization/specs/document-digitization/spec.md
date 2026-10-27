## ADDED Requirements

### Requirement: Region-first iterative extraction

The digitizer SHALL propose source-anchored regions before per-region recognition and SHALL allow recognition and structural checks to trigger explicit split, merge, expansion, rerecognition and restructuring actions. Each action SHALL retain its triggering rule, input revisions, output revisions and source-coordinate transforms. Reprocessing SHALL invalidate the affected dependency closure, including cross-page relationships, while retaining unrelated valid artifacts.

#### Scenario: OCR exposes mixed columns

- **WHEN** a pinned rule detects mixed columns in recognized region r1
- **THEN** the next revision records a split of r1, recognizes its children and rechecks dependent structure while retaining r1 and unrelated outputs

#### Scenario: Geometry outside page frame

- **WHEN** a proposed region cannot resolve within its declared page frame
- **THEN** the proposal is rejected with a diagnostic and the previous valid state survives

### Requirement: Attributed content and structure

The digitizer SHALL preserve raw OCR, AI proposals and manual corrections as distinct attributed observations with source hashes, selectors and producer configuration.

#### Scenario: Normalization removes poetic whitespace

- **WHEN** search normalization collapses indentation or stanza whitespace
- **THEN** the original observation and source layout remain available and the normalized text has explicit derivation bindings

#### Scenario: Ambiguous continuation

- **WHEN** two next-page regions could continue an article
- **THEN** both candidate relationships remain attributed and unresolved instead of selecting a semantic winner silently

### Requirement: Poetic layout preservation

It SHALL preserve poem line breaks, stanza boundaries, indentation and geometry separately from normalized search text.

#### Scenario: Poem survives search normalization

- **WHEN** raw poem text is "  luna\nmar\n\n  sal" with three line boxes and a stanza boundary
- **THEN** layout text retains both indents and the empty line, searchable text may be "luna mar sal", and derivation maps each search token to its original line box

### Requirement: Unresolved structural alternatives

Article membership, authorship, captions, reading order and cross-page continuations SHALL remain explicit proposals with unresolved alternatives retained.

#### Scenario: Caption has two candidate images

- **WHEN** caption c1 has attributed links to images i1 and i2 with no resolving judgment
- **THEN** both links remain exported as alternatives and c1 is unresolved; no default first-image winner is emitted

### Requirement: DSC export compatibility

Exported descriptors SHALL satisfy deployed DSC requirements; pipeline-only metadata SHALL remain in a linked manifest unless separately approved as a core change.

#### Scenario: Pipeline fields stay outside the descriptor

- **WHEN** a run contains an attempt counter and a valid DSC geometry observation
- **THEN** the descriptor passes deployed 0.3 validation without an attempt-counter wire field, and its digest links to the pipeline sidecar

### Requirement: Deterministic orchestration and operation cache

The digitizer SHALL use versioned canonical operation keys binding all input digests, crop/render transforms, implementation dependencies, model identity, prompts, preprocessing, decoding and policy configuration.

#### Scenario: Changed prompt

- **WHEN** a prompt digest changes with source and crop unchanged
- **THEN** the previous inference operation is a cache miss while independent unchanged operations remain reusable

#### Scenario: Multiple fresh responses

- **WHEN** two fresh attempts for one operation produce different valid outputs
- **THEN** both survive with distinct output digests and the run manifest explicitly pins the selected attempt

### Requirement: Verified cache and stable selection

It SHALL verify cached bytes before reuse, use a pinned stable ordering for actions and record explicit selections among fresh attempts.

#### Scenario: Corrupt cache and shuffled action input

- **WHEN** a cached response fails its digest check and two actions arrive in reverse order of pinned priority
- **THEN** the cache is refused, no corrupt output is selected, and valid actions execute in the pinned order regardless of arrival order

### Requirement: Semantic decision determinism

Identical recorded inputs and policy SHALL produce identical semantic decisions.

#### Scenario: Execution envelopes differ

- **WHEN** two replays have identical selected artifact bytes and policy but different timestamps and wall times
- **THEN** canonical semantic outputs and action ordering are byte-identical while both execution envelopes are retained

### Requirement: Fresh inference variability

Unavailable provider revision identifiers SHALL be explicit; fresh AI responses SHALL NOT be claimed deterministic merely from decoding settings.

#### Scenario: Model revision cannot be pinned

- **WHEN** a provider exposes only a model alias and fresh outputs are "luna" and "una"
- **THEN** revision identity is recorded unavailable, both outputs retain distinct attempt attribution, and no fresh determinism claim is made

### Requirement: Semantic state equality

Cycle detection SHALL compare the versioned canonical graph of active regions, exact source geometry, selected raw/layout/search text, hypotheses, attribution, relationships, alternatives and coverage/check outcomes under pinned source and configuration. Canonical labeling SHALL preserve multiplicity and remove allocation-ID dependence.

#### Scenario: Allocation IDs change

- **WHEN** two states differ only in newly allocated revision IDs
- **THEN** their canonical semantic graphs are equal

### Requirement: Cycle projection boundaries

Revision/history IDs, timestamps, counters, attempt IDs and resource envelopes SHALL be excluded from cycle equality; original evidence SHALL remain retained. Pending actions SHALL derive only from projected state and pinned policy. Immediate equality SHALL mean stable-state; nonadjacent equality SHALL mean repeated-state.

#### Scenario: Duplicate geometry does not merge identity

- **WHEN** state A contains two equal-geometry nodes with distinct graph roles and state B contains only one
- **THEN** their projections differ because node multiplicity is preserved

### Requirement: Bounded execution and honest stopping

The digitizer SHALL pin refinement-round, provider-attempt and monetary limits before execution, including currency, price-schedule digest and bounded request sizes.

#### Scenario: Next call exceeds remaining budget

- **WHEN** a proposed call cannot reserve its bounded charge within the remaining allowance
- **THEN** no call is dispatched and the run retains the last valid result with budget-exhausted diagnostics

#### Scenario: Region loop oscillates despite fresh IDs

- **WHEN** state A splits into B and merges back into A with new revision IDs but identical active content, geometry, attribution, relationships and coverage
- **THEN** execution stops with repeated-state diagnostics and preserves all revisions

#### Scenario: Content change is not a cycle

- **WHEN** a new state differs only by a retained raw poem newline
- **THEN** its semantic projection differs and it is not stopped as a repeated state

### Requirement: Persistent budget accounting

The digitizer SHALL atomically persist reservations and attempt consumption before dispatch, retain uncertain charges across resume, count new inference attempts and charged failures, and settle each attempt at most once. Available allowance SHALL subtract settled charges and outstanding reservations.

#### Scenario: Duplicate receipt

- **WHEN** an attempt reserved at 70 micro-units settles at 60 and the same receipt arrives twice
- **THEN** the ledger records 60 settled, releases 10 once and consumes one inference attempt

### Requirement: Dispatch uncertainty reconciliation

Uncertain requests SHALL be reconciled by status lookup or guaranteed idempotency binding the same key and payload to one execution/charge. Without either, automatic redispatch and reservation release SHALL be refused until evidence resolves uncertainty. Guaranteed-idempotent retransmission SHALL reuse the original key and reservation; a new inference attempt SHALL consume a new allowance.

#### Scenario: Crash leaves an uncertain charge

- **WHEN** the cap is 100 micro-units, an attempt reserves 70, and the process crashes after dispatch but before a receipt
- **THEN** resume keeps 70 encumbered, refuses a new 40-unit attempt and reconciles the original request before settlement or retransmission

#### Scenario: Unreconcilable request is not resent

- **WHEN** a reserved request has an uncertain dispatch outcome and its provider offers neither lookup nor guaranteed idempotency
- **THEN** resume retains the reservation, reports dispatch-uncertain and makes no automatic replacement call

### Requirement: Unbounded provider refusal

A provider without a safe cost bound SHALL be disabled under a hard monetary cap.

#### Scenario: Missing upper bound

- **WHEN** a provider supplies a unit price but no enforceable maximum output length under a hard monetary cap
- **THEN** configuration validation disables that route before dispatch and reports unbounded-cost

### Requirement: Explicit stop reasons

Stable state, repeated state, satisfied checks, exhausted budget and provider failure SHALL be distinct stop reasons; incomplete content SHALL retain unresolved diagnostics and SHALL NOT be reported complete because execution stopped.

#### Scenario: Budget stop retains incomplete poem

- **WHEN** a poem is unresolved and the next attempt would exceed the cap
- **THEN** status is stopped-with-unresolved-work with budget-exhausted reason, the poem remains unresolved and execution is not reported complete

### Requirement: Recorded replay and fresh-run verification

Recorded replay SHALL verify required artifact hashes and reconstruct identical canonical semantic outputs and decision traces without inference or network.

#### Scenario: Provider unavailable during replay

- **WHEN** all pinned artifacts are present but the original inference provider is unavailable
- **THEN** replay succeeds without provider access and reproduces the recorded semantic outputs

#### Scenario: Response artifact missing

- **WHEN** a pinned provider response is absent
- **THEN** replay reports incomplete artifacts and does not call a provider to fill the gap

### Requirement: Replay failure classification

It SHALL distinguish missing artifacts, integrity failure and unsupported versions.

#### Scenario: Corrupt and unsupported artifacts

- **WHEN** one replay has a response whose bytes fail its pinned hash and another has an intact manifest with an unsupported schema version
- **THEN** the first reports integrity-failure and the second unsupported-version; neither invokes inference or reports missing-artifact

### Requirement: Execution envelope retention

Execution timing and billing SHALL be retained outside semantic equality comparisons.

#### Scenario: Replay retains original billing

- **WHEN** a recorded envelope contains 70 micro-units charged and 300 milliseconds elapsed
- **THEN** replay integrity-checks and retains those values as original observations, excludes them from semantic equality and does not report them as fresh measurements

### Requirement: Fresh extraction verification boundary

Fresh extraction SHALL be a separately identified mode with measured output differences; recorded replay SHALL NOT imply that OCR or AI inference was independently reproduced or that its readings are correct.

#### Scenario: Fresh OCR changes one character

- **WHEN** recorded replay yields "luna" but a separately requested uncached run yields "una"
- **THEN** replay passes semantic equality, fresh verification records the character difference, and neither result certifies transcription correctness

### Requirement: Diario evaluation before scaling

The pilot SHALL pin its source pages, baseline, refinement policy, budgets, evaluation rules and acceptance thresholds before inference.

#### Scenario: No reviewed text reference

- **WHEN** only region annotations exist for an evaluated page
- **THEN** text accuracy is reported unknown until a reviewed transcription reference is supplied, while scoped region metrics may still be reported

#### Scenario: Loop costs more without measured improvement

- **WHEN** the loop consumes more resources than baseline and shows no measured quality improvement
- **THEN** the report retains that outcome and does not claim economical digitization or automatically approve full-issue scaling
### Requirement: Baseline comparison metrics

It SHALL compare whole-page OCR with the loop on the same difficult page and then the existing six-page Diario excerpt, measuring region quality, text errors, poetic layout, structural relationships, omissions, calls, cache reuse, estimated charges and runtime.

#### Scenario: Same pages and unknown denominator

- **WHEN** baseline and loop cover PDF pages 1 through 6 but page 4 has no reviewed text reference
- **THEN** the comparison pins identical source/page digests, reports page 4 text accuracy UNKNOWN with uncovered counts, and marks evaluation-incomplete rather than claiming six-page quality success

### Requirement: Correction effort measurement

Correction effort SHALL be measured or reported unknown.

#### Scenario: No correction timer

- **WHEN** outputs exist but no timed correction session was recorded
- **THEN** correction effort is UNKNOWN rather than zero and no reduced-human-effort claim is emitted

### Requirement: Scoped reviewed references

Quality references SHALL be independently reviewed for their declared scope; existing human region sheets SHALL NOT stand in for unrecorded transcription judgments.

#### Scenario: Region sheets lack transcription

- **WHEN** the only reviewed artifact records region geometry without any text judgment
- **THEN** geometry metrics cite that scope, text accuracy is UNKNOWN and the pilot quality/economy success gate remains blocked

### Requirement: Repeated fresh-run evaluation

At least two uncached difficult-page runs and one recorded replay SHALL distinguish fresh variation from replay equality.

#### Scenario: Cache hit cannot count as a fresh run

- **WHEN** one uncached difficult-page run, one cache reuse and one offline replay are available
- **THEN** the required second uncached run is missing, fresh variation is not declared measured, and replay equality is reported separately

### Requirement: Owner scaling decision

Scaling SHALL require an explicit owner decision grounded in reported results, including failures and reference/setup effort.

#### Scenario: Passing metrics do not authorize scaling

- **WHEN** all pinned pilot thresholds pass but the owner has not recorded a scaling decision
- **THEN** full-issue processing remains blocked; an explicit decision must cite the report including failed runs and reference/setup effort


### Requirement: Local run and inspection interface

The digitizer SHALL expose local run, resume, replay and inspect operations with documented exact invocation syntax. Run SHALL accept a PDF path, one-based PDF page selection, pinned configuration and new output directory. Invalid inputs SHALL be refused before inference; nonempty new output directories SHALL NOT be overwritten.

#### Scenario: Existing output directory

- **WHEN** run targets a nonempty output directory
- **THEN** it refuses before dispatch without changing existing files

### Requirement: Inspectable run outputs

Outputs SHALL include a manifest, source-linked searchable text, valid DSC descriptors, immutable artifacts/revisions, unresolved diagnostics, trace and ledger. Inspect SHALL expose source selectors, raw/layout/search text, alternatives, history, status and usage in human-readable and machine-readable form without requiring Lens.

#### Scenario: Inspect a partial page

- **WHEN** a local run on PDF page 2 yields poem p1 and unresolved caption c1
- **THEN** inspect shows p1 text and page/frame selectors, c1 unresolved, revision history and usage; the search-text mapping resolves p1 to that same page

#### Scenario: Invalid page selection

- **WHEN** page 7 is requested from a six-page PDF
- **THEN** run reports invalid-input with zero provider calls and does not overwrite existing artifacts

### Requirement: Reference completeness gates conclusions

Before candidate inference the pilot manifest SHALL pin independently reviewed source-linked reference digests, eligible units, exclusions, metric denominators and numerical thresholds. Missing required scopes or empty denominators SHALL yield evaluation-incomplete and block positive quality/economy or scaling conclusions. Engineering runs and negative decisions SHALL remain allowed.

#### Scenario: Missing reference permits engineering only

- **WHEN** no reviewed transcription exists for the difficult page
- **THEN** an engineering run may retain outputs but cannot pass the quality/economy gate

### Requirement: Minimum reviewed pilot scope

Difficult-page quality/economy success SHALL require full-page reviewed text and region/coverage plus poem layout and image/caption references, using an additional selected page if needed. Six-page success SHALL require reviewed text/layout and region/coverage for all six pages and a reviewed cross-page continuation with both endpoints. Unmeasured correction/setup costs SHALL preclude total-cost or human-effort improvement claims.

#### Scenario: Empty reference cannot pass

- **WHEN** a pilot defines zero eligible transcription units after exclusions
- **THEN** text accuracy is UNKNOWN, the report is evaluation-incomplete and quality/economy success is blocked despite low provider charges

#### Scenario: Reviewed pilot is eligible for assessment

- **WHEN** all required reviewed scopes and nonempty denominators are pinned before inference and both baseline and loop use those same scopes
- **THEN** the report evaluates the pinned numerical thresholds with exclusions and failures retained; a pass still requires an explicit owner decision before scaling


### Requirement: Real bounded local extraction route

Before measured pilots the digitizer SHALL integrate local region-first detection, real crop OCR, source-linked DSC inspection and whole-page baseline OCR with pinned configuration and usage. Integration SHALL require a separate bounded real local smoke run; fake-only tests SHALL NOT suffice. External routes SHALL remain disabled unless separately authorized.

#### Scenario: Local OCR is missing

- **WHEN** the configured OCR executable or language data is absent, or the engine exits unsuccessfully
- **THEN** the run retains provider-failure diagnostics and cannot emit an empty successful recognition or count a fake response as real integration evidence

#### Scenario: Local crop route is exercised

- **WHEN** an approved bounded local smoke run renders the selected page, detects regions from its image and invokes the pinned engine on their crops
- **THEN** public inspect exposes attributed OCR text, valid DSC source mappings, crop transforms and durable attempt records; whole-page baseline output uses the same pinned engine and no remote request occurs

### Requirement: Public resume continuity

Public resume SHALL reopen the original durable run from a fresh process, retain manifest identity/history/ledger and reconcile interrupted attempts without creating a replacement run, resetting allowances or double settlement. Unsupported resume SHALL NOT satisfy the completed budget checkpoint.

#### Scenario: Fresh process resumes uncertain attempt

- **WHEN** a process terminates after a durable 70-unit dispatch intention under a 100-unit cap and a fresh process invokes documented resume with no provider lookup or idempotency guarantee
- **THEN** it reports stopped-with-unresolved-work / dispatch-uncertain on the same run, retains 70 encumbered and the original attempt/history, and makes zero replacement calls

### Requirement: Reproducible pilot scoring

The digitizer SHALL expose a documented local evaluate operation shared by both pilot stages, computing region/text/layout/relationship metrics without inference and retaining input/configuration/report digests, numerators, denominators, exclusions and error witnesses. Metric policies SHALL be pinned and verified with numeric known-answer fixtures before pilot inference. Missing required scopes or zero denominators SHALL block positive conclusions.

#### Scenario: Character error arithmetic

- **WHEN** identity-normalized reference text is "ab", baseline is "ac" and candidate is "ab"
- **THEN** evaluation reports baseline CER 1/2 = 0.5 and candidate CER 0/2 = 0, and an empty eligible text reference instead yields UNKNOWN/evaluation-incomplete

#### Scenario: Unmatched regions and relationships remain errors

- **WHEN** a pinned one-to-one IoU policy matches exactly one of two candidate boxes to one of two reference boxes, and one of two reviewed directed continuation edges is replaced by a wrong endpoint
- **THEN** region precision and recall are both 1/2 with one missed and one spurious box, and continuation scoring retains one missing edge over two reference edges plus one spurious edge with endpoint witnesses

#### Scenario: Poem boundary scoring

- **WHEN** one of two reviewed line-break boundaries is lost in candidate layout text
- **THEN** evaluation reports one missing boundary over two eligible boundaries, error 0.5, separately from normalized search-text accuracy

### Requirement: Stage-specific reference and configuration approval

Difficult-page inference SHALL require its own approved bounded configuration and declared assessment or engineering-only mode; six-page references SHALL NOT block it. Six-page inference SHALL require a separate approved manifest freezing that stage's references, configuration and thresholds. Engineering-only approval SHALL name missing scopes and SHALL NOT permit positive quality/economy or scaling conclusions; earlier evidence SHALL remain unchanged.

#### Scenario: Difficult-page experiment precedes six-page references

- **WHEN** difficult-page references and bounded settings are approved but the other five pages lack reviewed transcription
- **THEN** the difficult-page assessment may proceed after local integration, while six-page assessment remains blocked pending its separate reference/configuration approval

#### Scenario: Engineering approval does not pass quality

- **WHEN** the owner approves a bounded engineering-only configuration with missing difficult-page transcription
- **THEN** local integration and engineering execution may proceed, reports mark the missing scope and evaluation-incomplete, and positive quality/economy/scaling conclusions remain blocked
