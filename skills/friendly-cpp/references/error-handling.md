---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-errors
  - https://google.github.io/styleguide/cppguide.html#Exceptions
  - https://en.cppreference.com/w/cpp/utility/expected
  - https://en.cppreference.com/w/cpp/language/exceptions#Exception_safety
---

# Error Handling

The rule that matters more than "exceptions or not": **one error strategy per layer, applied consistently, and no failure silently discarded.** Agent-written C++ typically mixes `bool` returns, `-1`, `nullptr`, exceptions, and log-and-continue in the same module.

## Pick the Strategy From the Project

Check before writing anything:

- Compiled with `-fno-exceptions` (common in games, embedded, Google-style code)? Then exceptions are unavailable; use `std::expected` (C++23), `absl::StatusOr`, `tl::expected`, or the project's own result type.
- Existing error type in the codebase? Use it. Introducing a second vocabulary is a finding, not an improvement.

Default when free to choose:

| Situation | Mechanism |
| --- | --- |
| Precondition violated by the caller (bug) | `assert` / contract check / `std::terminate` -- not a recoverable error |
| Expected, local failure the caller handles (parse error, not found, validation) | `std::expected<T, E>` / `std::optional<T>` (only when "absent" is the whole story) |
| Rare failure far from the handler, or constructor failure | exception derived from `std::exception` |
| OS/C API failure | `std::error_code` / `std::system_error` with `errno` preserved |

## Exceptions Done Right

- Throw by value, catch by `const&`: `catch (const ParseError& e)`. Catching by value slices.
- Throw types derived from `std::exception` carrying the context needed to act (path, offset, id). Never throw `int`, `const char*`, or `std::string`.
- Catch only where you can do something: recover, add context and rethrow, or translate at a boundary (thread entry, C API, `main`, request handler).
- `throw;` rethrows the original; `throw e;` slices and copies.
- Destructors, deleters, move operations, `swap`, and cleanup paths are `noexcept`. A throwing destructor during unwinding calls `std::terminate`.
- Exceptions must not cross C APIs, thread entry functions, or callbacks invoked by C code -- catch at that boundary.

```cpp
// Anti-pattern: swallow everything, continue with garbage.
try {
    cfg = load_config(path);
} catch (...) {
    std::cerr << "error\n";
}
start_server(cfg);          // runs with default/half-initialized config

// Positive: let it propagate, or handle meaningfully.
Config cfg = load_config(path);   // failure stops startup loudly

// Or, at a boundary that must not throw:
int main(int argc, char** argv) try {
    return run(argc, argv);
} catch (const std::exception& e) {
    std::fprintf(stderr, "fatal: %s\n", e.what());
    return EXIT_FAILURE;
}
```

## `expected`-Style Results

```cpp
enum class ParseError { empty_input, bad_digit, overflow };

[[nodiscard]] std::expected<std::uint32_t, ParseError> parse_port(std::string_view s);

auto port = parse_port(arg);
if (!port) return std::unexpected(port.error());   // propagate unchanged
listen(*port);
```

- Mark result-returning functions and result types `[[nodiscard]]` so ignoring them is a warning.
- Use an `enum class` (or small struct) error type per module; do not stringly-type errors.
- `optional` is for "no value" with a single obvious reason. Two or more failure reasons need `expected`.
- `.value()` on an empty `expected`/`optional` throws; `*` on an empty one is UB. Check first.

## Exception-Safety Guarantees

State which one each mutating operation gives:

- **Strong**: on failure, observable state is unchanged. Build new state aside, then commit with non-throwing operations (`swap`, `std::move` of `noexcept` types).
- **Basic**: on failure, invariants hold and nothing leaks; values may have changed.
- **No-throw**: `noexcept`.

```cpp
// Strong guarantee via copy-and-swap / build-then-commit.
void Registry::replace_all(std::vector<Entry> entries) {
    auto index = build_index(entries);   // may throw; nothing modified yet
    entries_.swap(entries);              // noexcept
    index_.swap(index);                  // noexcept
}
```

RAII is what makes the basic guarantee cheap: if every resource is owned by an object, nothing leaks on unwind.

## `noexcept`

- Required: destructors (implicit), move constructor/assignment, `swap`, deleters, functions called from destructors.
- Do not sprinkle `noexcept` on functions that allocate or call throwing code: an exception escaping a `noexcept` function is `std::terminate`, not a propagated error.

## Logging and Errors

- Log at the layer that handles the error, not at every layer it passes through. "Log and rethrow" at each level produces N copies of one failure.
- Never replace an error with a default value to keep going unless the default is genuinely correct, and say why in a comment.

## Review Questions

- Is there one error mechanism per layer, matching the project's policy (exceptions on/off, existing result type)?
- Any `catch (...)` that does not rethrow or terminate? Any catch by value? Any `throw e;`?
- Any ignored return value of a fallible function? Are result types `[[nodiscard]]`?
- Any `bool`/`-1`/`nullptr` return carrying more than one failure reason?
- Can any destructor, deleter, or move throw? Is `noexcept` placed on anything that can throw?
- Does each mutating operation meet at least the basic guarantee? Where strong is claimed, is it delivered?
