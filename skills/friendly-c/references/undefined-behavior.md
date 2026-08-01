---
urls:
  - https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard
  - https://blog.llvm.org/2011/05/what-every-c-programmer-should-know.html
  - https://en.cppreference.com/w/c/language/behavior
---

# Undefined Behavior

UB is not "works differently on another compiler". It is a licence for the optimizer to assume the situation never happens and delete the code that handles it. The bug appears somewhere else, months later, only in release builds. Treat every item below as a correctness rule, not a portability note.

## Integer arithmetic

- **Signed overflow is UB.** Unsigned wraps (defined). Never rely on signed wraparound, and never "detect" overflow after the fact:

```c
/* Anti-pattern: the check is UB and the optimizer may delete it */
if (a + b < a) return ERR_OVERFLOW;

/* Positive: check before the operation */
if (b > INT32_MAX - a) return ERR_OVERFLOW;

/* Or use the builtin where available */
int32_t sum;
if (__builtin_add_overflow(a, b, &sum)) return ERR_OVERFLOW;
```

- **`INT_MIN / -1` and `INT_MIN % -1` are UB**, as is any division by zero.
- **Shifting by >= the width of the type is UB**, in either direction. So is left-shifting a signed value into or past the sign bit: `1 << 31` on 32-bit `int` is UB -- write `1u << 31`.
- **Integer promotion bites small unsigned types.** `uint16_t a = 40000, b = 40000; a * b` promotes both to `int` and overflows *signed*. Cast up explicitly: `(uint32_t)a * b`.
- **`size_t` subtraction wraps.** `if (len - 1 < x)` with `len == 0` compares against `SIZE_MAX`.
- Conversion from a wider type to a narrower signed type is implementation-defined; range-check first. `-Wconversion` finds these.

## Pointers and memory

- Dereferencing `NULL` is UB -- including the "harmless" `&p->field` on a `NULL` `p`.
- **Pointer arithmetic is valid only inside one object, plus one-past-the-end.** Computing `arr + n + 1` where `n == len` is already UB even if never dereferenced.
- Comparing pointers into different objects with `<`/`>` is UB. `==`/`!=` is fine.
- **`memcpy` with a `NULL` pointer is UB even when `n == 0`.** Guard the empty case.
- `memcpy` with overlapping regions is UB -- use `memmove`.
- **Reading an uninitialized object is UB**, not "reads garbage". The optimizer may treat both branches as unreachable.
- **Use after free and double free are UB.** Setting the pointer to `NULL` after `free` costs one line and converts a class of exploitable bugs into a crash.
- Casting a pointer to a more strictly aligned type and dereferencing it is UB even on x86 where the hardware allows it -- the compiler may emit an aligned SIMD load.

## Type punning and aliasing

**Strict aliasing:** an object may only be accessed through an lvalue of a compatible type (or `char`/`unsigned char`). Violating this is a favorite way to get code silently deleted at `-O2`.

```c
/* Anti-pattern: UB, and it will break under optimization */
float f = 1.0f;
uint32_t bits = *(uint32_t *)&f;

/* Positive: memcpy is the sanctioned punning tool and compiles to nothing */
uint32_t bits;
memcpy(&bits, &f, sizeof bits);
```

In C (unlike C++), reading from a non-active union member is also permitted and reinterprets the bytes -- but `memcpy` reads the same everywhere and never depends on the reader knowing that rule.

For byte-level protocol work, use `unsigned char *` (which may alias anything) and explicit shifts, not a struct overlay:

```c
/* Portable, endian-explicit, no alignment or padding assumptions */
static uint32_t pkt_read_u32_be(const uint8_t *buf)
{
    return ((uint32_t)buf[0] << 24) | ((uint32_t)buf[1] << 16)
         | ((uint32_t)buf[2] <<  8) | ((uint32_t)buf[3]);
}
```

## Sequencing

- **Modifying an object twice without an intervening sequence point is UB**: `i = i++`, `a[i] = i++`, `f(i++, i)`.
- Function argument evaluation order is unspecified. Never write `f(next(it), next(it))`.
- The rule that prevents all of this: **no side effects inside conditions or argument expressions.** One statement, one effect.

## Strings and buffers

- `strcpy`, `strcat`, `sprintf`, `gets` have no bound. Ban them.
- **`strncpy` does not NUL-terminate** when the source fills the buffer. It is a fixed-width-field tool, not a safe `strcpy`.
- **`snprintf` returns the length it *wanted* to write.** Truncation is silent unless you check:

```c
int written = snprintf(buf, sizeof buf, "%s/%s", dir, name);
if (written < 0 || (size_t)written >= sizeof buf)
    return PATH_ERR_TOO_LONG;
```

- Passing a plain `char` to `<ctype.h>` functions is UB for negative values: `isalpha((unsigned char)c)`.
- `%s` with a non-NUL-terminated buffer reads until it finds a zero, somewhere.

## Other traps

- `realloc` returning `NULL` leaves the original block allocated. Never write `p = realloc(p, n)` -- assign to a temporary first.
- **`memcmp` on structs compares padding bytes**, which are indeterminate. Compare fields, or provide a `_equals` function.
- Casting a function pointer to `void *` is not guaranteed by the C standard (POSIX requires it). Note the dependency if you rely on it.
- `%d` with a `size_t`, `%ld` with an `int64_t`: format/argument mismatch is UB. Use `%zu` and the `<inttypes.h>` macros (`PRId64`).
- Flexible array members (`uint8_t data[];` as the last struct member) are the standard idiom; `data[1]` hacks and zero-length arrays are not.

## How to actually catch these

Review does not find UB reliably; tools do. See [build-tooling.md](build-tooling.md).

```sh
cc -std=c11 -Wall -Wextra -Werror -Wconversion -Wshadow \
   -fsanitize=address,undefined -fno-omit-frame-pointer -g -O1 ...
```

UBSan catches signed overflow, bad shifts, misaligned access, and null dereference at the moment they happen. ASan catches out-of-bounds, use-after-free, and leaks. Run the test suite under both, in CI, on every commit. Any UB rule in this file that a sanitizer can check should be checked by the sanitizer, not by a human reading a diff.
