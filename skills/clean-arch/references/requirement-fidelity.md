# Requirement Fidelity Checks

> Sources: Steve McConnell, *Code Complete 2* (ch. 3, 20, 22, 27); ISO/IEC/IEEE 29148 (requirements quality attributes); Google Engineering Practices (design + functionality as separate review axes)

The most expensive review miss is not a wrong `if` — it is a **mistranslated requirement**. Code can be architecturally clean, well-tested against its own assumptions, and still fail the user. Requirements and design errors are typically more costly than coding errors, and their share grows with project size. This file defines the gate that runs **before** any architecture lens.

The one-sentence version:

> A review does not verify "does this look like good code" — it verifies "was the requirement correctly turned into a system part that is easy to change, provable, readable, and controlled."

## Step 0: Locate the Requirement (Reviewability Gate)

Before reviewing any code, identify what the change claims to implement. Acceptable sources, in order of preference:

1. Linked PRD / issue / ticket with acceptance criteria
2. Task description or PR description stating user goal and constraints
3. Commit messages that state intent (weakest acceptable source)

**If no requirement source can be located, the change is not fully reviewable.** Do not silently degrade into an architecture-only review:

- Record it as an **Open Question / review blocker**: "Cannot map this change to a stated requirement or user scenario."
- Label the review output as **partial (structure-only)**.
- For non-trivial behavior changes, this alone justifies requesting a description before approval.

### Requirement Reviewability Check

When a requirement source exists, sanity-check that it is reviewable at all (condensed from ISO/IEC/IEEE 29148):

| Attribute | Failing signal |
|---|---|
| Unambiguous | Two reasonable readers would implement different behavior |
| Complete | Error paths, boundary values, or excluded scope unstated |
| Singular | One "requirement" bundles several independently verifiable behaviors |
| Verifiable | No way to write a test or check that proves it is met |
| Implementation-independent | The "requirement" already dictates *how*, foreclosing design options |

A requirement that fails these is itself a finding — flag it instead of guessing the intent and reviewing against your guess.

## Design Defect vs Behavior Bug

Keep these two failure classes separate; they need different evidence and different questions.

| | Design-level defect | Behavior bug |
|---|---|---|
| Symptom | Code works "as designed"; product still fails the user goal | Specific branch, state transition, boundary input, or failure path behaves wrongly |
| Reviewer question | "Which requirement does this implementation satisfy? What scenario or constraint is missing?" | "Is this logic correct on every branch? What about invalid input and failure paths?" |
| Evidence to demand | Requirement link, scenario walkthrough, requirement-to-test mapping | Diff, unit/integration tests, logs |
| Typical consequence | Feature gap, wrong workflow, painful evolution | Incident, data corruption, crash |

**The key judgment sentence**: if the code fully satisfies its existing tests but the product is still wrong, the defect is in requirement understanding or design decomposition. If the requirement and design are right but certain inputs or states misbehave, it is a behavior bug. Never let a green test suite close the requirement question.

## PRD-to-Code Mapping

For each requirement dimension present in the source, verify a corresponding implementation and test artifact exists.

| Requirement dimension | What to verify in the change | Mismatch class | Quick detection signal |
|---|---|---|---|
| Functional goal | Every stated user task/scenario has an entry point, branch, and test | Design defect | User story exists, but no code path or test can be pointed at |
| Business rules | Conditions, state machines, decision tables fully covered — including states/transitions the PRD implies | Both | Long if/case chains; status constants scattered; missing transitions |
| Interface contract | Input/output shape, error codes, compatibility, idempotency documented and tested | Design defect | Public API changed with no contract note or contract test |
| Performance / capacity | Stated budgets (latency, throughput, resource) addressed with measurement, not micro-tweaks | Design defect | Hand-optimization present, but no profile or budget evidence |
| Reliability / error recovery | Invalid input, failure recovery, boundary conditions handled per requirement | Behavior bug | Happy path only; no guards, no failure-path tests |
| Maintainability | Change is local; abstraction stable under the stated future direction | Design defect | Parallel edits across layers; duplicated rule |
| Verifiability | Each key requirement item maps to at least one test | Design defect | No requirement-to-test mapping can be constructed |

## Common Product-Level Defect Patterns

These pass every architecture check and still fail the user:

- **Silently narrowed requirement**: the implementation covers the easy subset (e.g., handles single-item orders when the PRD says orders); nothing marks the rest as out of scope.
- **Reinterpreted requirement**: the PRD's *what* was replaced by a convenient *how*, and the *how* is now hard-coded; future PRD evolution is foreclosed.
- **Missing scenario**: a stated user path (cancel, retry, concurrent edit, empty state) has no entry point or branch at all — absence does not show up in a diff, so actively enumerate scenarios against code paths.
- **Partial state machine**: some states/transitions from the PRD exist, others are unreachable or unrepresented; no error on entering the undefined region.
- **Dropped non-functional constraint**: correctness is met, but the stated performance, compatibility, idempotency, or audit constraint is nowhere in code or tests.
- **Acceptance criteria drift**: tests assert the implementation's behavior instead of the requirement's acceptance criteria — the suite is a mirror, not a proof.

## Requirement-to-Test Mapping

Tests are the evidence chain from requirement to code. Review what the tests *prove*, not whether they *exist*:

- Each key requirement item (functional goal, business rule, contract, error behavior) maps to at least one test that would fail if that requirement were violated.
- Coverage must include **boundary values, invalid/dirty input, and failure paths** — defects concentrate there, not on the nominal path.
- Happy-path-only tests on requirement-critical logic (money, auth, state transitions, data writes) are a **blocking** finding, not a nit.
- Combine with the deletion test (see review-checklist.md): a test that maps to a requirement but passes with the logic deleted proves nothing.

## Severity Mapping for Requirement Findings

| Finding | Severity |
|---|---|
| Core stated requirement not implemented, or silently replaced with different behavior | P0 |
| Required user scenario / state transition missing; requirement narrowed without acknowledgment | P1 |
| Happy-path-only tests on requirement-critical logic | P1 |
| Stated non-functional constraint (performance budget, compat, idempotency) unaddressed | P1-P2 by blast radius |
| No requirement-to-test mapping constructible, behavior plausibly correct | P2 |
| Change not traceable to any requirement source | P2 + review labeled partial |
| PR/commit description drifted from actual behavior | P3 |

## Review Comment Templates

- *Unclear mapping*: "I cannot map this change to a specific requirement or user scenario. Please link the PRD/issue item or describe the user goal and constraints this covers."
- *Design-level mismatch*: "This is a working implementation, but it fixes a *how* where the requirement states a *what* — future variants of the requirement will require rework. Consider keeping the decision behind a boundary."
- *Missing scenario*: "The requirement includes scenario X (e.g., cancellation mid-flow); I don't see a code path or test for it. Is it out of scope? If so, please state that explicitly."
- *Evidence gap*: "The logic looks right on the nominal path; I can't confirm the boundary/failure behavior required by the acceptance criteria. Please add a test covering that branch."
