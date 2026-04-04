---
urls:
  - https://doc.rust-lang.org/book/ch19-06-macros.html
  - https://doc.rust-lang.org/reference/macros-by-example.html
  - https://docs.rs/proc-macro2/latest/proc_macro2/
---

# Macros

## Goals

- Eliminate repetitive boilerplate while keeping core logic visible and testable.
- Choose the right level of abstraction: generics first, declarative macros second, proc macros last.
- Avoid macros that obscure control flow or make debugging harder.

## When to Use Macros

Macros are appropriate when:

- You have **truly repetitive** code that generics and traits cannot abstract (e.g., implementing a trait for 10 concrete types with the same pattern).
- You need **variadic arguments** (e.g., `vec![1, 2, 3]`, `println!`).
- You need **compile-time code generation** from attributes or derives.

Macros are not appropriate when:

- A generic function or trait would work. Generics produce better error messages and are easier to debug.
- The pattern occurs only 2-3 times. The macro complexity may exceed the repetition cost.
- The macro hides control flow (`return`, `break`, `?`). This makes code hard to reason about.

## Declarative Macros (macro_rules!)

Use for syntactic pattern matching and repetition:

```rust
// Generate trait impls for multiple types.
macro_rules! impl_display_for_newtype {
    ($($t:ty),+ $(,)?) => {
        $(
            impl std::fmt::Display for $t {
                fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                    write!(f, "{}", self.0)
                }
            }
        )+
    };
}

struct Meters(f64);
struct Seconds(f64);
impl_display_for_newtype!(Meters, Seconds);
```

Keep the core logic outside the macro and use the macro only for the repetitive shell. This makes the algorithm testable and the macro reviewable.

## Procedural Macros

Proc macros operate on token streams and are defined in separate crates. Three kinds:

| Kind | Syntax | Use Case |
| --- | --- | --- |
| Custom derive | `#[derive(MyTrait)]` | Auto-implement traits for structs/enums |
| Attribute | `#[my_attr]` | Transform annotated items |
| Function-like | `my_macro!(...)` | Arbitrary input processing |

Use `proc-macro2` for the stable API and `syn` + `quote` for parsing and generating tokens. Derive macros are the most common; prefer them over attribute macros when you're generating trait implementations.

## Anti-Pattern: Macro That Hides Control Flow

```rust
macro_rules! try_or_return {
    ($expr:expr) => {
        match $expr {
            Ok(v) => v,
            Err(_) => return, // hidden return -- surprising
        }
    };
}
```

The caller sees `try_or_return!(something)` but doesn't realize the function might return. Use `?` instead -- it makes the early return visible.

## Anti-Pattern: Macro for One-Off Boilerplate

```rust
// Used exactly once. A normal function would be clearer.
macro_rules! setup_logger {
    () => {
        env_logger::Builder::from_default_env()
            .filter_level(log::LevelFilter::Info)
            .init();
    };
}
```

If it's used once, write a function. Macros earn their complexity only through repetition.

## Hygiene

Declarative macros are hygienic by default -- identifiers created inside the macro don't collide with identifiers in the calling scope. Proc macros need explicit care:

- Use `Span::call_site()` for identifiers that should resolve in the caller's scope.
- Use `Span::mixed_site()` for generated helper names that shouldn't leak.
- Test that macro-generated code compiles in different module contexts.

## Debugging Macros

- `cargo expand` shows the expanded output of all macros in a file. Essential for debugging.
- Add `#[cfg(test)]` tests that exercise macro-generated code to catch expansion errors.
- For proc macros, return `compile_error!("...")` with a clear message on invalid input rather than panicking.
