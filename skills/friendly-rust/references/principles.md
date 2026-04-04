---
urls:
  - https://doc.rust-lang.org/book/
  - https://rust-lang.github.io/api-guidelines/
  - https://doc.rust-lang.org/nomicon/
---

# Core Principles

## Goals

- Make invalid states unrepresentable through types and visibility.
- Work with the borrow checker -- if the compiler fights you, the design likely needs rethinking.
- Future maintainers should find intent, boundaries, and change points quickly.

## Decision Order

1. Correctness and safety
2. Readability and maintainability
3. Extensibility and evolution cost
4. Performance and optimization

## Principles

- **Encode invariants in types.** Use newtypes, enums, and visibility to make illegal states impossible rather than checking them at runtime.
- **Prefer ownership clarity.** Every value has a clear owner. If a function needs to own data, take ownership. If it only reads, borrow. Do not default to cloning to silence the compiler.
- **Keep unsafe islands small and contained.** When unsafe is needed, isolate it behind a safe API in a private module. The module boundary is your primary containment tool.
- **Fail loudly at boundaries.** Validate inputs at public API surfaces and return meaningful errors. Never silently swallow failures or substitute defaults that mask broken state.
- **Measure before optimizing.** Rust's zero-cost abstractions are real, but "zero-cost" means "no cost you didn't ask for" -- it does not mean "always fast." Profile before rewriting.

## Anti-Pattern

Cloning to silence the borrow checker without understanding why:

```rust
// The clone here hides a design problem -- data is borrowed
// and owned at the same time because responsibilities are mixed.
fn process(data: &Vec<String>) -> Vec<String> {
    let mut owned = data.clone(); // hides the real issue
    owned.sort();
    owned
}
```

## Positive Pattern

Rethink ownership so the caller decides:

```rust
// Caller passes owned data when mutation is needed.
fn process(mut data: Vec<String>) -> Vec<String> {
    data.sort();
    data
}
```
