---
urls:
  - https://www.kernel.org/doc/html/latest/process/coding-style.html
  - https://arxiv.org/abs/2510.03178
  - https://arxiv.org/abs/2508.06414
---

# Naming and Constants

C has no namespaces and no module system. Names *are* the module system, and grep is the navigation tool. Both facts drive every rule here.

## Naming

- **Module prefix on every symbol with external linkage**: `rb_push`, `net_send`. Static helpers carry the prefix too, so a grep for `rb_` finds the whole module.
- **Functions are `verb_object`**: `parse_header`, `flush_queue`, `sensor_read_raw`.
- **Predicates start with `is_`/`has_` and are never negated**: `is_valid`, never `is_not_ready`. A negated predicate produces `!is_not_ready`, which costs a reader a mental double negation at every use.
- **Lifetime pairs are exact and mean something**:
  - `_create` / `_destroy` -- heap allocation, ownership transferred to the caller.
  - `_init` / `_deinit` -- caller-owned storage, no allocation of the object itself.
  - `_open` / `_close` -- an external handle.
  Do not mix the vocabularies. `foo_create` that takes a caller-provided buffer is a lie about ownership.
- **Sanctioned abbreviations**: `buf`, `len`, `ctx`, `cfg`, `idx`. Nothing else. `tmp`, `data2`, `do_stuff`, `mgr`, `hdlr` are banned.
- **Name length scales with scope distance.** `i` is fine in a five-line loop. Anything live across 20 lines gets a descriptive name.
- **Precise beats verbose.** The name is the shortest string that states the concept: `retry_count`, not `number_of_connection_retry_attempts`.
- **Types**: `snake_case` with a `_t` suffix for typedefs (`sensor_status_t`). Note POSIX reserves `_t` in principle; most projects use it anyway -- be consistent with the codebase you are in.
- **Enum constants**: `MODULE_UPPER_SNAKE` (`SENSOR_ERR_BUS`).
- Struct tag and typedef may share a name: `typedef struct sensor sensor_t;`.

Why this strictness: naming is a semantic channel, not decoration. Obfuscation studies show model comprehension drops when identifiers are stripped even on tasks that should depend only on structure, and human studies attribute up to a 30 percent comprehension effect to good names.

## Constants

- **No naked literals.** The only bare numbers in logic are `0` and `1` where the meaning is self-evident. Everything else gets a name at the top of the file or in the header.
- **Use `enum` for related integer constants** so debuggers and readers see names, not values. Use `#define` only for string literals, conditional compilation, and values needed by the preprocessor.
- **Units go in the name**: `TIMEOUT_MS`, `MAX_PAYLOAD_BYTES`, `RETRY_COUNT`, `SCALE_MILLIDEG`.
- **Derived values are computed, never restated**: `POOL_BYTES = POOL_SLOTS * SLOT_BYTES`.
- **One definition site per constant in the whole program.** A constant defined in two headers is a divergence waiting to happen.
- A string literal used twice becomes a `#define`.

## Anti-Pattern

```c
#define BUFSZ 1024                  /* 1024 what? bytes? entries? */

int chk(struct m *p, char *d)       /* chk? d? */
{
    if (!p || !d) return -1;
    char tmp[1024];                 /* literal restated, now two sources */
    if (strlen(d) > 1023)           /* 1023 is BUFSZ-1 restated a third time */
        return -2;
    ...
}
```

Three copies of one fact, two unnameable identifiers, and error values that mean nothing at the call site.

## Positive Pattern

```c
enum {
    MSG_BUF_BYTES     = 1024,
    MSG_MAX_TEXT_LEN  = MSG_BUF_BYTES - 1   /* derived, never restated */
};

/* Copies text into msg. Fails with MSG_ERR_TOO_LONG when text does not
 * fit in MSG_MAX_TEXT_LEN bytes. text must be NUL-terminated. */
msg_status_t msg_set_text(msg_t *msg, const char *text)
{
    if (msg == NULL || text == NULL)
        return MSG_ERR_ARG;

    size_t text_len = strlen(text);
    if (text_len > MSG_MAX_TEXT_LEN)
        return MSG_ERR_TOO_LONG;

    memcpy(msg->text, text, text_len + 1);
    return MSG_OK;
}
```

Change the buffer size in one place and every dependent fact follows.

## Grep discipline

Before adding a name, ask what a `grep` for it should return:

| Name kind | Expected grep result |
| --- | --- |
| Constant | 1 definition, N uses |
| Status value | 1 producing line, its handlers |
| Public function | 1 prototype, 1 definition, call sites |
| Struct field write | ideally 1 accessor, not scattered `->` assignments |

If a grep for a name returns a confusing scatter, the name or the design is wrong -- not the tool.
