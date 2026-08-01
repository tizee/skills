---
urls:
  - https://en.cppreference.com/w/c/types/integer
  - https://wiki.sei.cmu.edu/confluence/display/c/DCL+Declarations+and+Initialization
---

# Types and Data

Types are the cheapest documentation C offers: they are checked, they appear at every use site, and they cost nothing at runtime.

## Integer types

- **Fixed-width everywhere**: `uint32_t`, `int64_t`, `uint8_t`. Bare `int` only where an external API forces it.
- **`size_t` for sizes, counts, and indices.** `ptrdiff_t` for pointer differences.
- **Never mix signed and unsigned in a comparison.** `-Wsign-compare` catches the obvious cases; the subtle ones are `size_t` subtraction wrapping to a huge value.
- **Use `bool` from `<stdbool.h>`** for two-state values, never `int` with `0`/`1`.
- `char` for text, `uint8_t` for bytes. `char`'s signedness is implementation-defined; passing a plain `char` to `<ctype.h>` functions is UB for negative values -- cast to `unsigned char` first.

```c
/* Anti-pattern: silent wrap when count is 0 */
for (size_t i = 0; i < list->count - 1; i++) { ... }   /* 0 - 1 == SIZE_MAX */

/* Positive: guard the empty case, or restructure */
for (size_t i = 1; i < list->count; i++) { ... }
```

## `const` correctness

- **`const` on every pointer parameter the function does not write through.** This is not decoration: it is the only signal a caller has about whether their buffer survives the call unchanged.
- `const` on a by-value parameter adds nothing to the caller and is noise in the prototype.
- `static const` for lookup tables; `enum` for integer constants (a `const int` is not a compile-time constant in C and cannot size an array).

## Structs

- **Group fields by relatedness**, and document every invariant that ties two fields together in a comment above the struct.
- **Every variable initialized at declaration.** `= {0}` for structs, explicit values otherwise.
- **Designated initializers** so a field reorder cannot silently change meaning:

```c
sensor_cfg_t cfg = {
    .interval_ms = SENSOR_POLL_INTERVAL_MS,
    .retry_count = SENSOR_RETRY_COUNT,
    .bus         = bus                     /* borrowed, outlives cfg */
};
```

- **Opaque structs only at true library boundaries.** Internal modules expose layout so instances can live on the stack, embed in parent structs, and be inlined across. An opaque type forces heap allocation and a `_create`/`_destroy` pair on every user.
- Avoid bitfields for anything that crosses a process, file, or wire boundary -- their layout is implementation-defined. Use explicit shifts and masks with named constants.

## Unions

**Every union carries a tag field**, and the tag and union live in the same struct:

```c
typedef enum { VAL_INT, VAL_STR } val_kind_t;

/* Invariant: kind selects which member of u is live. */
typedef struct {
    val_kind_t kind;
    union {
        int64_t     i;
        const char *s;   /* borrowed, owned by the arena */
    } u;
} val_t;
```

An untagged union is a type error the compiler agreed not to report.

## Scope and dereference depth

- **Declare every object at the smallest scope that works, at the latest point that works** -- specifically at its first valid value. A variable declared 20 lines before it means anything is 20 lines of "is it set yet?" for the reader.
- **One level of dereference per expression.** A chain like `a->b->c->d` smuggles three lifetimes and three nullability questions into one term. Bind intermediates to named locals:

```c
/* Anti-pattern */
if (ctx->session->conn->state == CONN_READY) { ... }

/* Positive */
const conn_t *conn = ctx->session->conn;   /* one place to check nullability */
if (conn->state == CONN_READY) { ... }
```

## Function pointers and dispatch tables

**Function pointers appear only as entries in `static const` dispatch tables.** Control flow through data is legible when the table is immutable, named, and complete; a function pointer passed around loose is control flow no reader can trace.

```c
/* Anti-pattern: dispatch smeared across a chain */
if (strcmp(name, "get") == 0)       return do_get(req);
else if (strcmp(name, "put") == 0)  return do_put(req);
else if (strcmp(name, "del") == 0)  return do_del(req);
return HTTP_ERR_METHOD;

/* Positive: the mapping is data, and adding a verb costs one line */
typedef http_status_t (*http_handler_fn)(http_req_t *req);

typedef struct {
    const char      *name;
    http_handler_fn  fn;
} http_route_t;

static const http_route_t HTTP_ROUTES[] = {
    { "get", http_do_get },
    { "put", http_do_put },
    { "del", http_do_del }
};

static http_status_t http_dispatch(http_req_t *req, const char *name)
{
    for (size_t i = 0; i < ARRAY_LEN(HTTP_ROUTES); i++) {
        if (strcmp(name, HTTP_ROUTES[i].name) == 0)
            return HTTP_ROUTES[i].fn(req);
    }
    return HTTP_ERR_METHOD;
}
```

The table is the documentation. `grep HTTP_ROUTES` answers "what verbs exist" in one hit.

## `typedef` discipline

- Typedef structs and enums -- the `struct` keyword at every use adds nothing.
- **Never typedef a pointer.** `typedef node_t *node_ptr_t;` hides the single most important fact about a variable, and makes `const node_ptr_t` mean the surprising thing (const pointer, not pointer to const).
- Typedef function pointer types; the raw syntax is unreadable at a declaration site.

## Data over branches

When a chain of `if`s maps one value to another, it is a table, not logic:

```c
/* Invariant: indexed by cell_kind_t, one entry per kind. */
static const uint16_t MAP_CELL_SCORES[MAP_CELL_KIND_COUNT] = {
    [MAP_CELL_EMPTY]  = 0,
    [MAP_CELL_WALL]   = 0,
    [MAP_CELL_PELLET] = MAP_SCORE_PELLET,
    [MAP_CELL_POWER]  = MAP_SCORE_POWER
};
```

Adding a cell kind costs one line and cannot be forgotten in a second place. Add a `_KIND_COUNT` sentinel to the enum and a `static_assert` on the array length so a missed entry is a build failure.
