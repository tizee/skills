# TLA+ pitfalls

Most bad TLA+ results come from the model, not from TLC. Check this list before
you trust a green run or explain a red one.

## The model hides the bug

- **Too-coarse atomicity.** If `Claim` removes the job from the queue in the
  same step, the visibility-timeout race cannot happen. Model the real commit
  point. Ask: "Between which two lines can another process act?"
- **Missing failure.** No crash, timeout, duplicate delivery, reorder, or
  partition means the model explores only the happy path. Add the smallest
  failure set that can produce the bug class.
- **Too-strong assumptions.** `ASSUME` that a node never pauses, a message is
  never duplicated, or clocks are perfect can make the bug unrepresentable.
  State assumptions explicitly and check whether the code enforces them.
- **Implementation-shaped model.** If the spec mirrors every branch of the
  code, it is a second implementation. Raise the abstraction: model the
  protocol, the commit points, and the failure modes.

## The property is vacuous

- **True by construction.** `Cardinality(delivered[d]) = Cardinality(delivered[d])`
  proves nothing. If the state is a set, duplicate delivery is impossible by
  definition; model the list or counter the code actually uses.
- **Guard too strong.** If an action's precondition can never be true, the
  action never fires and its property is never exercised. Check coverage.
- **Mutation test.** Remove the dedupe check, the fencing token, or the lock.
  If the property still passes, the property or the model is wrong.
- **Coverage probe.** Add a temporary invariant `Probe == ~(seenDup /\ seenCrash
  /\ seenSkip)` that records whether the interesting behaviors were reached.
  Run TLC and expect `Probe` to fail. A violation proves the model exercised
  those paths. Remove the probe before the final run.
- **One-state model.** A model with one reachable state proves only that the
  initial state is well typed. Check the state count and depth.

## Liveness traps

- **No fairness.** `Spec == Init /\ [][Next]_vars` allows stuttering forever.
  A liveness property then fails with a `Stuttering` trace that is not a real
  bug. Add `WF_vars(A)` for the actions that must progress.
- **Too much fairness.** `WF_vars(Next)` makes the whole next-state relation
  fair. It can hide starvation of one action. Put fairness on the specific
  actions that must progress.
- **Deadlock is not a liveness failure.** TLC reports deadlock separately.
  Decide whether the terminal state is legal. If it is, set
  `CHECK_DEADLOCK FALSE` and keep a liveness property to catch stuck states.
- **Liveness is expensive.** TLC checks temporal properties over the whole
  state graph. Keep liveness models small; run safety first.

## State explosion

- **Unbounded types.** `Nat`, `Int`, and `Seq(S)` are infinite. Use `0..N` and
  fixed slots.
- **Unbounded retry counters.** A token, attempt counter, or clock that only
  increases makes the state space infinite, especially when a timeout returns
  work to the queue. Bound it with a small constant and a guard.
- **Too many nodes or items.** Start with 2 nodes and 2 items. Increase only
  when the smaller model passes and you need more coverage.
- **Payloads in state.** Do not store JSON, strings, or timestamps unless the
  property depends on them. Use ids.
- **Interleaving every internal step.** Model only the steps that another
  process can observe. Collapse internal computation into one action.
- **No symmetry.** If nodes are interchangeable, add `SYMMETRY` with
  `Permutations(Nodes)`. Do not use symmetry when nodes have distinct roles.
- **No constraint.** For an exhaustive bound, add a state `CONSTRAINT` to the
  config. `-depth` is only for simulation and will not bound an exhaustive
  search.
- **Wrong tool for the size.** `--simulate --depth N` is random simulation, not
  a bounded proof. It runs until timeout or coverage. Use it to hunt shallow
  traces, then shrink the model for an exhaustive check with a `CONSTRAINT`.

## Spec drift

- **No mapping to code.** A spec that does not name the code functions it
  models becomes fiction. Put the mapping in the README.
- **No CI run.** A spec that is not executed rots. Add a small CI target with
  fixed constants and a state constraint.
- **No owner.** A spec without an owner is not maintained. Treat it like code:
  review changes, keep it green, update it with the design.
- **No assumptions section.** Readers cannot tell what the spec proves. State
  the failure model, the bounds, and what is deliberately omitted.

## Misreading the result

- **Green means the model is correct, not the code.** TLC proves the model
  under its assumptions. The code can still diverge. Use refinement notes,
  tests, and runtime checks to connect them.
- **Red does not always mean a code bug.** The model may allow an impossible
  interleaving. Decide whether the trace is real before you change code.
- **A short trace is a gift.** Fix the root cause it names. Do not add a retry,
  a sleep, or a lock without understanding which invariant it restores.
- **A long trace is a modeling smell.** If the trace has ten steps of setup,
  the model is probably too concrete or the property is too weak.

## TLC quirks

- `-depth` applies to `-simulate` only. For exhaustive search, use a
  `CONSTRAINT`.
- `Cardinality` requires `EXTENDS FiniteSets` and a finite set.
- `Head` and `Tail` are undefined on `<<>>`; guard with `Len(s) > 0`.
- `CHOOSE x \in S: P(x)` is undefined when no element satisfies `P`. Guard it.
- `SYMMETRY` is unsound if the property distinguishes symmetric nodes. Check
  that the property is invariant under the permutation.
- TLC metadata (`states/`) can pollute the spec directory. Use `-metadir` or
  the bundled runner.
- A Java heap error on a large model is a signal to shrink the model, not only
  to raise `-Xmx`.

## Debugging a spec

1. Run with `-workers 1` for a deterministic trace.
2. Add `TypeOK` and rerun; type errors often explain a strange property
   failure.
3. Use `--simulate --depth 20 --timeout 60` for a quick trace when the
   exhaustive search is too slow. Simulation is not a proof.
4. Add `Print` or `Assert` from the `TLC` module to inspect a state. Remove
   them before committing.
5. Reduce constants to the smallest values that still produce the bug.
6. If the trace is impossible, add the missing assumption or remove the
   impossible action. Do not weaken the property first.
