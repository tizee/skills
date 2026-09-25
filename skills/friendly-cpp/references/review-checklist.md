---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines
  - https://google.github.io/styleguide/cppguide.html
  - https://clang.llvm.org/docs/AddressSanitizer.html
---

# Review Checklist

Quick-reference questions for reviewing C++. Pick the sections relevant to the code; work top-down, because a memory-safety defect outranks every structural finding below it. Read [agent-anti-patterns.md](agent-anti-patterns.md) alongside this file.

## Severity Scale

| Level | Meaning | Examples |
| --- | --- | --- |
| **P0** | Memory corruption, UB, or crash reachable in normal operation. Blocks merge. | UAF, double free, dangling view, data race, missing virtual dtor with base deletion, iterator invalidation |
| **P1** | Leak, lifetime hazard, or silently wrong behavior under realistic conditions. Blocks merge. | raw owning pointer, shared_ptr cycle, swallowed exception, un-joined thread, ODR violation, uninitialized member |
| **P2** | Maintainability or correctness risk that will cause bugs on the next change. Fix in this PR or file a ticket. | over-shared ownership, mixed error strategy, missing `override`, singleton dependencies, C-style casts, no sanitizer CI |
| **P3** | Idiom / clarity / style. Fix opportunistically. | getters/setters on data, `using namespace` in `.cpp`, `std::endl`, unneeded templates |

## Output Format

For each finding:

```text
[P0] src/net/session.cpp:142 -- timer callback captures `this`; Session can be destroyed before the timer fires (UAF).
     Mechanism: Session owned by unique_ptr in Server::sessions_, erased on disconnect; Timer outlives it.
     Fix: capture weak_from_this() and lock(), or cancel the timer in ~Session (Timer::cancel is synchronous).
     Ref: lifetime-traps.md#lambda-captures
```

Group by severity, P0 first. End with: commands run (build, tests, sanitizers, clang-tidy) and their results, and commands that could not run and why. Do not report "no issues" for categories you did not check.

## Blocking Gates (P0/P1)

- [ ] **Owner identifiable.** Every heap object, handle, and lock has an owner visible in its type. No owning raw `T*`.
- [ ] **No business-layer `new`/`delete`/`malloc`/`free`.** Scoped values, `make_unique`, `make_shared`, containers, or dedicated RAII wrappers.
- [ ] **No independent control blocks.** No two `shared_ptr` from one raw pointer; no `shared_ptr(this)`.
- [ ] **No strong cycles.** Parent/child, subject/observer, callback/self, cache/entry graphs checked; back edges weak.
- [ ] **Borrow lifetime provable.** Every stored `T*`, `T&`, `span`, `string_view`, iterator, and lambda reference capture names an owner that outlives it.
- [ ] **No views of temporaries.** No `string_view`/`span`/reference built from a temporary, by-value return, or local that escapes.
- [ ] **Container invalidation analyzed.** Nothing holds element pointers/iterators across mutation without a stated contract.
- [ ] **Async/thread borrows re-proven.** No `[&]`/`[this]` in stored, posted, or threaded callbacks without proof.
- [ ] **Shared ownership is not thread safety.** Pointee access synchronized; same `shared_ptr` variable written concurrently only under a lock or `atomic<shared_ptr>`.
- [ ] **Threads joined.** No joinable `std::thread` destroyed; no unjustified `detach()`.
- [ ] **Destructors, deleters, moves, `swap` do not throw.**
- [ ] **Resource wrappers correct.** Rule of Five complete; moved-from state safely destructible; moves `noexcept`.
- [ ] **Polymorphic deletion safe.** Virtual destructor on bases deleted through base pointers.
- [ ] **No UB from the catalog** in [types-ub.md](types-ub.md): uninitialized reads, signed overflow on external input, C-style/reinterpret casts that pun, OOB indexing of unchecked input.
- [ ] **No swallowed failures.** No `catch (...)` without rethrow/terminate; no ignored `[[nodiscard]]` results; no silent default fallback.
- [ ] **No ODR violations.** No non-inline definitions in headers.

## Ownership and RAII

- Does every smart-pointer parameter actually transfer or share lifetime? Otherwise `T&`/`const T&`/`T*`.
- For each `shared_ptr`: who are the independent owners? Could it be `unique_ptr` or a value?
- Is `.release()` rare, local, and immediately handed to another owner? (C++23: `out_ptr`/`inout_ptr` for C APIs.)
- Any hand-written destructor in a non-wrapper class? Can member types make it Rule of Zero?
- Does every `weak_ptr` use go through one `lock()` held for the whole use? Any `expired()`-then-`lock()`?
- Is the destruction thread of shared objects acceptable (heavy / thread-affine destructors)?
- Any `use_count()` in logic?
- Intrusive refcounts: ordering, delete policy, and cycle strategy documented? Prefer a mature utility.

## Lifetime

- Any returned or stored view/reference into a local, temporary, or container that mutates?
- Any range-for over a member of a temporary (pre-C++23)?
- Any `const T& r = f(temporary)` where `f` returns a reference?
- Any use after `std::move`?
- Any `string_view::data()` passed to a C string API?
- Any `this` registered externally in a constructor or unregistered in a destructor while other threads run?

## Concurrency

- Does every mutex document the data it guards? RAII locks only? No reference escaping a lock?
- Any check-then-act on an atomic? Any non-seq_cst ordering without a comment? Any `volatile` or plain flag for signaling?
- Any condition-variable `wait` without a predicate?
- Was it run under TSan?

## Errors

- One mechanism per layer matching project policy (exceptions on/off, existing result type)?
- Throw by value, catch by `const&`, `throw;` to rethrow?
- Exceptions contained at C API, thread, and callback boundaries?
- Each mutating operation meets at least the basic guarantee?

## Classes and APIs

- Invariant per class; otherwise plain struct without accessors?
- All members initialized; single-arg constructors `explicit`?
- `override` on every override; no slicing copies of polymorphic types; hierarchy <= 2 levels?
- Interface with one implementation and no test seam? Manager/Factory/Helper classes that add only indirection?
- Singletons or mutable globals used as dependencies?
- Sentinel values, bool flag parameters, plain enums, `int ms` where `optional`/`enum class`/strong types/`chrono` fit?

## Types and Library

- Any C-style cast, narrowing without check, signed/unsigned comparison, `size() - 1` on possibly-empty containers?
- Any `auto` hiding a copy, a proxy, or signedness that matters?
- Any hand-written container/algorithm/string utility the standard library provides? Any duplicate of an existing project utility?
- Any template with one instantiation, unconstrained templates, or SFINAE/CRTP without a reason?
- Any macro that could be `constexpr`/`inline`/`using`?

## Headers and Build

- Headers self-contained, guarded, no `using namespace`, no non-inline definitions?
- File-local helpers in an unnamed namespace; project code namespaced?
- Target-based CMake, explicit sources, `CMAKE_CXX_STANDARD_REQUIRED ON`, warnings per target, `-Werror` in CI?
- Any `NOLINT`, warning pragma, or `-Wno-*` without a justification comment?

## Tests and Tooling

- ASan+UBSan on unit and integration tests? TSan for concurrent code? Fuzz targets for parsers of external input?
- `.clang-tidy` with ownership/bugprone checks, clean on changed files?
- Does every error value / exception type have a test that produces it? Boundaries covered?
- For services: is retention observable (heap growth, live-object counts), not just leaks?

## High-Signal Grep List

These have legitimate uses, but each marks an ownership or lifetime boundary worth reading in context:

```bash
rg -n --type cpp -e '\bnew\b' -e '\bdelete\b' -e '\bmalloc\(' -e '\bfree\(' -e '\brealloc\('
rg -n --type cpp -e '\.release\(\)' -e '\.get\(\)' -e 'use_count\(' -e '\.data\(\)'
rg -n --type cpp -e 'shared_ptr<[^>]+>\(' -e 'shared_from_this' -e 'weak_ptr' -e 'expired\('
rg -n --type cpp -e 'string_view' -e 'span<' -e '\[this\]' -e '\[&\]' -e '\[=\]'
rg -n --type cpp -e '\.detach\(\)' -e 'std::thread' -e 'volatile' -e '\.lock\(\)' -e '\.unlock\(\)'
rg -n --type cpp -e 'catch *\(\.\.\.\)' -e 'reinterpret_cast' -e 'const_cast' -e '\(\s*(int|long|unsigned|char|float|double|size_t)\s*\*?\s*\)'
rg -n --type cpp -e 'using namespace' -e '#define ' -e 'NOLINT' -e '#pragma (GCC|clang) diagnostic'
rg -n --type cpp -e '\w+\s*\*\s*&' -e '\w+\s*\*\*'
```

## Migrating a Legacy or Agent-Written Codebase

Order by risk reduction, not by file count:

1. **Raw owners and exception-path leaks.** Replace owning raw pointers with `unique_ptr`/values; wrap C/OS resources in RAII.
2. **Shared ownership graph.** Draw it; fix double control blocks, cycles, self-capturing callbacks; demote unjustified `shared_ptr`.
3. **Long-lived observers.** Member raw pointers, views, iterators, callback captures, async tasks -- document or eliminate each.
4. **Tooling in CI.** Warnings as errors, ASan/UBSan, clang-tidy, Static Analyzer; TSan for concurrent modules.
5. **Only then optimize.** Intrusive refcounts, hazard pointers, custom allocators -- driven by profiles.

This order lowers real UAF/double-free risk first while keeping the ownership architecture getting simpler, not more elaborate.

## Final Gate

- Does the change stay within the requested scope?
- Is every deviation from these rules commented at the deviation site, naming the constraint?
- Were any checks skipped? Name the command that did not run rather than claiming compliance.
