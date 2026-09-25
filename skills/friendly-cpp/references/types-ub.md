---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-expr
  - https://en.cppreference.com/w/cpp/language/ub
  - https://en.cppreference.com/w/cpp/language/initialization
  - https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
---

# Types, Casts, and Undefined Behavior

UB is not "implementation-specific behavior". The optimizer assumes it never happens and deletes code paths accordingly, so UB bugs appear only in release builds, only on some compilers, and far from the cause.

## Initialization

- Initialize every variable at declaration. Uninitialized scalars (`int n;`) read before write are UB. Prefer declaring at first use with its real value.
- Prefer brace-init for its narrowing check: `std::int32_t x{some_int64};` fails to compile; `x = some_int64;` silently truncates.
- Beware `std::vector<int> v{10, 0};` (two elements) vs `v(10, 0)` (ten zeros): initializer-list constructors win braces.
- Members get default initializers (`int retries_ = 3;`) so no constructor can forget them.
- Use `constexpr` for compile-time constants, `inline constexpr` for namespace-scope constants in headers. No `#define` constants.

## Casts

| Cast | Use |
| --- | --- |
| `static_cast` | well-defined conversions: numeric, up/down a known hierarchy, `void*` back to its type |
| `dynamic_cast` | checked downcast; frequent use signals a missing virtual function or a variant |
| `const_cast` | only to call a legacy API that is const-incorrect but does not write |
| `reinterpret_cast` | low-level byte views and FFI; needs a comment and usually `std::bit_cast`/`memcpy` instead |
| C-style `(T)x` / functional `T(x)` for non-class `T` | **never** -- it silently picks `reinterpret_cast` or `const_cast` when `static_cast` fails |

- Type punning through `reinterpret_cast` or unions violates strict aliasing. Use `std::bit_cast` (C++20) or `std::memcpy`. Accessing bytes via `char`/`unsigned char`/`std::byte` pointers is the exception.
- `std::launder`, placement new, and manual lifetime (`std::start_lifetime_as`, C++23) belong only in allocator/container internals.

## Integers

- Signed overflow is UB. Validate ranges before arithmetic, use wider types, or `__builtin_*_overflow` / checked helpers.
- Mixing signed and unsigned in comparisons converts the signed side: `-1 < v.size()` is false. Use `std::cmp_less` (C++20), `std::ssize`, or keep indices `std::size_t` consistently. `-Wsign-compare`.
- `v.size() - 1` wraps when `v` is empty.
- Shifts by >= the width, or of negative values, are UB (left shift of negative until C++20).
- `int` is not `int32_t`. Use fixed-width types for wire formats and file formats; `std::size_t` for sizes and indices; `std::ptrdiff_t` for differences.
- Implicit narrowing (`double -> int`, `int64 -> int32`, `size_t -> int`) needs an explicit, checked conversion: `gsl::narrow`, or a helper that validates range. `-Wconversion` finds them.

## `auto`

- Use `auto` when the type is obvious from the right-hand side (`auto p = std::make_unique<Foo>()`), is an iterator, or is unutterable (lambdas).
- Avoid `auto` when it hides ownership or numeric type that matters for correctness: `auto n = compute();` where `n` is `unsigned` or a proxy.
- `auto` drops references and top-level const: `auto x = container.front();` copies. Use `const auto&` to borrow, and remember the borrow's lifetime.
- Proxy types: `auto b = vec_of_bool[i];` is a `std::vector<bool>::reference` into the vector, not a `bool`.

## Common UB Catalog

| UB | Typical agent form | Fix |
| --- | --- | --- |
| Out-of-bounds access | `v[i]` with unchecked `i` from input | validate at the boundary; `.at()` in non-hot code; `span` |
| Null dereference | `find()` result used without check; `*opt` on empty optional | check; return `optional`/`expected` |
| Use after free/scope | see [lifetime-traps.md](lifetime-traps.md) | owner-first design |
| Uninitialized read | POD member without initializer | default member initializers |
| Signed overflow | `int total = a * b;` on input sizes | wider type or checked math |
| Data race | plain flag shared across threads | `std::atomic`, mutex |
| Strict aliasing | `*reinterpret_cast<float*>(&u32)` | `std::bit_cast` |
| Deleting through base without virtual dtor | `unique_ptr<Base>` of `Derived` | virtual destructor |
| Modifying a `const` object | `const_cast` then write | redesign |
| Iterator invalidation | erase in range-for | `std::erase_if` |
| Infinite loop without side effects | busy-wait spin on a plain variable | atomic + proper wait |
| Missing `return` in non-void function | falls off the end in one branch | `-Werror=return-type` |
| Mismatched `new[]`/`delete` | `delete` on an array | `vector` / `unique_ptr<T[]>` |
| `memcpy`/`memset` on non-trivially-copyable types | `memset(this, 0, sizeof *this)` | value-initialize; `= {}` |

## Strings and Formatting

- `std::string` / `std::string_view`, never raw `char*` buffers in business code.
- `std::format` (C++20) or `fmt::format` instead of `sprintf`/`snprintf`. Stream formatting is acceptable but slow and stateful (`std::hex` sticks).
- `std::endl` flushes; use `'\n'` unless a flush is intended.
- Arrays: `std::array<T, N>` over C arrays; `std::size(arr)` over `sizeof(a)/sizeof(a[0])`.

## Review Questions

- Any uninitialized variable or member? Any narrowing conversion without a checked helper?
- Any C-style cast? Any `reinterpret_cast` or union pun without `bit_cast`/`memcpy`?
- Any signed/unsigned comparison, unguarded `size() - 1`, or unchecked arithmetic on external sizes?
- Any `auto` hiding a copy, a proxy, or a numeric type that matters?
- Any entry from the UB catalog above?
