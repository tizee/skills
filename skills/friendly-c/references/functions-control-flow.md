---
urls:
  - https://spinroot.com/gerard/pdf/P10.pdf
  - https://www.sonarsource.com/docs/CognitiveComplexity.pdf
---

# Functions and Control Flow

A function should fit entirely in attention while reasoning about any line of it. Nesting is state the reader must carry; guard clauses discharge it immediately.

## Function shape

- **One job.** If the contract comment needs the word "and", split the function.
- **Target 15 lines, hard cap 40.** A function is a table of contents for its helpers, not a container for logic phases.
- **Maximum nesting depth 2.** Guard clauses first, happy path at the left margin.
- **Maximum 4 parameters.** More means the parameters are a struct trying to exist.
- **Fixed parameter order**: module context pointer first, output parameters next, pure inputs last. A function with no context starts with its outputs, mirroring `memcpy`. A buffer and its length are always adjacent, buffer first.
- **No `static` locals** except `static const` lookup tables. All state is passed in or owned by a context struct. A `static` local is a global with better camouflage, and it makes the function non-reentrant.
- **Cognitive complexity budget**: target 8, hard cap 15 (Sonar rules -- each break in linear flow costs, nesting costs progressively). Code that respects the depth cap sits far under budget; the metric is a tripwire, not a goal.

## The three altitudes

Every function is exactly one of these, never a mix:

| Altitude | Contains | Never contains |
| --- | --- | --- |
| **Orchestrator** | A sequence of helper calls, status checks, branches on named predicates, result binding | Arithmetic, parsing, bit twiddling, direct field mutation |
| **Leaf** | Straight-line logic, calling only the module's own accessors and pure utilities | Calls into other modules |
| **Adapter** | Exactly one call into a foreign module, translating its status and calling convention | A second foreign call, or any business logic |

Public visibility is *not* a fourth altitude -- a public function is still one of the three.

Why: the reader follows a plan or follows arithmetic, never both at once.

## When to stop decomposing

**The name test:** if the most honest name for a candidate helper merely paraphrases its body, inline it and stop. A helper earns existence by naming a concept, owning an error value, or isolating a side effect.

This is the brake on ravioli code, where a hundred two-line functions turn every read into a pointer chase.

## Control flow rules

- **Early return over `else` chains.** The success path is the unindented path.
- **No `goto`.** A function that acquires multiple resources decomposes into helpers, each releasing what it acquired on its own failure, locally, next to the acquisition.
  - A `goto` whose label only returns is banned with no exception -- that is the cleanup pattern with the cleanup deleted.
  - **Narrow exception:** a function juggling three or more interdependent resources, where decomposition would smear half-initialized state across helpers, may use one forward `goto` to one cleanup label. The label site carries a comment justifying it. See [memory-resources.md](memory-resources.md).
- **Every `switch` case ends in `break` or an explicit `/* fallthrough */`.** `default` is always present, even when the enum is exhaustive -- it is the trap for the value that should not exist.
- **A loop body over 10 lines becomes a named function.** The call site then documents the iteration in one line.
- **Every loop has a statically evident upper bound.** The one exception is an intentionally nonterminating loop (event pump, scheduler), marked with a comment saying exactly that.
- **No recursion, direct or indirect.** Recursive shapes convert to a loop over an explicit bounded worklist, which makes stack use visible and termination checkable. (Exception in practice: a proven-bounded tree walk over a structure with a hard depth limit -- state the bound in a comment.)
- **No side effects inside conditions.** No assignment inside `if`. Ternaries only for simple value selection, never nested.

## Anti-Pattern

```c
/* Parses and validates and stores the record. */   /* three "and"s */
int rec_load(store_t *st, const char *line)
{
    if (line != NULL) {
        char *sep = strchr(line, ':');
        if (sep != NULL) {
            int id = atoi(line);                     /* no error path */
            if (id > 0) {
                for (size_t i = 0; i < st->count; i++) {
                    if (st->recs[i].id == id) {
                        st->recs[i].hits++;          /* depth 5 */
                        return 0;
                    }
                }
                ...
            }
        }
    }
    return -1;
}
```

Depth 5, three concepts interleaved, one `return -1` standing for four distinct failures, and `atoi` swallowing parse errors.

## Positive Pattern

```c
/* Loads one record line into the store. Fails with REC_ERR_FORMAT on a
 * malformed line and REC_ERR_FULL when the store has no room. */
rec_status_t rec_load(store_t *st, const char *line)
{
    if (st == NULL || line == NULL)
        return REC_ERR_ARG;

    rec_fields_t fields = {0};
    REC_TRY(rec_parse_line(&fields, line));

    rec_t *existing = rec_find_by_id(st, fields.id);
    if (existing != NULL) {
        rec_bump_hits(existing);
        return REC_OK;
    }
    return rec_append(st, &fields);
}
```

Six lines of plan. `rec_parse_line` owns the format error, `rec_find_by_id` owns the search, `rec_append` owns the capacity error. Each question about this function has exactly one place to look.

## Bounded loop conversion

```c
/* Anti-pattern: unbounded, recursive */
static void walk(node_t *n) { if (n) { visit(n); walk(n->left); walk(n->right); } }

/* Positive: explicit bounded worklist, stack use visible */
enum { TREE_MAX_PENDING = 64 };

/* Visits every node. Fails with TREE_ERR_DEPTH when the tree exceeds
 * TREE_MAX_PENDING pending nodes. */
tree_status_t tree_walk(node_t *root)
{
    node_t *pending[TREE_MAX_PENDING];
    size_t  pending_count = 0;

    pending[pending_count++] = root;
    while (pending_count > 0) {
        node_t *n = pending[--pending_count];
        if (n == NULL)
            continue;
        tree_visit(n);
        if (pending_count + 2 > TREE_MAX_PENDING)
            return TREE_ERR_DEPTH;
        pending[pending_count++] = n->left;
        pending[pending_count++] = n->right;
    }
    return TREE_OK;
}
```

The recursive version's failure mode is a stack overflow with no diagnostic. The iterative version's failure mode is a named status at a checkable line.
