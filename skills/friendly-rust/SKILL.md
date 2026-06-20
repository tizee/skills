---
name: friendly-rust
description: Practical guidance for writing, refactoring, and reviewing friendly Rust code that is correct, idiomatic, and maintainable. Use whenever working with Rust (.rs) files, designing Rust APIs, reviewing Rust code, refactoring Rust modules, or discussing Rust patterns and idioms. Also use when the user mentions ownership, borrowing, lifetimes, unsafe, async Rust, error handling in Rust, or Rust performance. Even if the user doesn't say "Rust" explicitly, trigger this skill when the context involves .rs files or Cargo.toml.
---

# friendly-rust

Concise guidance for writing Rust code that is correct, idiomatic, and pleasant to maintain.

## Purpose and Triggers

- Use when writing new Rust code, refactoring, reviewing, or designing public APIs and CLIs.
- Rust source files (`.rs`) or Cargo projects.
- Prefer correctness and clarity; optimize only after measuring.

## Decision Order

1. Correctness and safety -- work with the borrow checker, not around it
2. Readability and maintainability -- clear intent over clever tricks
3. Extensibility and evolution cost -- stable public surfaces, private internals
4. Performance and optimization -- measure first, optimize second

## Workflow

> **MANDATORY FIRST STEP:** When reviewing Rust code, read [references/review-checklist.md](references/review-checklist.md) in full before producing any review. Then read the topic-specific reference file(s) relevant to the change (see Topics table below). Do not review from memory — the reference files are the source of truth.

1. Read [references/review-checklist.md](references/review-checklist.md) (mandatory for any review).
2. Locate the relevant topic below and read its linked reference file.
3. Apply the guidance and compare against anti-pattern / positive-pattern examples.
4. Confirm the change against every applicable checklist item before reporting.

## Topics

| Topic | Guidance | Reference |
| --- | --- | --- |
| Principles | Correctness first, work with the type system, encode invariants in types | [references/principles.md](references/principles.md) |
| Error Design | Meaningful error types, Result over panics, design error boundaries | [references/error-design.md](references/error-design.md) |
| Ownership & Borrowing | Caller controls cloning, Cow for flexibility, avoid hidden allocations | [references/ownership-borrowing.md](references/ownership-borrowing.md) |
| Unsafe Discipline | Contain unsafe in modules, SAFETY comments, minimize scope | [references/unsafe-discipline.md](references/unsafe-discipline.md) |
| Async & Concurrency | Send/Sync contracts, spawn_blocking, cancellation, waker correctness | [references/async-concurrency.md](references/async-concurrency.md) |
| API Design | Trait conventions, builders, visibility, rustdoc, standard trait impls | [references/api-design.md](references/api-design.md) |
| Performance & Profiling | Measure-first profiling, Criterion benchmarks, PGO workflow | [references/performance-profiling.md](references/performance-profiling.md) |
| Type Patterns | Newtypes, phantom types, typestate, const generics, sealed traits | [references/type-patterns.md](references/type-patterns.md) |
| Testing | Unit tests, property-based testing, mocking, fuzzing, Miri, coverage | [references/testing.md](references/testing.md) |
| Macros | Declarative vs proc macros, when to use, hygiene, debugging | [references/macros.md](references/macros.md) |
| Build & Dependencies | Compile time, cargo features, workspace layout, security audits | [references/build-dependencies.md](references/build-dependencies.md) |
| Review | Quick-reference checklist covering all topics | [references/review-checklist.md](references/review-checklist.md) |

## References

- Each topic file lists source URLs in its frontmatter `urls`.
