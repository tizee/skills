---
urls:
  - https://clang.llvm.org/docs/AddressSanitizer.html
  - https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
  - https://clang.llvm.org/docs/ThreadSanitizer.html
  - https://clang.llvm.org/docs/MemorySanitizer.html
  - https://clang.llvm.org/docs/LifetimeSafety.html
  - https://clang.llvm.org/docs/ClangStaticAnalyzer.html
  - https://clang.llvm.org/extra/clang-tidy/checks/list.html
  - https://valgrind.org/docs/manual/mc-manual.html
  - https://valgrind.org/docs/manual/ms-manual.html
  - https://llvm.org/docs/LibFuzzer.html
---

# Tooling and Testing

No single tool proves a C++ program free of lifetime errors. Deploy three kinds together:

- **Dynamic sanitizers** ask: did this execution go wrong?
- **Static analysis** asks: does some path in the code go wrong?
- **Runtime/heap diagnostics** ask: why does memory keep growing, and why is this object still alive?

## Tool Matrix

| Tool | Finds best | Blind spots / cost | Use for |
| --- | --- | --- | --- |
| **ASan** | heap/stack/global OOB, UAF, use-after-return/scope, double/invalid free | only executed paths; ~2x slowdown | every PR: unit + integration tests, fuzzing |
| **LSan** (ASan leak detection) | unreachable allocations at exit | reachable-but-useless memory is not a leak | leak gate on test exit |
| **UBSan** | signed overflow, bad shifts, null/misaligned deref, some OOB, invalid enum/bool | not lifetime tracking | combine with ASan |
| **TSan** | data races, lock-order inversions | 5-15x slowdown; cannot combine with ASan | separate job for threaded code |
| **MSan** | uninitialized reads | needs everything instrumented (incl. libc++) | dedicated Clang/Linux job |
| **Valgrind Memcheck** | invalid access, UAF, leak classification, no recompilation | 20-50x slowdown; Linux/x86/ARM | nightly, third-party binaries |
| **Valgrind Massif / heaptrack** | heap growth over time, retention | profiling, not correctness | "no leaks reported but RSS grows" |
| **clang-tidy** | ownership/API anti-patterns, Core Guidelines checks, bugprone patterns | heuristic; needs tuning | every commit |
| **Clang Static Analyzer** | path-sensitive leaks, double free, UAF, null deref | model limits; false positives/negatives | PR or periodic full scan |
| **Clang Lifetime Safety / `-Wdangling`** | dangling pointers/references/views, use-after-scope, container invalidation | bug finder, optimistic across calls without annotations | new and lifetime-heavy code |
| **Thread Safety Analysis** (`-Wthread-safety`) | lock discipline via `GUARDED_BY`/`REQUIRES` | only annotated code | concurrent modules |

## Build Recipes

```bash
# ASan + UBSan (development and CI)
cmake -B build-asan -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS="-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=undefined"
cmake --build build-asan && ctest --test-dir build-asan --output-on-failure

# TSan (separate build; incompatible with ASan)
cmake -B build-tsan -DCMAKE_CXX_FLAGS="-O1 -g -fsanitize=thread"

# Valgrind deep leak run
valgrind --leak-check=full --show-leak-kinds=all \
  --errors-for-leak-kinds=definite,possible --error-exitcode=1 ./build/integration_tests

# clang-tidy over the compilation database
run-clang-tidy -p build -quiet
```

Useful environment: `ASAN_OPTIONS=detect_leaks=1:detect_stack_use_after_return=1:strict_string_checks=1`, `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`.

On macOS, LSan is unavailable or unreliable with Apple Clang's ASan (notably on arm64); run leak checks on Linux CI, or use `leaks --atExit -- ./app`.

## clang-tidy Baseline

A starting `.clang-tidy` focused on ownership and bugs rather than style:

```yaml
Checks: >
  -*,
  bugprone-*,
  cppcoreguidelines-owning-memory,
  cppcoreguidelines-no-malloc,
  cppcoreguidelines-special-member-functions,
  cppcoreguidelines-virtual-class-destructor,
  cppcoreguidelines-slicing,
  cppcoreguidelines-pro-type-cstyle-cast,
  cppcoreguidelines-pro-type-member-init,
  cppcoreguidelines-init-variables,
  cppcoreguidelines-rvalue-reference-param-not-moved,
  modernize-make-unique,
  modernize-make-shared,
  modernize-use-override,
  modernize-use-nullptr,
  modernize-avoid-c-arrays,
  performance-unnecessary-value-param,
  performance-move-const-arg,
  performance-noexcept-move-constructor,
  misc-unconventional-assign-operator,
  misc-misplaced-const,
  clang-analyzer-*,
  concurrency-mt-unsafe
WarningsAsErrors: 'bugprone-use-after-move,bugprone-dangling-handle,clang-analyzer-cplusplus.NewDeleteLeaks'
```

Tune per project; a check that fires hundreds of times on legacy code is enabled for new directories first.

## CI Tiers

| Tier | Runs |
| --- | --- |
| Every PR | warnings-as-errors build, clang-tidy on changed files, ASan+UBSan unit tests |
| Main / daily | full ASan integration tests, Static Analyzer full scan |
| Concurrent modules | dedicated TSan job |
| Linux nightly | Valgrind Memcheck on a selected suite; MSan if feasible |
| New lifetime-heavy code | Clang Lifetime Safety / `-Wdangling*` |
| Parsers, protocol decoders, file formats, serialization | sanitizer-enabled fuzzing (libFuzzer, AFL++) |
| Long-running services | heap/RSS/object-count time series in production |

Sanitizers only report executed paths. For code that parses external bytes, fuzzing buys more coverage than more hand-written tests.

## Leak vs Retention

- **Leak**: every pointer to the memory is lost. ASan/LSan/Memcheck report it.
- **Retention**: the memory is still reachable but useless -- unbounded caches, `shared_ptr` cycles, long-lived `weak_ptr` holding `make_shared` storage, listeners never unregistered, queues never drained. Leak checkers usually stay silent.

"0 leaks" is not "memory-correct". For services, watch heap growth curves, per-type live-object counts, cache cardinality, and the shared-ownership graph. A diagnostic live counter is cheap:

```cpp
class Connection {
public:
    Connection() { live_count.fetch_add(1, std::memory_order_relaxed); }
    ~Connection() { live_count.fetch_sub(1, std::memory_order_relaxed); }
    inline static std::atomic<std::size_t> live_count{0};
};
```

Note the counter misses copies/moves unless those constructors increment too. `shared_ptr::use_count()` is fine for diagnostics, never for logic.

## Testing Practice

- Use the project's framework (GoogleTest, Catch2, doctest). Tests build and run via `ctest`.
- Test behavior through public interfaces; seams via constructor-injected dependencies, not via `#define private public` or friend-test hacks.
- Cover each error path: every error enum value / exception type has a test that produces it.
- Boundaries: empty, one, capacity-1, capacity, capacity+1, max values, negative/overflow inputs.
- Ownership tests: moved-from objects destructible and assignable; destruction order in teardown; callbacks firing after owner destruction do not crash (with sanitizers on).
- Concurrency tests run under TSan with enough iterations to interleave; avoid `sleep`-based synchronization in tests.
- Tests follow the same rules as production code (no raw `new`, checked results).

## Review Questions

- Did the tests run under ASan+UBSan? Concurrent code under TSan? Which commands could not run?
- Is there a `.clang-tidy` with ownership/bugprone checks, and is it clean on the changed files?
- Does any parser of external input lack a fuzz target?
- For long-running services: is retention (not just leaks) observable?
