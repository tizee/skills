---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-templates
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-stdlib
  - https://en.cppreference.com/w/cpp/algorithm
  - https://en.cppreference.com/w/cpp/language/constraints
---

# Generic Code and the Standard Library

Two opposite failure modes show up in agent-written C++: hand-rolled loops and containers that reimplement the standard library badly, and template metaprogramming nobody asked for. Both cost the reader.

## Standard Library First

- Containers: `std::vector` by default. `std::array` for fixed size. `std::unordered_map` for lookup unless ordering is needed (`std::map`). `std::deque`/`std::list` only for their specific guarantees (stable references, O(1) splice). Do not write custom linked lists, dynamic arrays, or string classes.
- Algorithms over raw loops when an algorithm names the intent: `std::find_if`, `std::any_of`, `std::count_if`, `std::transform`, `std::accumulate`, `std::sort`, `std::partition`, `std::erase_if` (C++20). C++20 ranges (`std::ranges::sort(v)`, `views::filter`) when the project is on C++20.
- A range-for is fine and often clearer than an algorithm + lambda. The goal is naming intent, not eliminating loops.
- `std::optional`, `std::variant`, `std::string_view`, `std::span`, `std::filesystem`, `std::chrono` replace sentinel values, tagged unions, `char*` + length, `T*` + size, string path concatenation, and raw integer milliseconds.

```cpp
// Anti-pattern: manual search with flag and index bookkeeping.
bool found = false;
int idx = -1;
for (int i = 0; i < (int)users.size(); i++) {
    if (users[i].id == id) { found = true; idx = i; break; }
}
if (found) notify(users[idx]);

// Positive
auto it = std::ranges::find(users, id, &User::id);
if (it != users.end()) notify(*it);
```

- Use `std::chrono` types for durations and time points in APIs: `void set_timeout(std::chrono::milliseconds)` beats `void set_timeout(int ms)` -- units are checked.
- `reserve` when the final size is known; do not `shrink_to_fit` reflexively.
- `emplace_back` only when constructing in place from constructor arguments; for an existing object, `push_back(std::move(x))` is clearer. `emplace_back` with `new T` into a `vector<unique_ptr<T>>` leaks if the vector reallocation throws -- use `push_back(std::make_unique<T>())`.

## Templates: Only When They Pay

Write a template when you have (or will imminently have) two or more concrete types, and the code is genuinely identical. Otherwise write the concrete function.

- Constrain templates. C++20: concepts (`template <std::integral T>`, or a named concept). C++17: `static_assert` with a clear message, or `std::enable_if_t` only if overload selection needs it.
- Unconstrained templates produce errors deep in instantiation and accept types they cannot handle.
- Keep template definitions small; move type-independent code into non-template functions in a `.cpp`.
- Avoid template metaprogramming (recursive templates, SFINAE tricks, type-list machinery) in application code. `if constexpr`, fold expressions, and concepts cover most real needs readably.
- CRTP, policy classes, expression templates, and tag dispatch are library-author tools. In application code each needs a stated reason.

```cpp
// Anti-pattern: unconstrained, SFINAE soup for a two-type use.
template <typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
auto clamp_add(T a, T b, T hi) -> decltype(a + b) { ... }

// Positive (C++20)
template <std::integral T>
T clamp_add(T a, T b, T hi);
```

## Type Erasure and Callables

- `std::function` owns a callable (may allocate); `std::function_ref` (C++26) / `absl::FunctionRef` / `llvm::function_ref` only borrow and must not be stored.
- For a parameter used during the call only, a template parameter (`std::invocable<Arg> auto&& f`) or a `function_ref` avoids allocation. For stored callbacks, `std::function` (or `std::move_only_function`, C++23) is right.
- Virtual interfaces are type erasure too; choose based on whether the set of implementations is open.

## Macros

- Macros only for what the language cannot do: include guards (or `#pragma once`), conditional compilation for platforms, and a few logging/assert macros that need `__FILE__`/`__LINE__` (or use `std::source_location`, C++20).
- Constants -> `constexpr`. Function-like macros -> `inline`/`constexpr` functions or templates. Type aliases -> `using`.
- Every remaining macro is `UPPER_CASE`, fully parenthesized, and `#undef`d if local.

## Review Questions

- Any hand-written container, string, or algorithm that the standard library already provides?
- Any raw loop whose intent a named algorithm expresses better? (And conversely, any algorithm+lambda chain that a plain loop would make clearer?)
- Any template with a single instantiation, or without constraints?
- Any SFINAE/TMP/CRTP in application code without a stated reason?
- Any stored `function_ref`/view-like callable? Any `int ms` where `std::chrono` fits?
- Any macro that could be `constexpr`, `inline`, or `using`?
