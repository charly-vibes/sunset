## ADDED Requirements

### Requirement: Queue is a pure function

The review queue SHALL be derived solely from the descriptor, claims and recorded policy, containing exactly the claims whose status is unverified or conflicted, in deterministic order of scope, claim type and claim id.

#### Scenario: Two processes

- **GIVEN** identical inputs and policy
- **WHEN** the queue is derived in two separate processes
- **THEN** the queues are identical

### Requirement: Complete review items

Each queue item SHALL carry a pinned crop reference, the canonical value, the verifier reason codes and every retained alternative with its origin.

#### Scenario: Conflicted claim

- **GIVEN** a conflicted claim with two alternatives
- **WHEN** its queue item is read
- **THEN** both alternatives and their origins are present

### Requirement: Decisions are non-destructive evidence

Accept, reject and edit SHALL each be recorded as a human-origin claim, and no decision SHALL modify or delete the model claim it concerns.

#### Scenario: Edit

- **GIVEN** a model claim a reviewer edits
- **WHEN** the edit is saved
- **THEN** the original claim is unchanged and a new human claim records the edit

### Requirement: Deterministic audit sampling

Audit samples SHALL be drawn from auto-accepted claims by a seeded procedure at a recorded rate and minimum count per claim type, and the seed SHALL be recorded.

#### Scenario: Repeat draw

- **GIVEN** the same claims, seed and rate
- **WHEN** the sample is drawn twice
- **THEN** the two samples are identical

### Requirement: Evidence-gated autonomy

A claim type SHALL be exported without review only when its audited false-accept upper bound is within the recorded threshold over at least the recorded minimum number of human-audited claims, and otherwise its claims SHALL be queued, including when no audit data exists.

#### Scenario: No audit data

- **GIVEN** a claim type with no audited claims
- **WHEN** export is requested
- **THEN** its claims are queued and not exported

### Requirement: Evidence classes stay separate

Each audit result SHALL be labeled human or agent-executed, and only human results SHALL count toward the autonomy gate.

#### Scenario: Agent audit

- **GIVEN** audits labeled agent-executed that meet the threshold
- **WHEN** the gate is evaluated
- **THEN** the claim type remains queued
