# Triage: TLA+, Lean, tests, or runtime checks

Use the cheapest layer that can falsify the property. Formal verification is
not a status symbol; it is a tool for a specific class of question.

## Decision table

| Question | Best first tool | Why |
| --- | --- | --- |
| Can these concurrent actions interleave badly? | TLA+ / TLC | Exhaustive interleaving search over a small model |
| Can this protocol lose, duplicate, or reorder a message? | TLA+ / TLC | The failure model is part of the state |
| Can two leaders be active after a pause? | TLA+ / TLC | Time and failure ordering are explicit |
| Is this pure algorithm correct for all inputs? | Lean, Coq, or property tests | No concurrency; the question is functional correctness |
| Is this data structure's invariant preserved? | Lean or property tests | Algebraic or structural proof |
| Is this state unrepresentable? | Types, schema, API design | Prevent the state instead of checking it |
| Is this misuse forbidden? | Lint rule, CI check, compiler flag | Enforceable on every change |
| Does the app behave correctly in the real environment? | Runtime checks, tests, DevTools | The model is not the implementation |
| Is this a style or process rule? | Lint, CI, review checklist | Prose rules rot and cannot be enforced |

## TLA+ is the right fit when

- The bug depends on the order of events across two or more actors.
- The bug depends on a failure: crash, timeout, duplicate, reorder, partition.
- The state space is finite after abstraction: 2-3 nodes, 1-2 items.
- You can name the safety or liveness property in one sentence.
- A counterexample trace would tell you which interleaving to fix.

## TLA+ is the wrong fit when

- The question is "is this function correct for every input?" Use Lean or
  property-based tests. TLA+ can model a sequential algorithm, but the proof
  is not the point and the model is usually a worse implementation.
- The question is "can this state exist?" Use the type system, a schema, or an
  API boundary. Make it unrepresentable.
- The question is "does the button render?" Use a browser test or a screenshot.
  TLA+ has nothing to say about pixels.
- The model would need to mirror implementation details to be useful. Raise the
  abstraction or use runtime verification.
- The team will not run the spec in CI. A spec that is not executed is prose.

## Lean is the right fit when

- The property is about a pure algorithm or a data structure.
- You need a proof over an unbounded input domain.
- The code can be extracted or connected to the proof with a refinement
  argument.
- The cost of a proof is justified by the criticality of the algorithm.

Lean is a poor fit for a lease-renewal race, a message fan-out, or a retry
protocol. Those are temporal questions. Use TLA+.

## Tests and runtime checks are the right fit when

- The behavior depends on a real browser, device, network, or database.
- You need a regression test for a specific interleaving found by TLC.
- You want to check that the implementation matches the model's assumptions
  (for example, that the database enforces the unique constraint).
- The property is cheap to check on every run and does not need a proof.

TLA+ and runtime checks complement each other. The spec finds the design bug;
the test keeps the code from regressing.

## The quality stack

Order the layers by how hard they are to bypass:

1. **Codebase and API design.** Make the bad state hard to express.
2. **Static constraints.** Types, schemas, lint rules, compiler flags, CI.
3. **Verification.** Runtime checks, tests, TLA+ for temporal behavior, Lean for
   algorithms.
4. **Prose rules.** Skills, AGENTS.md, review comments. Useful for judgment,
   weak as enforcement.

This is the inverted pyramid: invest in the top layers first. A formal proof of
a design that the codebase cannot express is wasted work. A lint rule that
prevents the bug is cheaper than a model that finds it.

## Combining the layers

A practical loop for a concurrency-sensitive change:

1. Write the question and the property.
2. Build the smallest TLA+ model; run TLC.
3. If TLC finds a trace, fix the design or the code.
4. Add the enforceable constraint that prevents the class of bug: a unique
   index, a fencing token in the write path, a lint rule, a type.
5. Add a regression test that reproduces the trace.
6. Run the app or service and check the behavior in the real environment.
7. Keep the spec in CI with small constants.

The spec is not the deliverable by itself. The deliverable is the design
change, the constraint, and the test that keep the bug from coming back.

## Cost and latency

| Layer | Time to first result | Maintenance cost | Strength |
| --- | --- | --- | --- |
| Type or schema | Minutes | Low | Prevents a class of states |
| Lint or CI rule | Minutes | Low | Enforces on every change |
| Unit test | Minutes | Medium | Catches known cases |
| TLA+ model | Hours | Medium | Finds unknown interleavings |
| Lean proof | Days | High | Proves all inputs |

Start cheap. Escalate only when the cheaper layer cannot express the property.
