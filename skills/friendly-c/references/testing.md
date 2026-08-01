---
urls:
  - https://clang.llvm.org/docs/AddressSanitizer.html
  - https://llvm.org/docs/LibFuzzer.html
  - https://github.com/silentbicycle/greatest
---

# Testing

The test suite is the feedback loop. Any change beyond what the tests can verify has to route through a human reading it carefully -- so the reach of the tests sets the pace of the project.

## What makes C testable

The structural rules in this skill are also testability rules:

| Rule | Testing payoff |
| --- | --- |
| Leaves are pure, straight-line logic | Testable with no setup |
| Adapters isolate foreign calls | The only place needing a fake |
| No `static` locals | Tests are order-independent |
| `_init` over `_create` | Fixtures live on the test's stack, no leaks |
| Named status enum | Assertions name the expected failure, not `-1` |

If a function is hard to test, the usual cause is a mixed altitude: logic fused with I/O. Split it before writing a mock.

## A test looks like this

Any small framework works (greatest, Unity, cmocka, µnit) -- or none at all. What matters is one behavior per test and a name that states the expectation.

```c
/* test_rb.c: covers ring buffer capacity and wraparound behavior. */

#include "greatest.h"
#include "rb.h"

TEST rb_push_rejects_when_full(void)
{
    uint8_t   storage[RB_TEST_CAPACITY];
    rb_t      rb;
    ASSERT_EQ(RB_OK, rb_init(&rb, storage, sizeof storage));

    for (size_t i = 0; i < RB_TEST_CAPACITY; i++)
        ASSERT_EQ(RB_OK, rb_push(&rb, (uint8_t)i));

    ASSERT_EQ(RB_ERR_FULL, rb_push(&rb, 0));   /* names the exact failure */
    ASSERT_EQ(RB_TEST_CAPACITY, rb_count(&rb));

    rb_deinit(&rb);
    PASS();
}
```

Note what the test asserts: the named status *and* that the failed push did not change the count. A test that only checks "it failed" misses the half-mutation bug, which is the bug that actually happens.

## What to test

- **Every named error value.** If `RB_ERR_FULL` has one producing line, there should be one test that produces it. An error path with no test is an error path that has never run.
- **Boundaries**: 0, 1, capacity-1, capacity, capacity+1. `SIZE_MAX` where a size is caller-supplied.
- **Post-failure state**: after a failed call, is the object still usable? The contract says something; the test proves it.
- **Round trips**: `encode` then `decode`, `create` then `destroy` under a leak checker.
- Not: `static` helpers directly. Test them through the public boundary; if a leaf is complex enough to need direct testing, it probably belongs in its own module with a public API.

## Seams without a framework

The adapter altitude *is* the seam. To test a module that talks to hardware or the network, give the adapter a function-pointer table and swap it in tests:

```c
/* Injected in tests; the production table is BUS_REAL_OPS. */
typedef struct {
    bus_status_t (*read_u16)(bus_t *bus, uint16_t reg, uint16_t *out_val);
} bus_ops_t;
```

Keep the indirection at exactly one layer, in a `static const` table ([types-data.md](types-data.md)). A codebase where every call is virtual for testability is untraceable.

## Sanitizers are part of the test run

A passing test suite proves nothing about memory safety unless it ran instrumented:

```sh
# Debug/test build
cc -std=c11 -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer ...

# Threads get their own run (TSan is incompatible with ASan)
cc -std=c11 -g -O1 -fsanitize=thread ...
```

LeakSanitizer runs by default with ASan on Linux (`ASAN_OPTIONS=detect_leaks=1`). It is not available on macOS/arm64 -- use `leaks -atExit -- ./tests` or Instruments there. Treat any sanitizer report as a build failure, not a warning.

## Fuzzing

Every parser that consumes external bytes gets a fuzz target. This is the single highest-yield test type in C:

```c
/* fuzz_parse.c -- built with -fsanitize=fuzzer,address,undefined */
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    pkt_t pkt = {0};
    (void)pkt_parse(&pkt, data, size);   /* any status is fine; a crash is not */
    pkt_deinit(&pkt);
    return 0;
}
```

Run it in CI for a bounded time, and check the corpus in. When a crash is found, the reproducer becomes a permanent unit test.

## Coverage as a map, not a score

`--coverage` / `gcovr` is useful for one question: which error paths have never executed. Chasing a percentage target produces tests that assert nothing. An uncovered `return MOD_ERR_FULL` is a real finding; an uncovered `default:` trap arm is not.

## Test hygiene

- Tests are C code and follow every rule in this skill: named constants, checked calls, no magic numbers.
- One assertion concept per test; a test named `rb_push_rejects_when_full` must fail for exactly one reason.
- No test depends on another's side effects, and no test depends on wall-clock time or unseeded randomness.
- A bug fix lands with the test that would have caught it, in the same commit.
