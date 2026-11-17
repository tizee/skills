# TLA+ syntax and TLC reference

A compact reference for writing specs. Keep it open while you write; do not
memorize it.

## Module skeleton

```tla
---- MODULE Queue ----
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Items, Workers
VARIABLES queue, inFlight, done

vars == <<queue, inFlight, done>>

Init ==
    /\ queue = Items
    /\ inFlight = {}
    /\ done = {}

Next ==
    \/ \E w \in Workers: Claim(w)
    \/ \E w \in Workers: \E j \in Items: Complete(w, j)

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

====
```

- The module name must match the file name (`Queue.tla`).
- The file ends with four or more `=`. A missing `====` is a parse error.
- `\*` starts a line comment. `(* ... *)` is a block comment.

## Definitions and equality

- `==` defines an operator: `Init == x = 0`.
- `=` compares values: `x = 0`.
- `#` and `/=` both mean "not equal". Prefer `#`.
- Definitions can take arguments: `Max(a, b) == IF a > b THEN a ELSE b`.
- `LET` introduces local definitions:

```tla
Next ==
    LET j == CHOOSE i \in Items: i \notin done
    IN Complete(j)
```

## State and actions

An action is a formula with primed variables. Every variable must be assigned
or declared unchanged.

```tla
Claim(w) ==
    /\ \E j \in queue:
        /\ queue' = queue \ {j}
        /\ inFlight' = inFlight \cup {<<w, j>>}
        /\ UNCHANGED done

Complete(w, j) ==
    /\ <<w, j>> \in inFlight
    /\ inFlight' = inFlight \ {<<w, j>>}
    /\ done' = done \cup {j}
    /\ UNCHANGED queue
```

- Prime only variables: `x' = x + 1`. You cannot write `(x + 1)'`.
- `UNCHANGED x` and `UNCHANGED <<x, y>>` mean the variables keep their values.
- An action that assigns only some variables is an error.
- `[Next]_vars` means "Next or stuttering". `<<Next>>_vars` means "Next and
  the variables change".
- `ENABLED A` is true in a state where action `A` can occur. It is useful for
  fairness and for detecting stuck states.

## Sets

```tla
x \in S
x \notin S
S \cup T
S \cap T
S \ T              \* set difference
S \subseteq T
SUBSET S           \* set of all subsets
UNION S            \* union of a set of sets
S \X T             \* Cartesian product
Cardinality(S)     \* requires FiniteSets
{ x \in S : P(x) } \* set filter
{ f(x) : x \in S } \* set map
```

Use bounded sets. `Nat` and `Int` are infinite; TLC cannot enumerate them.
Write `0..N` instead.

## Functions

```tla
f == [i \in 1..N |-> 0]          \* function from 1..N to 0
f[1]                              \* application uses brackets
g == [f EXCEPT ![1] = 42]         \* copy with one point updated
h == [f EXCEPT ![i] = @ + 1]      \* @ is the old value
DOMAIN f                          \* the function's domain
[S -> T]                          \* set of all functions from S to T
```

Functions are total on their domain. A partial function is a function whose
domain is a subset; model it explicitly if absence matters.

## Records and tuples

```tla
r == [id |-> 1, state |-> "ready"]
r.state
r2 == [r EXCEPT !.state = "done"]

t == <<"w1", "j1">>
t[1]                              \* tuples are 1-indexed
Len(t)
```

Tuples and sequences are the same structure in TLA+. `<<>>` is the empty
sequence.

## Sequences

```tla
s == <<1, 2, 3>>
Len(s)                            \* 3
Head(s)                           \* 1; undefined on <<>>
Tail(s)                           \* <<2, 3>>; undefined on <<>>
Append(s, 4)                      \* <<1, 2, 3, 4>>
s \o <<4>>                        \* concatenation
SubSeq(s, 2, 3)                   \* <<2, 3>>
```

`Seq(S)` is the set of all finite sequences over `S`. It is infinite even when
`S` is finite; bound it with a length constraint or use a fixed set of slots.

## Quantifiers and choice

```tla
\A x \in S: P(x)
\E x \in S: P(x)
\A x \in S, y \in T: P(x, y)
\E x \in S, y \in T: P(x, y)
CHOOSE x \in S: P(x)              \* some x satisfying P; undefined if none
```

`CHOOSE` is deterministic in TLA+ semantics but hard to read. Prefer an
explicit action parameter when the choice matters for the trace.

## Control flow

```tla
IF x = 0 THEN "empty" ELSE "full"

CASE x = 0 -> "zero"
  [] x = 1 -> "one"
  [] OTHER -> "many"
```

`CASE` arms use `->`; implication uses `=>`. Do not mix them.

## Temporal operators

```tla
[]P          \* always P
<>P          \* eventually P
P ~> Q       \* P leads to Q
WF_vars(A)   \* weak fairness on A
SF_vars(A)   \* strong fairness on A
[A]_vars     \* A or stuttering
<<A>>_vars   \* A and a change of vars
```

A typical spec:

```tla
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)
```

Fairness is part of the model, not a detail. Without fairness, TLC can report a
stuttering trace for a liveness property even when the system always makes
progress in practice. With too much fairness, you can prove liveness for a
system that starves an action. State why each fairness conjunct is there.

## Assumptions

```tla
CONSTANT N
ASSUME N \in Nat /\ N > 0
```

TLC evaluates `ASSUME` and fails if it is false (exit code 10). Use it for
properties of the constants that the model depends on. It is not a substitute
for an invariant over the state.

## TLC configuration

```tla
SPECIFICATION Spec

CONSTANTS
    Items = {"i1", "i2"}
    Workers = {"w1", "w2"}

INVARIANTS
    TypeOK
    NoDoubleClaim

PROPERTIES
    EventuallyDone

CONSTRAINT
    DepthBound

SYMMETRY
    Symmetry

CHECK_DEADLOCK FALSE
```

- `SPECIFICATION` names the temporal formula. Do not also set `INIT` and
  `NEXT` in the same config.
- `INVARIANTS` are state predicates checked in every reachable state.
- `PROPERTIES` are temporal formulas checked over the whole behavior.
- `CONSTRAINT` prunes states. It is the correct way to bound an exhaustive
  search: `DepthBound == clock < 8`.
- `SYMMETRY` names an operator that returns a set of permutations. The `TLC`
  module provides `Permutations(S)`.
- `CHECK_DEADLOCK FALSE` is correct when terminal states are legal (all work
  done). Leave it `TRUE` when a stuck state is a bug.
- Constants must be defined in the config, or declared with `CONSTANT` and
  assigned by `CONSTANTS`.

## Command line

```bash
java -cp tla2tools.jar tlc2.TLC -config Queue.cfg -workers 1 Queue.tla
```

Useful flags:

| Flag | Effect |
| --- | --- |
| `-workers N` | Number of workers. `1` gives deterministic traces. |
| `-simulate` | Random simulation instead of exhaustive search; safety traces only |
| `-depth N` | Simulation depth; only valid with `-simulate` |
| `-coverage N` | Print action coverage every N minutes |
| `-metadir DIR` | Put TLC metadata in `DIR` instead of the spec directory |
| `-cleanup` | Remove TLC metadata after the run |
| `-nowarning` | Suppress the GC warning |

TLC exit codes: `0` pass, `10` false assumption, `11` deadlock, `12`
invariant violation, `13` temporal property violation, `150/151/255` parse,
semantic, or config error.

## Common errors

| Error | Cause | Fix |
| --- | --- | --- |
| `Unknown operator` | Typo, or missing `EXTENDS` | Check the spelling and the module imports |
| `The variable ... is not defined` | Missing `VARIABLE` | Declare it |
| `The symbol ... is not assigned a value` | Action does not assign every variable | Add the assignment or `UNCHANGED` |
| `Attempted to compare values of different types` | A variable changed shape | Add `TypeOK`; find the action that produced the wrong shape |
| `TLC found a state with no successor` | Deadlock | Legal terminal state: `CHECK_DEADLOCK FALSE`; otherwise fix the action |
| `The configuration file does not define constant ...` | Missing constant | Add it to the `.cfg` |
| `Cannot enumerate an infinite set` | `Nat`, `Int`, or `Seq(S)` used directly | Bound the set (`0..N`, a fixed set of slots) |
| `Parsing error` | Missing `====`, unbalanced `/\`, `=>` vs `->` | Read the first error; fix the line it names |
| `File name ... does not match the name ...` | The module name and the file name differ | Rename the module or the file |
| `The name ... specified in the configuration file` | `SPECIFICATION` names a missing operator | Match the name after `SPECIFICATION` to the spec operator |
| `Temporal properties were violated` with `Stuttering` | No fairness, or a real stuck state | Add the right fairness conjunct, or fix the deadlock |
| `TLC threw an unexpected exception` | Semantic error in the spec | Read the first `Error:` line, not the last |
| `Assumption ... is false` | The constants violate an `ASSUME` | Fix the constants or the assumption |

## Reading TLC output

```text
Error: Invariant NoDoubleClaim is violated.
Error: The behavior up to this point is:
State 1: <Initial predicate>
/\ inFlight = {}
/\ queue = {"j1", "j2"}

State 2: <Claim line 19, col 5 to line 22, col 25 of module Queue>
/\ inFlight = {<<"w1", "j1">>}
/\ queue = {"j1", "j2"}
```

- The first `Error:` names the failed property.
- Each `State N:` shows the variable values and the action that produced them.
- `Stuttering` means the trace ended in a state with no successor.
- `N states generated, M distinct states found` tells you how much was
  explored. A small number is not automatically bad, but a single state is
  suspicious.
- `The depth of the complete state graph search is K` is the longest shortest
  path. If `K` is tiny, the model may be too abstract to exercise the bug.

## Sources

- TLA+ home: https://lamport.azurewebsites.net/tla/tla.html
- Specifying Systems: https://lamport.azurewebsites.net/tla/book.html
- TLA+ examples: https://github.com/tlaplus/Examples
- TLC options: `java -cp tla2tools.jar tlc2.TLC -help`
