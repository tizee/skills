---
name: tlaplus
description: Model-check concurrent, stateful, and failure-prone designs with TLA+ and TLC. Use whenever the user mentions TLA+, TLC, formal verification, model checking, invariants, liveness, race conditions, distributed protocols, retries, timeouts, queues, idempotency, or cross-device sync, or asks to prove that a design cannot lose, duplicate, or reorder messages. Also use proactively when changing code that coordinates concurrent workers, background jobs, caches, leases, or multi-step workflows, even if the user does not ask for a spec -- a small TLA+ model often finds the bug faster than another round of tests. Do not use for pure algorithm proofs (use Lean) or simple sequential code.
---

# TLA+ model checking

Use TLA+ to find design bugs that tests miss: races, lost or duplicated messages, stale leases, non-idempotent retries, and deadlocks. TLC explores the interleavings of a small model exhaustively (or samples them in simulation) and returns a concrete trace when a property fails.

The deliverable is not a pretty spec. It is a runnable model, the properties you checked, and either a counterexample trace or a bounded pass with its assumptions stated.

## Decide whether TLA+ is the right tool

Use it when the bug depends on ordering or failure:

- concurrent workers, locks, leases, leader election
- queues, retries, timeouts, visibility timeouts, idempotency
- message loss, duplication, reordering, partitions
- cross-device or cross-service sync, cache coherence
- multi-step workflows with partial failure (saga, 2PC)
- protocols where "it works on the happy path" is not enough

Skip it when:

- the bug is a pure function or algorithm error: use property tests, or Lean for a proof
- the bug is a type or shape error: use the compiler, types, or a schema
- the bug is single-threaded control flow: use tests or a debugger
- the model would need to mirror implementation details: raise the abstraction or use runtime verification

Read `references/triage.md` when the choice is unclear.

## Cheaper constraints first

TLA+ is one layer of a quality system, not the first line. Before writing a spec, ask:

1. Can a type, schema, or API signature make the bad state unrepresentable?
2. Can a lint rule, CI check, or database constraint reject it?
3. Can a deterministic test reproduce it?
4. Only then: is the remaining risk an interleaving or failure-ordering problem?

This order matters. A spec that proves a design the codebase cannot express is wasted work. Fix the codebase and the enforceable constraints first. Use TLA+ for behavior that static analysis cannot express.

## The loop

### Step 0: Write the question in one sentence

Name the bug class before you write a line of TLA+.

- Good: "Can two workers process the same job after a visibility timeout?"
- Good: "Can a device that reconnects receive the same notification twice?"
- Bad: "Verify the notification system."

If you cannot name the question, stop. A spec without a question becomes a second implementation with no owner.

### Step 1: Build the smallest model

Model the protocol, not the code.

- **State variables**: only what the property needs. Messages are tokens, not payloads. Time is an ordering or a boolean, not milliseconds.
- **Actions**: one atomic step each. Name them after the real operations (`Claim`, `Complete`, `Retry`, `Crash`). Comment the code function each action maps to.
- **Environment**: include only failures that can produce the bug class: crash, timeout, duplicate delivery, reorder, partition, clock skew.
- **Constants**: start with 2-3 nodes and 1-2 items. Small scopes find shallow bugs quickly.
- **TypeOK**: always add it. It catches modeling mistakes such as a variable becoming the wrong shape.

Atomicity is a modeling decision. If you merge "claim" and "remove from queue" into one action, you hide the race between them. Model the real commit point, not the operation you wish were atomic.

### Step 2: Write properties before running

- **Safety**: nothing bad happens. `NoDoubleClaim`, `NoLostNotification`, `AtMostOneLeader`.
- **Liveness**: something good eventually happens. `EventuallyDone`, `EventuallyDelivered`. Liveness needs fairness; without it, TLC reports a stuttering trace that may not be a real bug.
- **TypeOK**: every variable stays in its intended domain.

Prefer properties that a reviewer can read without knowing the actions. Avoid properties that merely restate the next-state relation.

### Step 3: Run TLC

Run the bundled script from this skill. It downloads `tla2tools.jar` into the user cache on first use and keeps TLC metadata out of the repository.

```bash
bash scripts/tlc specs/notifications/Notify.tla
bash scripts/tlc --workers 1 specs/notifications/Notify.tla specs/notifications/Notify.cfg
```

If your working directory is not the skill directory (the directory that contains this `SKILL.md`), use the absolute path to `scripts/tlc`.

Useful options:

```bash
bash scripts/tlc --workers auto spec.tla          # larger models, less deterministic traces
bash scripts/tlc --simulate --depth 100 --timeout 60 spec.tla # random traces, stop on timeout
bash scripts/tlc --timeout 120 spec.tla          # requires the timeout command
```

Exit codes:

| Code | Meaning | Next move |
| --- | --- | --- |
| 0 | No error found in the explored state space | Validate the spec, then map back to code |
| 10 | An `ASSUME` is false | Fix the constants or the assumption |
| 11 | Deadlock | Decide whether the terminal state is legal; if not, fix the model or code |
| 12 | Safety invariant violated | Read the trace; this is the usual deliverable |
| 13 | Temporal property violated | Read the trace; check fairness and the liveness property |
| 150/151/255 | Parse, semantic, or config error | Read the first error; check the module name, config name, and constants |
| other | TLC error | Read the first `Error:` line; the exit code alone is not enough |

### Step 4: Read the counterexample

TLC prints each state with its variable values and the action that produced it. Find the first state where the property fails. The action that led there is the suspect.

Map the trace to real code:

- Which function or line implements each action?
- Which interleaving does the trace represent? Two workers, a timeout, a reconnect, a crash?
- Is the model wrong (an impossible interleaving) or is the code wrong (a real bug)?

If the model is wrong, fix the model and rerun. Do not weaken the property to make the model pass.

### Step 5: Validate the spec before trusting a green run

A passing TLC run proves only that the model satisfies the properties under the stated assumptions. Validate the spec itself:

- **Mutation test**: remove the guard, dedupe check, or fencing token and rerun. If the property still passes, the property is vacuous or the model never exercises the bug. Restore the mutation after the test.
- **Coverage probe**: add a temporary invariant that is the negation of "all interesting behaviors were reached" (duplicate delivery, crash inside the transaction, the skip path). Run TLC; a violation is the good outcome. Remove the probe before the final run.
- **Coverage**: every action fired; the state count is more than 1; the search depth is plausible. A one-state model proves nothing.
- **Assumptions**: constants are bounded, fairness is intentional, and `CHECK_DEADLOCK` matches the design. Document each assumption in the README.
- **Abstraction**: the bug you fear must be representable. If the model cannot express the bad interleaving, it cannot find it.

Simulation is not exhaustive and does not stop at `--depth`; it keeps generating traces until it is interrupted or reaches coverage. It is useful for safety traces, not for liveness proofs. Always pair it with `--timeout` when you want a quick look. For an exhaustive search with a bound, add a state `CONSTRAINT` to the `.cfg` (for example, `CONSTRAINT DepthBound` with `DepthBound == clock < 8`). State the bound in the README.

### Step 6: Map the result back to code

- Fix the root cause in code, not only in the spec.
- Add a regression test that reproduces the interleaving: two workers, a pause between claim and complete, a timeout, a reconnect.
- If the fix changes the design, update the spec first, then the code. Keep them in sync.
- Record the mapping in the README: action -> code function, invariant -> database constraint or test.

### Step 7: Commit the spec with the code

Keep the spec next to the code it describes:

```
specs/<feature>/
├── <Feature>.tla
├── <Feature>.cfg
└── README.md
```

The README must state:

- the question and the bug class
- the model scope and assumptions
- state variables and actions, mapped to code
- safety and liveness properties
- how to run the spec
- results: pass or counterexample, state counts, depth
- findings and code changes
- known limits

Run the spec in CI with small constants. A spec that is not executed is documentation, and documentation rots. If the full state space is too large, add a state `CONSTRAINT` to the `.cfg` and state the bound; run the deeper search locally.

Keep the spec runnable without the agent's local skill directory. Commit the raw `java -cp tla2tools.jar tlc2.TLC ...` command in the README or a Makefile target, so a reviewer can rerun it. The skill runner is a convenience, not a repository dependency.

## Reading a trace: queue example

```text
State 2: <Claim(w1, j1)>
/\ inFlight = {<<w1, j1>>}
/\ queue = {"j1"}

State 3: <Claim(w2, j1)>
/\ inFlight = {<<w1, j1>>, <<w2, j1>>}
/\ queue = {"j1"}
```

The trace below is from a buggy variant where `Claim` adds a job to `inFlight` but leaves it in `queue`. A second worker can claim the same job before the first completes. The root cause is not "the queue is slow"; it is that claim and removal are not one atomic step, and completion does not check a fencing token. Fix the commit point or add a fencing token that `Complete` must present.

This is the shape of a useful result: a short trace, a named interleaving, and a root-cause fix.

## Modeling rules

- **Bound everything.** Use `0..N`, not `Nat`. TLC cannot enumerate an infinite set.
- **Abstract payloads.** Model a message as an id or a small record. Do not model JSON, strings, or timestamps unless the property depends on them.
- **Prefer sets and functions.** `[Node -> State]` is clearer than parallel variables, and `EXCEPT` keeps updates local.
- **Use symmetry for interchangeable nodes.** `SYMMETRY Symmetry` with a permutation set cuts the state space. Only use it when the nodes are truly symmetric.
- **Keep fairness narrow.** `WF_vars(Next)` is a blunt instrument. Prefer fairness on the actions that must progress.
- **Use `ASSUME` for constants.** Encode "at least one worker" or "quorum is a majority" as an assumption, not a comment.
- **Add `TypeOK`.** It catches many modeling errors before a property fails for the wrong reason.
- **Name actions after code.** A trace is easier to map back when `Claim` and `Complete` match the function names.

## Verification discipline

- **A green run is not a proof of the code.** It is a proof of the model, under the model's assumptions. State those assumptions.
- **Do not weaken an invariant to get green.** That is the formal-verification equivalent of deleting a failing test. If the invariant is wrong, explain why and change it deliberately.
- **Spend effort on verification, not generation.** Budget time to run TLC, read traces, mutate the model, and map findings back. A spec that is written but never run is prose.
- **Make the verification executable.** The script, the config, and the CI command are part of the deliverable. A reviewer must be able to rerun the result.
- **Earn trust with evidence.** Show the trace, the command, and the exit code. Do not claim "verified" without a run.
- **Fix the root cause.** A counterexample is a design signal, not a prompt to add a retry or a sleep.
- **Complement runtime verification.** TLA+ models design. Run the app, inspect logs, use DevTools, and take screenshots for implementation behavior. Neither layer replaces the other.

## TLA+ or Lean?

| Question | Tool |
| --- | --- |
| Can these concurrent actions interleave badly? | TLA+ / TLC |
| Can this protocol lose, duplicate, or reorder a message? | TLA+ / TLC |
| Can two leaders be active at once? | TLA+ / TLC |
| Is this pure algorithm correct for all inputs? | Lean, Coq, or property tests |
| Is this data structure's invariant preserved? | Lean or property tests |
| Does this implementation match the design? | Refinement plus tests, or runtime checks |

Read `references/triage.md` for the full decision table. Do not use TLA+ to prove a sorting algorithm; do not use Lean to find a lease-renewal race.

## References

| File | Read it when |
| --- | --- |
| `references/syntax.md` | You need exact TLA+ syntax, operators, config keys, or common errors |
| `references/patterns.md` | You need a starting shape for queues, retries, fan-out, leases, caches, or sagas |
| `references/pitfalls.md` | A run is slow, green but suspicious, or the trace is hard to interpret |
| `references/triage.md` | You are unsure whether TLA+, Lean, tests, or runtime checks fit |

Templates live in `templates/`. Copy `templates/Spec.tla` and `templates/Spec.cfg` to start a new spec, then replace the example actions. Copy `templates/README.md` for the spec report.
