---
urls:
  - https://wiki.sei.cmu.edu/confluence/display/c/MEM+Memory+Management
  - https://man7.org/linux/man-pages/man3/malloc.3.html
---

# Memory and Resources

C's hardest question is not "what does this do" but "who frees this, and when". Answer it at the interface, in the name, and in a comment -- never leave it to the reader to reconstruct.

## Ownership is stated, not inferred

Every pointer that crosses a function boundary is one of three things, and the contract comment says which:

| Kind | Meaning | Convention |
| --- | --- | --- |
| **Owned** | The receiver must release it | Returned by `_create`; comment says "caller owns" |
| **Borrowed** | The receiver must not release it, and must not outlive it | Comment says "borrowed, must outlive X" |
| **Output** | Caller-owned storage the callee writes into | Named `out_*`, appears right after the context parameter |

```c
/* Creates a ring buffer with capacity slots. Caller owns the result and
 * must release it with rb_destroy. Fails with RB_ERR_ALLOC. */
rb_status_t rb_create(rb_t **out_rb, size_t capacity);

/* Initializes caller-owned storage. Pairs with rb_deinit. buf is borrowed
 * and must outlive rb. */
rb_status_t rb_init(rb_t *rb, uint8_t *buf, size_t buf_len);
```

The `_create`/`_destroy` versus `_init`/`_deinit` distinction is not stylistic: it tells the caller whether a `free` is coming.

## Prefer caller-owned storage

Reach for `_init` over `_create` whenever the object can live on the caller's stack or inside a parent struct. It removes an allocation, an error path, and a leak opportunity. Heap allocation is for objects whose size or lifetime is genuinely dynamic.

## Allocation rules

- Check every allocation. `malloc` returning `NULL` is a status, not an abort -- unless the project's policy is fail-fast, in which case say so once, in one place.
- **Compute sizes with the object, not the type**: `p = malloc(count * sizeof *p)` never `sizeof(struct thing)`. A type change at the declaration then cannot desynchronize.
- **Check for multiplication overflow before allocating**: `if (count > SIZE_MAX / sizeof *p) return ERR_RANGE;`. This is a real exploit class, not a theoretical one.
- Set a pointer to `NULL` immediately after freeing it if it remains in scope or in a struct that outlives the free. A stale pointer in a live struct is a use-after-free waiting for a schedule change.
- **`free(NULL)` is defined and does nothing** -- never guard it with an `if`.
- No VLAs and no `alloca`: their failure mode is a stack overflow with no diagnostic. Use a fixed bound with a named constant, or the heap.

## Release next to acquisition

The rule that replaces `goto cleanup`: **decompose so each helper releases what it acquired, on its own failure, locally.**

```c
/* Anti-pattern: three acquisitions, one exit ladder, easy to get wrong */
int session_open(session_t *s, const char *path)
{
    int rc = -1;
    s->fp = fopen(path, "r");
    if (!s->fp) goto out;
    s->buf = malloc(BUF_BYTES);
    if (!s->buf) goto close_fp;
    if (lock_take(&s->lock) != 0) goto free_buf;
    return 0;
free_buf:
    free(s->buf);
close_fp:
    fclose(s->fp);
out:
    return rc;
}
```

```c
/* Positive: each acquisition owns its own failure path */
session_status_t session_open(session_t *s, const char *path)
{
    if (s == NULL || path == NULL)
        return SESSION_ERR_ARG;

    session_status_t status = session_open_file(s, path);
    if (status != SESSION_OK)
        return status;

    status = session_alloc_buf(s);
    if (status != SESSION_OK) {
        session_close_file(s);
        return status;
    }

    status = session_take_lock(s);
    if (status != SESSION_OK) {
        session_free_buf(s);
        session_close_file(s);
        return status;
    }
    return SESSION_OK;
}
```

The second version is longer and that is fine: every release sits next to the failure it answers, and adding a fourth resource does not require re-reading a label ladder. Note also that **no `MODULE_TRY` appears here** -- this function acquires.

**Narrow `goto` exception:** three or more *interdependent* resources, where decomposition would smear half-initialized state across helpers, may use one forward `goto` to one cleanup label. The label carries a comment justifying it. A `goto` whose label only returns is never justified.

## Symmetry check

For every `_create` there is exactly one `_destroy`, and `_destroy` accepts `NULL` and does nothing:

```c
/* Releases rb. Accepts NULL. */
void rb_destroy(rb_t *rb)
{
    if (rb == NULL)
        return;
    free(rb->slots);
    free(rb);
}
```

A `_destroy` that rejects `NULL` forces a guard at every call site -- a hundred copies of one decision.

## Partial-failure discipline

A function that fails must leave its output in a state the caller can reason about. State which in the contract:

- **Strong guarantee (preferred)**: on failure, nothing observable changed. Build the new object completely, then swap it in as the last step.
- **Weak guarantee**: on failure, the object is valid but unspecified. Say so explicitly.
- **No guarantee**: unacceptable in new code.

```c
/* Replaces the config with the contents of path. On failure the existing
 * config is unchanged. */
cfg_status_t cfg_reload(cfg_t *c, const char *path)
{
    cfg_t staged = {0};                    /* build fully, then commit */
    CFG_TRY(cfg_load_into(&staged, path));

    cfg_deinit(c);
    *c = staged;
    return CFG_OK;
}
```

## Lifetime traps

- Never return a pointer to a local. `-Wreturn-local-addr` catches the direct case; storing it into an out-parameter is not caught.
- A pointer into a `realloc`-able array is invalidated by any growth. Store indices, not pointers, into dynamic arrays.
- String literals are not writable. Point at them with `const char *`, always.
- A borrowed pointer stored in a struct is a lifetime coupling: document which object must outlive which, in the struct comment.
