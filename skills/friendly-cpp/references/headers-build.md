---
urls:
  - https://google.github.io/styleguide/cppguide.html#Header_Files
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-source
  - https://cliutils.gitlab.io/modern-cmake/
  - https://best.openssf.org/Compiler-Hardening-Guides/Compiler-Options-Hardening-Guide-for-C-and-C++.html
---

# Headers and Build

## Headers

- Every header is self-contained: it compiles when included first in an empty `.cpp`. Include what you use; never rely on transitive includes.
- Guard with `#pragma once` or a `PROJECT_PATH_FILE_H_` guard -- match the project.
- **Never `using namespace` in a header** (at namespace scope). It leaks into every includer. In `.cpp` files, prefer targeted `using std::string;` or namespace aliases; `using namespace std;` is a finding.
- Headers declare; `.cpp` files define. Exceptions: templates, `constexpr`/`inline` functions, and short member functions that benefit from inlining.
- Non-`inline` function or variable definitions in a header violate the ODR when included twice (link errors, or silently different definitions). Namespace-scope constants in headers: `inline constexpr`.
- Forward-declare to cut compile-time dependencies only where it does not obscure ownership (a `std::unique_ptr<Impl>` member requires the destructor defined where `Impl` is complete).
- Include order: related header, C system, C++ standard, third-party, project. Let `clang-format` sort within groups.

## Namespaces and Linkage

- All project code lives in a project namespace. No code in the global namespace besides `main`.
- File-local helpers go in an unnamed namespace (or `static`), not in the project namespace, so they cannot collide at link time.
- No `namespace std { ... }` additions except permitted specializations (`std::hash<MyType>`).

## Source Layout

- One class or cohesive group of functions per header/source pair; file names match the primary type.
- A `.cpp` over ~1000 lines or a class over ~30 public members is a design smell (god object). Split by responsibility.
- Keep `main.cpp` thin: parse arguments, build the object graph, run, map errors to exit codes.

## CMake (Target-Based)

```cmake
cmake_minimum_required(VERSION 3.20)
project(app LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)   # for clang-tidy / clangd

add_library(core src/parser.cpp src/session.cpp)
target_include_directories(core PUBLIC include)
target_compile_options(core PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wnon-virtual-dtor -Wold-style-cast -Woverloaded-virtual -Wnull-dereference -Wimplicit-fallthrough>
  $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->)

add_executable(app src/main.cpp)
target_link_libraries(app PRIVATE core)
```

Anti-patterns agents commonly write:

- `include_directories()`, `add_definitions()`, `link_libraries()`, or `set(CMAKE_CXX_FLAGS "...")` at directory scope -- use `target_*` commands with `PUBLIC`/`PRIVATE`/`INTERFACE`.
- `file(GLOB ...)` for sources -- new files are not picked up without re-running CMake. List sources explicitly.
- Hardcoded `-O2`/`-g` in flags instead of `CMAKE_BUILD_TYPE`.
- Vendored copies of dependencies with local edits. Use `find_package`, `FetchContent` with a pinned tag/hash, or the project's package manager (vcpkg/Conan).
- Missing `CMAKE_CXX_STANDARD_REQUIRED ON`, so the compiler silently falls back to an older standard.

## Warnings

- Treat warnings as errors in CI (`-Werror` / `/WX` or `CMAKE_COMPILE_WARNING_AS_ERROR ON`), not necessarily on developer machines with newer compilers.
- Do not suppress warnings with casts or pragmas to make them go away; fix the cause. A local, commented `#pragma` for third-party headers (or `SYSTEM` includes) is fine.
- Useful extras: `-Wreturn-type` (as error), `-Wformat=2`, `-Wduplicated-cond`, `-Wlogical-op` (GCC), `-Wrange-loop-analysis` / `-Wdangling` family (Clang).

## Hardening for Release

- `-D_FORTIFY_SOURCE=3` (with optimization), `-fstack-protector-strong`, `-fstack-clash-protection`, `-fPIE -pie`, `-Wl,-z,relro,-z,now`.
- Standard library hardening: libc++ `_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_FAST`, libstdc++ `_GLIBCXX_ASSERTIONS` -- bounds-checks `operator[]`, `front()`, etc. at low cost. Consider enabling in production.

## Formatting and Naming

- Enforce formatting with a checked-in `.clang-format`; do not hand-review whitespace.
- Naming: follow the project. If none exists, pick one convention (e.g. `snake_case` functions/variables, `PascalCase` types, `kConstant` or `UPPER_CASE` constants, trailing `_` for members) and apply it everywhere. Mixed conventions in one codebase are a finding.
- No leading underscore + capital or double underscore in identifiers -- reserved.

## Review Questions

- Is every header self-contained, guarded, free of `using namespace`, and free of non-inline definitions?
- Is file-local code in an unnamed namespace? Is project code namespaced?
- Is CMake target-based, with explicit sources, a required standard, and warnings on per target?
- Does CI build with warnings as errors? Any warning silenced by cast or pragma instead of fixed?
- Are `.clang-format` and `.clang-tidy` present and used?
