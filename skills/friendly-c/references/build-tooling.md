---
urls:
  - https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html
  - https://best.openssf.org/Compiler-Hardening-Guides/Compiler-Options-Hardening-Guide-for-C-and-C++.html
  - https://clang.llvm.org/extra/clang-tidy/
---

# Build and Tooling

In C the compiler is the only static analyzer you get for free, and by default it is switched almost entirely off. Turning it on is the highest-value change most C projects can make.

## Warning flags

Baseline, from the first commit:

```
-std=c11 -Wall -Wextra -Werror -Wconversion -Wshadow
```

- `-Wconversion` is the one people skip and the one that catches real bugs: silent narrowing and signedness changes.
- `-Wshadow` catches the inner `len` hiding the outer `len`.
- `-Werror` from day one. Retrofitting it onto a warning-rich codebase never happens.

Worth adding:

| Flag | Catches |
| --- | --- |
| `-Wvla` | Variable length arrays (banned -- unbounded stack) |
| `-Wwrite-strings` | Writing through a string literal |
| `-Wstrict-prototypes` | `f()` meaning "any arguments" instead of `f(void)` |
| `-Wmissing-prototypes` | A non-static function with no prototype -- usually a missing `static` |
| `-Wcast-align` | Alignment-increasing pointer casts |
| `-Wpointer-arith` | Arithmetic on `void *` |
| `-Wdouble-promotion` | Accidental float-to-double on embedded targets |
| `-Wformat=2` | Format string mismatches and non-literal formats |

## Release hardening

```
-D_FORTIFY_SOURCE=3 -fstack-protector-strong -fstack-clash-protection
-fPIE -Wl,-z,relro,-z,now -Wl,-z,noexecstack
```

`_FORTIFY_SOURCE` requires optimization to be on (`-O1` or higher). These turn a class of memory bugs from exploits into crashes; they are not a substitute for the rules in [undefined-behavior.md](undefined-behavior.md).

## Debug and test builds

```
-g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer
```

Run the whole test suite this way, in CI, on every commit. See [testing.md](testing.md). Never ship sanitizer builds -- they are debugging tools, not hardening.

## Static analysis

Layer these; they find different things:

- **`clang-tidy`** with `clang-analyzer-*`, `bugprone-*`, `cert-*`, `readability-*`. Check in a `.clang-tidy` so everyone runs the same set.
- **`cppcheck --enable=warning,style,performance,portability`** -- fast, catches different patterns than clang.
- **`scan-build`** (clang static analyzer) for path-sensitive bugs: null derefs and leaks along specific branches.
- **`gcc -fanalyzer`** (GCC 10+) for double-free, use-after-free, and leak paths.

Run at least one in CI. A finding a tool reports is a finding no reviewer has to spend attention on.

## Formatting

Check in a `.clang-format` and stop discussing style:

```yaml
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
AlwaysBreakAfterReturnType: TopLevelDefinitions
PointerAlignment: Right
```

Enforce it in CI with `clang-format --dry-run --Werror`.

## Choosing the standard

| Standard | When |
| --- | --- |
| **C11** | Default. `static_assert`, `<stdatomic.h>`, anonymous structs/unions, `_Generic`. Universally available. |
| **C17** | C11 with defect fixes. Free upgrade if the toolchain supports it. |
| **C23** | Only when every target toolchain supports it. Brings `nullptr`, `constexpr`, `typeof`, `enum` with fixed underlying type, `[[nodiscard]]`. |
| **C99** | Legacy targets only. You lose `static_assert` and atomics. |

Pin it explicitly (`-std=c11`, not `gnu11`) so the build does not silently depend on extensions. If GNU extensions are needed, use `gnu11` deliberately and say why.

## Project layout

```
src/            module .c files
include/proj/   public headers, one per module
tests/          test_<module>.c, one per module
fuzz/           libFuzzer targets
CMakeLists.txt  or Makefile
.clang-format
.clang-tidy
```

- One module = one `.c` + one `.h`, sharing a name and a symbol prefix.
- Public headers live under a directory named after the project so `#include <proj/rb.h>` is unambiguous at the consumer.
- Internal headers stay in `src/` and are never installed.

## A minimal CMake baseline

```cmake
cmake_minimum_required(VERSION 3.16)
project(proj C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)         # -std=c11, not -std=gnu11
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)   # feeds clang-tidy and editors

add_library(proj src/rb.c src/sensor.c)
target_include_directories(proj PUBLIC include)
target_compile_options(proj PRIVATE
    -Wall -Wextra -Werror -Wconversion -Wshadow -Wvla -Wstrict-prototypes)

option(PROJ_SANITIZE "Build with ASan+UBSan" OFF)
if(PROJ_SANITIZE)
    target_compile_options(proj PUBLIC -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(proj PUBLIC -fsanitize=address,undefined)
endif()
```

`CMAKE_EXPORT_COMPILE_COMMANDS` is not optional: `compile_commands.json` is what clang-tidy, clangd, and every editor integration need to work at all.

## CI gates

Make the correct path the default by putting it in the pipeline, not a wiki:

| Trigger | Gate |
| --- | --- |
| Save | `clang-format` |
| Commit | Build with `-Werror`, `clang-tidy` on changed files |
| Push / PR | Full test suite under ASan+UBSan, TSan run for threaded code |
| Nightly | Fuzz targets for a bounded time, `cppcheck`/`scan-build` full scan |

Discipline that lives in a pipeline survives; discipline that lives in a document does not.

## Dependencies

C has no standard package manager, and that is a feature to exploit: the cheapest dependency is the one you do not take. When you do take one, prefer single-file libraries vendored into `third_party/` with the commit hash recorded, so the build is reproducible and the code is auditable. Build vendored code with its own warning settings -- do not weaken yours to accommodate it.
