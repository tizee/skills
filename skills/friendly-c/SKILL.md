---
name: friendly-c
description: Practical guidance for writing, refactoring, and reviewing friendly C code that is correct, legible, and safe to change. Use whenever working with C (.c/.h) files, designing C module APIs, reviewing or refactoring C code, or debugging crashes and undefined behavior. Also use when the user mentions pointers, ownership, malloc/free, error codes, headers, macros, sanitizers, MISRA/CERT, Power of 10, or C build warnings. Even if the user does not say "C" explicitly, trigger this skill when the context involves .c/.h files, Makefile/CMakeLists.txt for C targets, or C11/C17/C23 standards. Do not use for C++ or Objective-C.
---

# friendly-c

Concise guidance for writing C that a stranger -- human or model -- can read one screen at a time and change without fear. C gives no safety net: every invariant the compiler will not check must be visible in the code's shape, its names, and its assertions. The goal of this skill is to make every region of a C file locally understandable and every symbol greppable to few sites.

## Purpose and Triggers

- Use when writing new C, refactoring, reviewing, designing module APIs and headers, or hunting undefined behavior.
- C source and headers (`.c`, `.h`), C build files, C tests.
- Prefer correctness and legibility; optimize only after measuring.

## Decision Order

1. **Correctness and defined behavior** -- no UB, every fallible call checked, every buffer bounded
2. **Legibility and locality** -- small flat functions, one concept per name, vocabulary before logic
3. **Change cost** -- single-sourced logic, one producer per error value, edits stay local
4. **Performance** -- profile first; the optimizer is smarter than a clever rewrite

The ordering matters because C's failure mode is not a slow program, it is a program that corrupts memory in one place and crashes in another. Everything below buys locality: the ability to reason about a region without loading the rest of the program.

## Workflow

> **MANDATORY FIRST STEP:** When reviewing C code, read [references/review-checklist.md](references/review-checklist.md) in full before producing any review. Then read the topic-specific reference file(s) relevant to the change (see Topics table below). Do not review from memory -- the reference files are the source of truth.

1. Read [references/review-checklist.md](references/review-checklist.md) (mandatory for any review).
2. Locate the relevant topic below and read its linked reference file.
3. Before editing bodies, map the module: ownership, public API, constants, types, status values, and which functions are orchestrators, leaves, or adapters ([references/functions-control-flow.md](references/functions-control-flow.md)).
4. Apply the guidance and compare against the anti-pattern / positive-pattern examples.
5. Confirm the change against every applicable checklist item before reporting.

For new modules, follow the skeleton in [references/file-layout.md](references/file-layout.md). For edits to existing code, run the near-miss test in [references/worked-example.md](references/worked-example.md): code that looks fine at a glance usually hides duplicated mutation, data encoded as control flow, or interleaved concepts.

For any non-trivial change, build clean under `-Wall -Wextra -Werror -Wconversion -Wshadow` and run the test suite under ASan+UBSan -- see [references/build-tooling.md](references/build-tooling.md). In C, warnings and sanitizers are not style preferences; they are the only automated correctness check the language offers.

## Topics

| Topic | Guidance | Reference |
| --- | --- | --- |
| Principles | Locality first, vocabulary before logic, make invariants visible | [references/principles.md](references/principles.md) |
| File Layout | Fixed `.c`/`.h` section order, headers as the module contract, include hygiene | [references/file-layout.md](references/file-layout.md) |
| Naming & Constants | Module prefixes, verb_object, lifetime pairs, named constants with units | [references/naming-constants.md](references/naming-constants.md) |
| Functions & Control Flow | 15-line target, depth cap 2, orchestrator/leaf/adapter, guard clauses, bounded loops, no recursion | [references/functions-control-flow.md](references/functions-control-flow.md) |
| Error Handling | One status enum per module, check every call, propagate unchanged, `MODULE_TRY` | [references/error-handling.md](references/error-handling.md) |
| Types & Data | Fixed-width types, `const` correctness, tagged unions, designated initializers, dispatch tables | [references/types-data.md](references/types-data.md) |
| Memory & Resources | Ownership stated at the interface, acquire/release locality, no `goto`-only-return, lifetime discipline | [references/memory-resources.md](references/memory-resources.md) |
| Boundaries & Assertions | Validate at public entry, assert internally, two-asserts-per-function floor | [references/boundary-assertions.md](references/boundary-assertions.md) |
| Macros & Preprocessor | `static inline` first, hygienic macro rules, the one macro allowed to `return` | [references/macros-preprocessor.md](references/macros-preprocessor.md) |
| Undefined Behavior | Signed overflow, aliasing, alignment, integer promotion, string and buffer traps | [references/undefined-behavior.md](references/undefined-behavior.md) |
| Testing | Unit tests as the feedback loop, sanitizers, fuzzing, seams without frameworks | [references/testing.md](references/testing.md) |
| Build & Tooling | Warning flags as errors, hardening, clang-tidy/cppcheck, CMake/Make layout, C standard choice | [references/build-tooling.md](references/build-tooling.md) |
| Worked Example | "Good but not good enough": the near-miss refactor, staged to full conformance | [references/worked-example.md](references/worked-example.md) |
| Review | Quick-reference checklist covering all topics | [references/review-checklist.md](references/review-checklist.md) |

## Resolve Constraints

- Higher-priority user instructions, repo `AGENTS.md`/`CLAUDE.md`, ABI and wire-format freezes, generated code, and platform requirements win over this skill.
- Do not widen a scoped task into a repo-wide rewrite because nearby untouched C predates these rules.
- When a constraint forces a deviation, put a comment at the deviation site stating the constraint precisely. A note in the chat does not replace the source-site comment.
- Do not claim compliance for checks that could not run; name the command that did not run.

## References

- Each topic file lists source URLs in its frontmatter `urls`.
- Primary lineage: Kernighan & Pike *The Practice of Programming*, Hanson *C Interfaces and Implementations*, Holzmann's *Power of 10* (NASA/JPL), CERT C and MISRA C in spirit, and the C11/C17 standard itself.
