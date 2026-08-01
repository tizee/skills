---
urls:
  - https://wiki.sei.cmu.edu/confluence/display/c/ERR00-C.+Adopt+and+implement+a+consistent+and+comprehensive+error+handling+policy
  - https://spinroot.com/gerard/pdf/P10.pdf
---

# Error Handling

C has no exceptions, so error handling is a discipline, not a feature. The discipline: one status vocabulary per module, checked at every call, propagated unchanged, decided at the top.

## Rules

- **Every fallible function returns a module status enum.** Success is `0` and is named: `RB_OK`.
- **One status enum per module**, values prefixed: `RB_ERR_ALLOC`, `RB_ERR_FULL`.
- **Never return `bool` from anything that can fail more than one way.** `false` is not a diagnosis.
- **Never mix errno-style and enum-style inside module code.** Wrap libc at the boundary and convert (see the adapter pattern below).
- **Every fallible call is checked.** No exceptions, including `snprintf`, `fclose`, and `write`.
- **Status propagates upward unchanged.** Only the top of the call chain logs, converts, or decides. A function that both returns a status and logs it produces duplicate diagnostics.
- **Minimize producers per error value.** `grep RB_ERR_FULL` should land on one producing line and its handlers. If three functions produce the same value, a debugger cannot tell you which one fired.
- **Results come back through output parameters**, never through a sentinel in the return value. A function that returns `-1` for error and a valid index otherwise forces every caller to know the sentinel.
- **Never use a valid-looking value to signal failure.** `map_eat` returning `0` for "NULL map", "out of bounds", and "empty cell" alike is three bugs waiting to happen.

## The status enum

```c
typedef enum {
    RB_OK          =  0,
    RB_ERR_ARG     = -1,   /* NULL pointer or invalid parameter */
    RB_ERR_ALLOC   = -2,   /* allocation failed */
    RB_ERR_FULL    = -3,   /* no room for the push */
    RB_ERR_EMPTY   = -4    /* nothing to pop */
} rb_status_t;
```

Negative error values with `0` success means `if (status != RB_OK)` reads the same everywhere and `status < 0` still works for callers that need a quick test.

## Propagation with `MODULE_TRY`

```c
/* Propagates any non-OK status to the caller. Permitted only in
 * functions that acquire nothing. Sole macro allowed to return. */
#define RB_TRY(expr)                        \
    do {                                    \
        rb_status_t rb_try_s_ = (expr);     \
        if (rb_try_s_ != RB_OK)             \
            return rb_try_s_;               \
    } while (0)
```

`TRY` is C's answer to Rust's `?`. It is the **only** macro permitted to contain `return`, and it carries a hard usage restriction:

> **`TRY` may appear only in functions that acquire nothing.** Any function whose body calls `_create`, `_init`, `_open`, `alloc`, or any acquiring function uses explicit checks with explicit release instead.

The restriction is greppable, which is the point. Orchestrators hold no cleanup obligations by construction, so a hidden return inside one cannot leak anything. The payoff: a fallible call sitting outside a `TRY` or an `if` becomes visibly an unchecked call -- the single most common C bug.

The cost is priced in: `grep return` misses these exits, and a debugger steps into the macro. Both are cheaper than the forgotten check.

## Wrapping foreign conventions

Never let errno-style leak inward. One adapter per foreign call:

```c
/* Adapter over fread. Fails with FILE_ERR_IO on a short read. */
static file_status_t file_read_exact(FILE *fp, void *out_buf, size_t len)
{
    size_t got = fread(out_buf, 1, len, fp);
    if (got != len)
        return ferror(fp) ? FILE_ERR_IO : FILE_ERR_EOF;
    return FILE_OK;
}
```

Now the module's own code never touches `ferror`, and there is exactly one line to change if the I/O layer changes.

## Anti-Pattern

```c
int cfg_load(cfg_t *c, const char *path)
{
    FILE *fp = fopen(path, "r");
    if (!fp) {
        fprintf(stderr, "open failed: %s\n", strerror(errno)); /* logs mid-stack */
        return -1;                                             /* what is -1? */
    }
    char line[256];
    while (fgets(line, sizeof line, fp)) {
        cfg_parse_line(c, line);      /* return value dropped */
    }
    fclose(fp);                       /* return value dropped */
    return 0;
}
```

Three defects: an unnamed error value, logging from the middle of the stack (the caller will log again), and two dropped return values -- a parse failure silently produces a half-loaded config.

## Positive Pattern

```c
/* Loads config from path. Fails with CFG_ERR_OPEN when the file cannot be
 * opened and CFG_ERR_FORMAT on a malformed line. Leaves *c unmodified on
 * failure. */
cfg_status_t cfg_load(cfg_t *c, const char *path)
{
    if (c == NULL || path == NULL)
        return CFG_ERR_ARG;

    FILE *fp = fopen(path, "r");     /* acquires: no TRY below this line */
    if (fp == NULL)
        return CFG_ERR_OPEN;

    cfg_status_t status = cfg_read_lines(c, fp);
    fclose(fp);
    return status;
}
```

The acquiring function stays explicit, `cfg_read_lines` (which acquires nothing) may use `CFG_TRY` freely, and the caller at the top of the stack decides whether to log, retry, or exit.

## Where to log

| Layer | Behavior |
| --- | --- |
| Leaf / adapter | Return a status. Never log. |
| Orchestrator | Propagate. Never log. |
| Top of call chain (`main`, request handler, task loop) | Map status to a message, exit code, or retry. Log exactly once. |

A helper that returns a `cfg_status_t` for the caller to handle should also provide `cfg_status_str(status)` so the top layer can print a name, not a number.
