---
name: friendly-cpp
description: Guardrail guidance for writing, refactoring, and reviewing friendly modern C++ (C++17/20/23) that is memory-safe, maintainable, and free of common anti-patterns. Built for auditing C++ projects written by unconstrained coding agents -- ownership and lifetime (RAII, unique_ptr/shared_ptr/weak_ptr, string_view/span borrows), error handling, class and API design, UB, headers and CMake, sanitizers and static analysis. Invoke explicitly for C++ (.cpp/.cc/.hpp/.h in a C++ project) work.
disable-model-invocation: true
user-invocable: true
---

# friendly-cpp

Guardrails for writing C++ that a stranger -- human or model -- can review one screen at a time and change without leaking, dangling, or invoking undefined behavior. C++ gives you deterministic lifetimes and zero-cost abstractions, and also every way to misuse them. The goal of this skill is to make **ownership, lifetime, and failure visible in types and signatures**, so that a reviewer can answer the four core questions for any line of code:

1. **Who owns it?**
2. **When is it released?**
3. **Who borrows it, and what guarantees the owner outlives the borrow?**
4. **Under concurrency, who synchronizes it?**

Most leaks, double-frees, use-after-frees, and reference cycles reduce to a missing answer to one of these.

## Purpose and Triggers

- Explicitly invoked by the user. Scope is C++ projects only (`.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh`, `.h` inside a C++ target, `CMakeLists.txt` for C++ targets). For pure C use `friendly-c` instead.
- Two primary modes:
  - **Review** an existing codebase, often one written by a coding agent without constraints. Find ownership bugs, UB, and anti-patterns; rank them by severity.
  - **Write / refactor** C++ that passes the same review.
- Baseline: C++17. Use C++20/23 facilities (`std::span`, concepts, `std::jthread`, `std::expected`, `std::out_ptr`) when the project's standard allows -- check `CMAKE_CXX_STANDARD` or equivalent first; never silently raise the standard.

## Decision Order

1. **Correctness and memory safety** -- no UB, no leak, no dangling borrow, every failure handled
2. **Legibility of ownership and intent** -- types say who owns; signatures say what is borrowed; names say what things are
3. **Change cost** -- Rule of Zero, value semantics, small interfaces, single-sourced logic
4. **Performance** -- measure first; `shared_ptr` everywhere is not "safe", and template tricks are not "fast" until a profile says so

The ordering matters because C++'s failure mode is not a slow program: it is a program that corrupts memory in one place and crashes in another, often only under load or in release builds.

## Workflow

> **MANDATORY FIRST STEP:** Before producing any review, read [references/review-checklist.md](references/review-checklist.md) and [references/agent-anti-patterns.md](references/agent-anti-patterns.md) in full. Then read the topic reference(s) relevant to the code in front of you (Topics table below). Do not review from memory -- the reference files are the source of truth.

### Review mode

1. Read the two mandatory files above.
2. Establish the project baseline: C++ standard, compiler(s), build system, exception policy (exceptions on/off), existing error type, existing lint/sanitizer config. Project conventions override this skill where they are deliberate and consistent.
3. Map ownership before judging bodies: which types own resources, where heap objects are created, where `shared_ptr` graphs form, which classes store non-owning pointers/views, which callbacks cross threads.
4. Run the high-signal grep list in [references/review-checklist.md](references/review-checklist.md) to find lifetime boundaries quickly; read every hit in context.
5. Report findings using the severity scale and output format in the checklist, each with a `file:line` anchor, the failure mechanism, and a concrete fix.
6. If the build and tests can run, run them under ASan+UBSan and clang-tidy ([references/tooling-testing.md](references/tooling-testing.md)). If they cannot, say which command did not run.

### Write / refactor mode

1. Read the topic references for what you are touching.
2. Design the ownership graph first: values by default, `unique_ptr` for dynamic single ownership, `shared_ptr` only with named independent owners, borrows for everything else.
3. Wrap every resource in RAII at the point of acquisition; prefer Rule of Zero.
4. Build clean with the warning set in [references/headers-build.md](references/headers-build.md) and test under sanitizers.
5. Confirm against every applicable checklist item before reporting.

## Topics

| Topic | Guidance | Reference |
| --- | --- | --- |
| Principles | Four ownership questions, value semantics first, make invariants visible in types | [references/principles.md](references/principles.md) |
| Ownership & Borrowing | Ownership vocabulary for parameters/returns/fields, smart pointers only when lifetime is involved | [references/ownership-lifetime.md](references/ownership-lifetime.md) |
| RAII & Resources | Rule of Zero/Five, custom deleters, handle classes, `noexcept` moves, `out_ptr`, `jthread` | [references/raii-resources.md](references/raii-resources.md) |
| Shared Ownership | When `shared_ptr` is justified, double control blocks, `enable_shared_from_this`, cycles, `weak_ptr::lock`, intrusive refcount | [references/shared-ownership.md](references/shared-ownership.md) |
| Lifetime Traps | Dangling views, temporaries, container invalidation, lambda captures, non-owning fields | [references/lifetime-traps.md](references/lifetime-traps.md) |
| Concurrency | Ownership vs pointee vs publication, `atomic<shared_ptr>`, destructor thread, locks and threads as RAII | [references/concurrency.md](references/concurrency.md) |
| Error Handling | One error strategy per layer, exceptions vs `expected`, exception-safety guarantees, no swallowing | [references/error-handling.md](references/error-handling.md) |
| Classes & API Design | Invariants, `explicit`, const-correctness, composition over inheritance, virtual destructor rules, `enum class`, `optional`/`variant` | [references/classes-api-design.md](references/classes-api-design.md) |
| Types, Casts & UB | Initialization, narrowing, casts, integer pitfalls, `auto`, `constexpr`, common UB | [references/types-ub.md](references/types-ub.md) |
| Generic Code & STL | Algorithms over raw loops, concepts over SFINAE, templates only when they pay | [references/generic-stl.md](references/generic-stl.md) |
| Headers & Build | Header hygiene, ODR, include discipline, target-based CMake, warning flags | [references/headers-build.md](references/headers-build.md) |
| Tooling & Testing | ASan/UBSan/TSan/MSan, Valgrind, clang-tidy, Static Analyzer, Lifetime Safety, CI tiers, leak vs retention | [references/tooling-testing.md](references/tooling-testing.md) |
| Agent Anti-Patterns | Catalog of what unconstrained agents typically write, why it is wrong, and the fix | [references/agent-anti-patterns.md](references/agent-anti-patterns.md) |
| Review | Severity scale, blocking gates, grep list, output format, legacy migration order | [references/review-checklist.md](references/review-checklist.md) |

## Resolve Constraints

- Higher-priority user instructions, repo `AGENTS.md`/`CLAUDE.md`, ABI freezes, generated code, and platform requirements (e.g. `-fno-exceptions`, embedded, no RTTI) win over this skill.
- Do not widen a scoped task into a repo-wide rewrite because nearby untouched code predates these rules. In review mode, report; do not silently refactor.
- When a constraint forces a deviation, put a comment at the deviation site stating the constraint precisely.
- Do not claim compliance for checks that could not run; name the command that did not run.

## References

- Each topic file lists source URLs in its frontmatter `urls`.
- Primary lineage: the C++ working draft ([basic.life], [smartptr]), C++ Core Guidelines, Google C++ Style Guide, Chromium and LLVM coding standards, Boost/Folly/RocksDB production practice, and Clang sanitizer/static-analysis documentation.
