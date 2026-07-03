# Code Construction Rules and Anti-Patterns

> Source: Steve McConnell, *Code Complete 2*. The concurrency addendum draws on C++ Core Guidelines concurrency rules and CWE race-condition guidance, since CC2 has no dedicated concurrency chapter.

The architecture lenses in [review-checklist.md](review-checklist.md) operate at module/layer level. These checks operate **below** that — at function, statement, and variable level, where most diff lines actually live. Use this file when reviewing implementation diffs line-by-line.

The unifying mechanism compresses to three sentences:

> **Naming reduces explanation cost. Abstraction reduces how many things a reader must hold in mind at once. Tests provide verifiable evidence.** A review that loses sight of these three degenerates into format policing.

## Rule Domains

Default severities use this skill's P0-P3 rubric; escalation conditions are noted inline.

| Domain | Rule | Review question | Default severity | Fix direction |
|---|---|---|---|---|
| Naming | Names fully express the concept; no misleading, near-identical, or mixed-language names | Can a reader infer responsibility and data meaning from the name alone, without opening the body? | P3; P2 when a misleading name lies about behavior on a critical path | Rename; unify the team glossary; drop ambiguous abbreviations |
| Variables | Declare and initialize near first use; smallest possible scope; one variable, one purpose | Must the reader track state across a large span of code? | P2 | Split multi-purpose variables; shrink scope; initialize at declaration |
| Constants & types | Named constants, enums, booleans — never bare numbers or numeric flags | Does any literal encode a business concept without a name? | P2; P1 when the magic value governs money/auth/state writes | Promote to enum/named constant/boolean (see PIE checks in review-checklist.md) |
| Global data | Minimize global mutable state; access shared state through a narrow interface | Can a change here silently affect unrelated code? | P1 | Encapsulate in an object/module; inject dependencies |
| Classes & ADTs | A class has one central purpose; its public interface presents a single consistent abstraction | Do the name, interface, and members all serve the same abstraction? | P1-P2 | Split the class (see God Class in common-patterns.md); hide details |
| Cohesion & coupling | Strong cohesion, loose coupling, information hiding | Does changing one place force parallel edits elsewhere? | P1-P2 | Extract class/interface; break cycles (see Information Hiding checks) |
| Routines/functions | Do one thing; the name covers **all** behavior including side effects; few parameters; valid return on every path | Are there hidden side effects, too many parameters, or paths that return garbage? | P2; P1 for hidden side effects on state-writing paths | Split; introduce parameter object; make side effects explicit in the name |
| Control flow | Structured flow; shallow nesting; simple boolean expressions; the nominal path reads top-to-bottom | Does the reader *read* this code or have to *simulate* it? | P2 | Guard clauses, early return, extract function, simplify booleans |
| Unconventional control | Multiple returns only when they aid clarity; recursion only where the problem is recursive; goto (nearly) never; empty statements made explicit | Does any construct impose non-linear reasoning? | P2; P1 for implicit case fallthrough | Structured replacements; explicit `FALLTHROUGH` marker or rewrite |
| Table-driven methods | When branching encodes knowledge, prefer putting the knowledge in data, not logic | Could a lookup/decision table replace this repetitive conditional tree? | P3 (improvement suggestion) | Replace long if/case chains with a lookup or decision table |
| Comments | Code explains itself first; comments explain **why/intent**, never restate **what**; stay adjacent and current | Is this comment compensating for bad code, or speeding up a competent reader? | P3 | Rewrite the code first, then keep one intent/summary comment |
| Defensive programming | Guard invalid input; assert preconditions/postconditions; barricade to isolate errors at trust boundaries | Are boundaries, assumptions, and illegal inputs handled explicitly — or does correctness rely on callers behaving? | P1-P2 | Add guards/asserts at the boundary; validate at system edges only |
| Exceptions & errors | One project-wide error strategy; handle locally when possible; exception types match the interface's abstraction level; never throw from constructors/destructors of critical paths | Is the error channel consistent, and does it avoid leaking implementation detail to callers? | P1-P2 | Unify the error model; narrow catch scope; translate at boundaries |
| Tests as evidence | Tests cover every relevant requirement, branch, data flow, boundary, and dirty path | Not "are there tests" but "what do the tests prove"? | P1 (blocking on requirement-critical logic) | See [requirement-fidelity.md](requirement-fidelity.md) and Testing Best Practices |
| Refactoring & performance | Refactor when smells appear before adding features; optimize only after measurement — architecture/algorithm first, hand-tuning last | Is this change "refactor first" or "optimize blind"? | P2 | Small-step refactors; demand a profile before accepting readability loss |
| Layout & style | Layout mirrors logical structure; one statement per line; team-consistent formatting | Does what the eye sees match what the code does? | P3 | Apply the team formatter; reorder to match logic |
| Concurrency (addendum) | Shared mutable state has explicit ownership and synchronization; concurrency rules appear in interfaces and tests | Is there any "occasional" timing-dependent behavior risk? | P0-P1 | See Concurrency Addendum below |

## Anti-Pattern Catalog

Cross-references point to fuller treatment elsewhere in this skill; rows here give the fast recognition signal.

| Anti-pattern | Recognition signal | Why it hurts | Severity | Fix / see also |
|---|---|---|---|---|
| Giant function | `HandleStuff(a,b,c,d,e,f,g,h)` — unclear abstraction, parameter explosion | High change cost; no unit is independently understandable | P1 | Split responsibilities; parameter object |
| Hidden side effect | `computeTotal()` also writes a file or mutates state | The name lies; callers misjudge the blast radius | P1 on state-writing paths | Separate compute from effect, or put the effect in the name |
| God class / broken abstraction | One class handles UI + DB + business rules | Interface no longer presents one abstraction; maintainability collapses | P1 | Split by abstraction (common-patterns.md: God Class) |
| Duplicate knowledge | Same rule/validation/mapping implemented in 2+ places | Defects copy themselves; changes diverge | P1 for domain invariants | Extract shared logic or table-drive (review-checklist.md: DRY) |
| Magic number | `if status == 3` | Semantics lost; change is high-risk guesswork | P2; P1 on money/auth/state | Enum/named constant (review-checklist.md: PIE) |
| Numeric/ambiguous flag | `if printerError == 1`, `create(true, false)` | Boolean semantics opaque; easy to invert | P2 | Named boolean/enum/options object |
| Global mutable state | `g_config`, `g_status` read/written across modules | Breaks modularity; fragile init order; implicit coordination | P1 | Encapsulate; inject |
| Deep nesting | 3-4 levels of `if/for/while` | Exceeds working memory; branch defects multiply | P2 | Guard clauses, early return, extract function |
| goto / cross-layer exception control | `goto Start`; exceptions thrown through layers as flow control | Non-linear control flow defeats local reasoning | P1-P2 | Structured control; handle locally; translate at boundaries |
| Empty loop / empty statement | `while (read()) ;` | Trivially misread; side effect hidden in the condition | P2-P3 | Explicit loop body, or explicit marker if intentional |
| Implicit case fallthrough | `case A:` falls into `case B` with no marker | The single most maintenance-hostile branch construct | P1 | Explicit `FALLTHROUGH` comment/attribute, or restructure |
| Clever expression | `print(++n, n+2)`; multi-decision one-liners | Poor readability, sometimes not even faster | P2-P3 | Unpack into single steps |
| Comment paying for bad code | "// this is complicated because..." atop tangled logic | The comment is interest on design debt | P3 | Rewrite the code first, then one intent comment |
| Happy-path-only tests | No boundary, dirty-input, or failure-path tests | Defects concentrate exactly where tests aren't | P1 (blocking on requirement-critical logic) | requirement-fidelity.md: Requirement-to-Test Mapping |
| Premature optimization | Hand-tuning with no profile or metric | Wastes effort, damages structure, usually optimizes the wrong spot | P2 | Demand measurement; clear version first (Action Habits) |
| "Might need it later" code | Dormant branches, unused hooks and parameters | Adds cognitive load and test surface for zero present value | P2-P3 | Delete; record the idea in a design doc (Speculative Generality) |
| Unsynchronized shared state | Two threads read/write one object with no lock/atomic | Race conditions: intermittent, environment-dependent, brutal to reproduce | P0-P1 | Concurrency Addendum below |

### Worked Example: Compound Construction Failure

Four anti-patterns stacking in one function — hidden side effect + magic numbers + deep nesting + no error isolation. Reviewing them individually understates the risk; together the function is unreviewable without simulation.

```text
# BAD
function process(order, user, mode):
    if user.role == 1:                  # magic number: which role?
        if order.status == 3:           # magic number: which status?
            if mode == 2:               # magic number: which mode?
                saveAudit()             # hidden side effect in a "process" path
                return calc(order)
                                        # all other paths: implicit no-op, no error

# GOOD
function calculatePaidOrderTotal(order):
    require order.status == OrderStatus.PAID    # guard: explicit precondition
    return calc(order)

function processAdminPreview(order, user):
    require user.isAdmin
    audit.logPreview(order.id)                  # side effect explicit and named
    return calculatePaidOrderTotal(order)
```

Review takeaways: every literal became a named concept; the side effect moved into a function whose name admits it; guards replaced nesting; undefined input states now fail loudly instead of returning nothing.

### Worked Example: Semantic Clarity (Python)

The reviewer's bar is not "does it run" but "is the meaning readable without opening other files":

```python
# BAD: reader must reverse-engineer u, t, s, and the constants
if u.t == 1 and s == 3:
    do_it()

# GOOD: the business rule is the code
if user.is_admin and order_status is OrderStatus.PAID:
    handle_paid_order_for_admin()
```

## Concurrency Addendum

*Code Complete 2* offers no systematic concurrency chapter; these checks fill that gap for modern review. Findings here default to **P0-P1** because race conditions produce intermittent, environment-dependent failures that evade testing and debugging.

Flag when:

- **Shared mutable state without explicit ownership**: two or more threads/tasks can reach the same mutable object and no lock, atomic, or single-owner discipline is documented and enforced.
- **Compound operations assumed atomic**: check-then-act (`if not exists: create`), read-modify-write (`count += 1`), or iterate-while-mutating on shared data without synchronization.
- **Concurrency contract missing from the interface**: a type is used from multiple threads but nothing in its API, docs, or type system states whether it is thread-safe.
- **Locking scattered at call sites** instead of encapsulated with the state it protects — every new caller is a new race opportunity.
- **Tests ignore concurrency**: concurrent code paths verified only single-threaded; no stress/interleaving test for the claimed thread-safety.

Fix direction: shrink the shared-mutable surface first (ownership transfer, immutability, message passing), synchronize what remains, encapsulate the lock with the data, and state the concurrency contract in the interface.

## Relationship to the Architecture Lenses

Run these construction checks **after** requirement fidelity and the layer/SOLID lenses, while walking the diff. A construction finding can escalate an architecture finding (e.g., a magic-number state constant duplicated across layers is simultaneously a PIE violation and a DRY/split-invariant P1) — report it once at the higher severity with both mechanisms named.
