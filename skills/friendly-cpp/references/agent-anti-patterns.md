---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines
  - https://google.github.io/styleguide/cppguide.html
---

# Agent Anti-Patterns

What unconstrained coding agents repeatedly produce in C++, why it is wrong, and what to write instead. These patterns compile, often pass happy-path tests, and look plausible -- which is exactly why a reviewer must hunt for them deliberately.

Each entry: **pattern -> why it hurts -> fix -> where to read more**. Severity uses the scale in [review-checklist.md](review-checklist.md).

## Ownership and Memory

| # | Pattern | Why it hurts | Fix | Sev |
| --- | --- | --- | --- | --- |
| A1 | `shared_ptr` everywhere "for safety" | hides the owner, widens lifetimes, cycles, atomic cost, non-deterministic destruction thread | values, then `unique_ptr`; `shared_ptr` only with named independent owners ([shared-ownership.md](shared-ownership.md)) | P2 (P1 if it forms a cycle) |
| A2 | Raw `new`/`delete` in business code, owning `T*` members | leaks on early return/exception; double delete on copy | `make_unique`, value members, Rule of Zero ([raii-resources.md](raii-resources.md)) | P1 |
| A3 | Class with raw owning pointer + hand-written destructor, no copy/move handling | defaulted copy = double free (Rule of Three/Five violated) | replace members with RAII types, delete the destructor | P0 |
| A4 | `const std::shared_ptr<T>&` or `shared_ptr<T>` params on functions that only read | false lifetime claim, forces heap allocation on callers | `const T&` / `T*` ([ownership-lifetime.md](ownership-lifetime.md)) | P3 |
| A5 | `std::shared_ptr<T>(this)` or two `shared_ptr` from one raw pointer | two control blocks -> double delete | `enable_shared_from_this`; create once, copy | P0 |
| A6 | Callback stored in the object captures `shared_from_this()` | self-cycle, object never freed | `weak_from_this()` + `lock()` | P1 |
| A7 | `[this]` / `[&]` captured into threads, timers, executors, signal handlers | use-after-free when the object/scope dies first | capture by value, move in ownership, weak promotion ([lifetime-traps.md](lifetime-traps.md)) | P0 |
| A8 | Returning `string_view`/`span`/`const T&` to a local or a by-value temporary | dangling immediately | return by value | P0 |
| A9 | `.get()` from a smart pointer stored in another object | borrow with no lifetime proof | pass `T&` for the call; if stored, document owner or share ownership | P1 |
| A10 | `malloc`/`free`/`realloc`, `char buf[N]` + `strcpy`/`sprintf` | C in C++: no constructors, overflows | `std::vector`, `std::string`, `std::format` | P1 |
| A11 | `std::thread` without join on every path; `detach()` | `std::terminate`; thread outlives referenced data | `std::jthread` or joining RAII wrapper ([concurrency.md](concurrency.md)) | P1 |

## Errors and Control Flow

| # | Pattern | Why it hurts | Fix | Sev |
| --- | --- | --- | --- | --- |
| B1 | `catch (...) { log; }` and continue | hides failures, continues with invalid state | catch only where handled; propagate otherwise ([error-handling.md](error-handling.md)) | P1 |
| B2 | Mixed `bool`/`-1`/`nullptr`/exceptions in one module | callers cannot handle errors uniformly; failures ignored | one mechanism per layer, `[[nodiscard]]` | P2 |
| B3 | `init()` / `setup()` after constructor; `is_initialized_` flags | zombie objects; every method must check | construct fully or factory returning `expected` | P2 |
| B4 | Fallback defaults on failure (`catch -> return {}`, `value_or(0)` on config) | silently wrong behavior | fail loudly unless the default is genuinely correct and commented | P1 |
| B5 | `throw std::string(...)` / catch by value | slicing, uncatchable by `std::exception` handlers | throw `std::exception`-derived by value, catch by `const&` | P2 |
| B6 | `noexcept` sprinkled on allocating functions | exception becomes `std::terminate` | `noexcept` only where no-throw is guaranteed | P2 |

## Class and API Design

| # | Pattern | Why it hurts | Fix | Sev |
| --- | --- | --- | --- | --- |
| C1 | Getter/setter for every field | no invariant protected, pure noise | plain `struct`, or real operations on a class ([classes-api-design.md](classes-api-design.md)) | P3 |
| C2 | `IFoo` interface + `FooImpl` with one implementation, `FooManager`, `FooFactory`, `FooHelper` | speculative abstraction, indirection without payoff | concrete class; add the interface when the second implementation or test double appears | P3 |
| C3 | Polymorphic base without virtual destructor | UB + leak when deleted through base | `virtual ~Base() = default;` | P0 if deleted via base, else P2 |
| C4 | Missing `override`; `virtual` repeated on overrides | silent non-override on signature drift | `override` everywhere | P2 |
| C5 | Singletons / mutable globals for dependencies | hidden coupling, untestable, init/teardown order bugs | constructor injection | P2 |
| C6 | God class (thousands of lines, dozens of members) | untestable, every change touches it | split by responsibility | P2 |
| C7 | `bool` flag parameters, stringly-typed enums, magic numbers | unreadable call sites, typos compile | `enum class`, named constants, strong types | P3 |
| C8 | Uninitialized members; non-`explicit` single-arg ctors | UB reads; surprising implicit conversions | default member initializers; `explicit` | P1 / P3 |

## Language and Library Usage

| # | Pattern | Why it hurts | Fix | Sev |
| --- | --- | --- | --- | --- |
| D1 | C-style casts `(int)x` | silently becomes `reinterpret_cast`/`const_cast` | `static_cast`, `std::bit_cast` ([types-ub.md](types-ub.md)) | P2 |
| D2 | `for (int i = 0; i < v.size(); i++)` | signed/unsigned mismatch, truncation on big sizes | range-for, `std::size_t`, algorithms | P3 |
| D3 | Erase inside range-for / hold reference across `push_back` | iterator invalidation -> UAF | `std::erase_if`; index or stable container | P0 |
| D4 | Hand-written containers, string utilities, sort, thread pools | bugs the standard library already fixed | standard library or the project's existing utilities ([generic-stl.md](generic-stl.md)) | P2 |
| D5 | Template/SFINAE/CRTP for code with one type | unreadable errors, compile time, no benefit | concrete code; concepts when generic | P3 |
| D6 | `#define` constants and function-like macros | no scope, no types, double evaluation | `constexpr`, `inline` functions, `enum class` | P3 |
| D7 | `std::endl` in loops, pass-by-value of large objects, `std::move` on `const` or on return locals | hidden flush / copies / pessimized RVO | `'\n'`, `const&`, plain `return local;` | P3 |
| D8 | `volatile` or plain `bool` for thread signaling | data race = UB | `std::atomic<bool>`, `std::stop_token` | P0 |
| D9 | `auto` for everything, including numeric results and proxies | hidden copies, wrong signedness, dangling proxies | explicit types where they matter | P3 |

## Headers and Build

| # | Pattern | Why it hurts | Fix | Sev |
| --- | --- | --- | --- | --- |
| E1 | `using namespace std;` in headers (or anywhere) | pollutes every includer, ambiguous overloads | qualify names ([headers-build.md](headers-build.md)) | P2 in headers, P3 in `.cpp` |
| E2 | Non-`inline` definitions in headers | ODR violations, link errors | `inline`, or move to `.cpp` | P1 |
| E3 | Directory-scope CMake (`include_directories`, `CMAKE_CXX_FLAGS`), `file(GLOB)` | leaking flags, stale builds | target-based CMake | P3 |
| E4 | No warnings, or warnings silenced with casts/pragmas | the compiler's free checks thrown away | warning set + `-Werror` in CI | P2 |
| E5 | No sanitizer or clang-tidy configuration at all | lifetime bugs found in production | ASan+UBSan CI, `.clang-tidy` ([tooling-testing.md](tooling-testing.md)) | P2 |
| E6 | Tests only for happy paths; `sleep` in concurrency tests | error paths untested; flaky tests | test each error value; deterministic sync | P2 |

## Process Smells in Agent Output

- **Fixing symptoms**: adding `if (ptr)` null checks or `shared_ptr` to silence a crash instead of fixing who owns the object. Ask what lifetime bug the null check is hiding.
- **Silencing tools**: `// NOLINT`, `#pragma warning(disable...)`, `-Wno-*`, `(void)` casts added without a reason. Each needs a justification comment or removal.
- **Scope creep**: reformatting or renaming unrelated files alongside a fix. Findings in review should separate the fix from incidental churn.
- **Duplicate utilities**: a second logger, a second string-split helper, a second `Result` type next to the project's existing one. Search before adding.
- **Dead code and TODO stubs**: unused functions, commented-out blocks, `// TODO: implement` bodies that return defaults -- stubs that return plausible values are worse than ones that fail.
