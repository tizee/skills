---
urls:
  - https://rust-lang.github.io/api-guidelines/
  - https://rust-lang.github.io/api-guidelines/naming.html
  - https://rust-lang.github.io/api-guidelines/type-safety.html
---

# API Design

## Goals

- Public APIs should be hard to misuse and easy to use correctly.
- Follow Rust conventions so users can rely on ecosystem muscle memory.
- Keep public surfaces small and stable; hide internal wiring.

## Guidance

### Trait Implementations

- **Implement standard traits where they make sense.** `Debug`, `Clone`, `PartialEq`, `Eq`, `Hash`, `Display`, `Default`, `From`, `TryFrom`, `AsRef`, `Deref` (for smart pointers only). Missing a common trait is a papercut for every consumer.
- **Implement `From` rather than `Into`.** `From` gives you `Into` for free via the blanket impl. Implementing `Into` directly is almost always wrong.
- **Implement `TryFrom` for fallible conversions.** Returning `Result` from conversion makes the failure mode explicit.
- **Make types `Send + Sync` where valid.** Types used in async or threaded contexts should be `Send + Sync`. If they can't be, document why. Add compile-time assertions in tests.

### Visibility

- **Default to `pub(crate)`, promote to `pub` deliberately.** Every `pub` item is a commitment. Minimize the public surface.
- **Use re-exports to control the public shape.** Expose a clean `pub` API from `lib.rs` or a `pub mod api` while keeping internal module structure private.
- **Keep struct fields private.** Public fields lock you into a representation. Use constructors and accessors; derive `Debug` for inspectability.

### Builders and Constructors

- **Use builders for types with many optional parameters.** The builder pattern avoids functions with 8 parameters and makes defaults explicit.
- **Provide `new()` for simple cases.** If there are only 1-2 required fields, a plain constructor is clearer than a builder.

### Naming

- **Follow Rust naming conventions.** `snake_case` for functions/variables, `CamelCase` for types/traits, `SCREAMING_SNAKE` for constants. Clippy enforces most of these.
- **Use `_mut` suffix for mutable-access methods** (e.g., `fn get(&self)` / `fn get_mut(&mut self)`).
- **Getters don't use `get_` prefix.** Rust convention: `fn name(&self) -> &str`, not `fn get_name(&self) -> &str`.

### Documentation

- **Every public item gets a doc comment.** Enforce with `#![deny(missing_docs)]`.
- **Include `# Examples` that use `?`.** Users copy-paste; model proper error handling.
- **Add `# Errors` for functions returning `Result`.** Describe when each error variant occurs.
- **Add `# Panics` if the function can panic.** Document the preconditions.
- **Add `# Safety` for `unsafe fn`.** Document the caller's obligations.

## Anti-Pattern: Over-Exposed Internals

```rust
pub struct Config {
    pub db_url: String,       // locked into String representation
    pub pool_size: usize,     // changing this field name is breaking
    pub retry_config: RetryConfig, // leaks internal type
}
```

## Positive Pattern: Controlled Surface

```rust
pub struct Config { /* fields private */ }

impl Config {
    pub fn builder() -> ConfigBuilder {
        ConfigBuilder::default()
    }

    pub fn db_url(&self) -> &str {
        &self.db_url
    }

    pub fn pool_size(&self) -> usize {
        self.pool_size
    }
}
```

## Anti-Pattern: Stringly-Typed APIs

```rust
// Caller can pass any string, including typos. Fails at runtime.
pub fn set_log_level(level: &str) { /* ... */ }
set_log_level("degub"); // compiles, panics at runtime
```

## Positive Pattern: Enum-Typed APIs

```rust
pub enum LogLevel { Debug, Info, Warn, Error }
pub fn set_log_level(level: LogLevel) { /* ... */ }
// set_log_level(LogLevel::Degub); // compile error -- caught immediately
```

Use enums for any parameter with a fixed set of valid values. This eliminates an entire class of typo-driven bugs and gives callers IDE autocomplete.

## Anti-Pattern: Boolean Parameter Trap

```rust
// What do these booleans mean? Unreadable at the call site.
connect("host", true, false, true);
```

## Positive Pattern: Enums or Builder for Clarity

```rust
pub enum Compression { Enabled, Disabled }
pub enum Tls { Required, Optional }

connect("host", Compression::Enabled, Tls::Required);
// Or use a builder for many options:
Connection::builder().host("host").compression(true).tls(true).build();
```

## Anti-Pattern: Deref as Inheritance

```rust
// Using Deref to simulate OOP inheritance -- confusing.
use std::ops::Deref;
struct Admin { user: User }
impl Deref for Admin {
    type Target = User;
    fn deref(&self) -> &User { &self.user }
}
```

`Deref` should only be used for smart pointer types. For code reuse, prefer composition with explicit delegation or traits for shared behavior.

## Object Safety

If a trait is intended for dynamic dispatch (`dyn Trait`), ensure it is object-safe:

- No generic methods (unless bounded with `where Self: Sized`).
- No `Self` in return position (unless bounded).
- No associated constants or types with defaults that reference `Self`.

Mark non-object-safe methods with `where Self: Sized` so the trait can still be used as `dyn Trait` for the remaining methods.

## Sealed Traits

Seal a trait to prevent external implementations, allowing future additions without breaking changes:

```rust
mod private {
    pub trait Sealed {}
}

pub trait MyTrait: private::Sealed {
    fn method(&self);
}

// Only types in this crate can implement MyTrait.
```

## Semver Awareness

- Use `cargo-semver-checks` to verify that changes don't accidentally break the public API.
- `#[non_exhaustive]` on public enums and structs allows adding variants/fields in minor versions without breaking downstream code.
