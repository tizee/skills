---
urls:
  - https://spinroot.com/gerard/pdf/P10.pdf
  - https://en.cppreference.com/w/c/error/assert
---

# Boundaries and Assertions

One validation site per boundary, assertions everywhere else. Validation duplicated at every level is noise that hides the logic; assertions are machine-checked comments that cost nothing in release.

## The boundary rule

- **Public entry points validate their arguments** and return `MODULE_ERR_ARG` on violation. This is the only place a `NULL` check belongs.
- **Internal `static` helpers do not re-validate.** They `assert` their invariants. The assert documents the contract in debug builds and vanishes in release.
- Data from outside the process -- files, sockets, `argv`, environment, IPC -- is validated at the boundary and *never* asserted. An assert on untrusted input is a denial-of-service switch, since `NDEBUG` builds skip it entirely and debug builds abort on attacker-chosen input.

| Input source | Mechanism |
| --- | --- |
| Caller inside the module | `assert` |
| Caller outside the module (public API) | Validate, return `ERR_ARG` |
| Outside the process (file, network, user) | Validate, return a specific status, never assert |

## Assertion density

- **Every leaf that mutates state asserts at least one invariant.**
- Module-wide target: the Power of 10 floor of two assertions per function.
- Assert facts that are *not* locally obvious: relationships between fields, index bounds derived elsewhere, non-`NULL` derived from a boundary check three frames up.
- **Never put a side effect inside `assert`.** `NDEBUG` deletes the whole expression:

```c
assert(rb_push(rb, item) == RB_OK);   /* the push disappears in release */
```

- Use `static_assert` (C11 `<assert.h>`) for anything checkable at compile time: struct sizes for wire formats, table lengths against enum counts, type width assumptions.

```c
static_assert(sizeof(packet_hdr_t) == PACKET_HDR_BYTES,
              "packet header must match the wire format");
static_assert(ARRAY_LEN(MAP_CELL_SCORES) == MAP_CELL_KIND_COUNT,
              "score table must cover every cell kind");
```

A `static_assert` turns a class of runtime corruption into a build failure. Prefer it whenever the fact is static.

## Anti-Pattern

```c
/* NULL-checked at every level; the real logic is hard to find */
static int mod_step(mod_t *m, item_t *it)
{
    if (m == NULL) return -1;            /* already checked by the caller */
    if (it == NULL) return -1;           /* and by its caller */
    if (m->items == NULL) return -1;     /* and it can never be NULL here */
    m->items[m->count++] = *it;          /* the one real line, unasserted */
    return 0;
}
```

Four lines of ceremony, one line of work, and the *actual* invariant -- `count < capacity` -- is the one thing nobody checks. This function can overflow the array while dutifully rejecting `NULL`.

## Positive Pattern

```c
/* Public boundary: the only validation site. */
mod_status_t mod_add(mod_t *m, const item_t *item)
{
    if (m == NULL || item == NULL)
        return MOD_ERR_ARG;
    if (m->count >= m->capacity)
        return MOD_ERR_FULL;

    mod_append(m, item);
    return MOD_OK;
}

/* Appends item. The caller has proved there is room. */
static void mod_append(mod_t *m, const item_t *item)
{
    assert(m->items != NULL);
    assert(m->count < m->capacity);     /* the invariant that actually matters */

    m->items[m->count] = *item;
    m->count++;
}
```

The boundary owns the two failure modes and names them. The leaf states, in machine-checked form, exactly what it is trusting -- so the next editor who calls `mod_append` from a new site gets an abort in the test run instead of heap corruption in production.

## Assertions versus statuses: the decision

```
Can this condition be triggered by data outside my control?
├── yes  -> validate, return a named status
└── no   -> can it be checked at compile time?
           ├── yes -> static_assert
           └── no  -> assert
```

If the answer is "it can never happen", it is an `assert`. If it is "it should not happen but a caller might", it is a status. Never a silent `return`.

## Public API preconditions

State preconditions in the contract comment even when they are also asserted -- the comment is what a caller reads, the assert is what catches them:

```c
/* Writes len bytes from buf into the ring. buf must be non-NULL and hold at
 * least len bytes. Fails with RB_ERR_FULL when the ring lacks room; nothing
 * is written in that case. */
rb_status_t rb_write(rb_t *rb, const uint8_t *buf, size_t len);
```

Every pointer parameter gets a nullability statement. Every failure mode gets a named status. Every partial-write behavior is stated, because "nothing is written" versus "some bytes were written" is the difference between a retry loop that works and one that corrupts the stream.
