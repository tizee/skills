---
urls:
  - https://gcc.gnu.org/onlinedocs/cpp/Macro-Pitfalls.html
  - https://wiki.sei.cmu.edu/confluence/display/c/PRE+Preprocessor
---

# Macros and the Preprocessor

The preprocessor is a text substitution engine that runs before the type checker sees anything. Every macro is code the debugger cannot step into and the compiler cannot type-check. Use it only where the language cannot reach.

## Prefer functions

**`static inline` beats a function-like macro in every case where types allow.** It type-checks, it debugs, it evaluates arguments once, and modern compilers inline it just as aggressively.

```c
/* Anti-pattern: double evaluation, no type checking */
#define MAX(a, b) ((a) > (b) ? (a) : (b))
size_t n = MAX(read_len(fp), MIN_CHUNK);   /* read_len called twice */

/* Positive */
static inline size_t size_max(size_t a, size_t b)
{
    return a > b ? a : b;
}
```

Reach for a macro only when you need one of: a compile-time constant expression, a string literal, `#`/`##` token manipulation, conditional compilation, or `__FILE__`/`__LINE__` capture.

## Macro hygiene rules

When a macro is genuinely required:

- **UPPERCASE names**, module-prefixed like any other symbol.
- **Parenthesize every argument and the whole body.** `#define AREA(w, h) ((w) * (h))`.
- **Multi-statement bodies wrap in `do { } while (0)`** so the macro behaves like a statement at a call site with a trailing semicolon and inside an unbraced `if`.
- **No macro evaluates an argument twice.** If it must, bind to a local inside a `do/while` block with a name that cannot collide (trailing underscore).
- **No macro contains `return`, `goto`, `break`, or `continue`** -- with exactly one sanctioned exception, below.
- No macro defines control flow keywords or shadows language syntax (`#define BEGIN {` and friends).
- Never `#undef` and redefine a macro to mean something else in the same translation unit.

## The one exception: `MODULE_TRY`

Each module may define exactly one `MODULE_TRY(expr)` beside its status enum -- the sole macro permitted to contain `return`:

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

The rationale and the "acquires nothing" restriction live in [error-handling.md](error-handling.md). The short version: hidden control flow is banned wherever it could skip an obligation; orchestrators hold no obligations by construction, so there the hidden return is safe and buys a greppable rule -- a fallible call outside a `TRY` or an `if` is visibly unchecked.

## Standard useful macros

```c
/* Element count of an array. Never pass a pointer: this silently lies. */
#define ARRAY_LEN(arr) (sizeof (arr) / sizeof (arr)[0])
```

`ARRAY_LEN` on a decayed pointer compiles and silently produces garbage. `-Wsizeof-pointer-div` (on by default in recent GCC/Clang) warns about it; with `-Werror` that is usually enough. To make it a hard error everywhere, use the negative-bitfield trick:

```c
#if defined(__GNUC__)   /* GCC/Clang: reject a pointer at compile time */
#define ARRAY_IS_ARRAY_(arr) \
    (!__builtin_types_compatible_p(__typeof__(arr), __typeof__(&(arr)[0])))
#define ARRAY_LEN(arr)                          \
    (sizeof (arr) / sizeof (arr)[0]             \
     + 0 * sizeof(struct { int : -!ARRAY_IS_ARRAY_(arr); }))
#else
#define ARRAY_LEN(arr) (sizeof (arr) / sizeof (arr)[0])
#endif
```

The `sizeof` of an anonymous bitfield with negative width is a constraint violation, so a pointer argument fails the build instead of returning a plausible wrong number. If the project cannot afford the extension, keep the simple version and note the constraint in a comment at the definition.

## Conditional compilation

- Keep `#ifdef` out of function bodies. Platform variation belongs at file granularity or behind a single-line wrapper function, not smeared through logic.

```c
/* Anti-pattern: two programs interleaved, neither one readable */
void log_line(const char *msg)
{
#ifdef _WIN32
    HANDLE h = GetStdHandle(STD_ERROR_HANDLE);
    DWORD written = 0;
    WriteFile(h, msg, (DWORD)strlen(msg), &written, NULL);
#else
    ssize_t n = write(STDERR_FILENO, msg, strlen(msg));
    (void)n;
#endif
}

/* Positive: one function per platform, chosen at build time */
/* log_posix.c and log_win32.c each define log_line; the build picks one. */
```

- Prefer `#if defined(FEATURE_X)` over `#ifdef` when the condition may grow.
- Every `#endif` over ten lines away from its `#if` carries a comment naming the condition: `#endif /* FEATURE_X */`.
- Feature flags are named constants when possible: `if (CFG_ENABLE_TRACE) { ... }` compiles both branches and lets dead-code elimination do the work, keeping both paths type-checked.

## Compiler extensions

C11 minimum. No compiler extensions without a wrapping macro and a comment naming the compiler:

```c
/* GCC/Clang: warn when a status return value is dropped. */
#if defined(__GNUC__)
#define RB_MUST_CHECK __attribute__((warn_unused_result))
#else
#define RB_MUST_CHECK
#endif

RB_MUST_CHECK rb_status_t rb_push(rb_t *rb, uint8_t byte);
```

This particular one earns its keep: it turns "every fallible call is checked" from a review rule into a compiler error.
