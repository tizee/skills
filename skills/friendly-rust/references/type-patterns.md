---
urls:
  - https://doc.rust-lang.org/book/ch19-04-advanced-types.html
  - https://doc.rust-lang.org/reference/items/type-aliases.html
  - https://github.com/skyzh/type-exercise-in-rust
---

# Type Patterns

## Goals

- Make invalid states unrepresentable through the type system.
- Use newtypes, phantom types, and const generics to encode domain rules at compile time.
- Reduce runtime checks by moving validation to type construction.

## Newtype Pattern

Wrap primitive types to create distinct domain types with zero runtime cost:

```rust
struct Meters(f64);
struct Seconds(f64);

// These are different types -- you can't accidentally mix them.
fn speed(distance: Meters, time: Seconds) -> f64 {
    distance.0 / time.0
}

// speed(Seconds(5.0), Meters(100.0)) // compile error: wrong order
```

Implement `From`/`Into` for conversions, and standard traits (`Debug`, `Display`, `PartialEq`, `Clone`, `Copy`) as needed. Newtypes are the simplest way to prevent unit confusion, ID mixing, and stringly-typed APIs.

## Typestate Pattern with Phantom Types

Encode state machines in types so invalid transitions don't compile:

```rust
use std::marker::PhantomData;

struct Disconnected;
struct Connected;

struct Connection<State> {
    addr: String,
    _state: PhantomData<State>,
}

impl Connection<Disconnected> {
    pub fn new(addr: String) -> Self {
        Connection { addr, _state: PhantomData }
    }

    pub fn connect(self) -> Connection<Connected> {
        // ... establish connection ...
        Connection { addr: self.addr, _state: PhantomData }
    }
}

impl Connection<Connected> {
    pub fn query(&self, sql: &str) -> Vec<Row> {
        // Only callable when connected.
        todo!()
    }

    pub fn disconnect(self) -> Connection<Disconnected> {
        Connection { addr: self.addr, _state: PhantomData }
    }
}

// conn.query("SELECT 1"); // compile error: Connection<Disconnected> has no method `query`
```

The state transition consumes `self` and returns a new type, so you can't use a connection after disconnecting.

## Const Generics

Encode numeric constraints in types:

```rust
struct ArrayVec<T, const N: usize> {
    data: [Option<T>; N],
    len: usize,
}

impl<T, const N: usize> ArrayVec<T, N> {
    pub fn push(&mut self, item: T) -> Result<(), T> {
        if self.len >= N {
            return Err(item);
        }
        self.data[self.len] = Some(item);
        self.len += 1;
        Ok(())
    }
}
```

Useful for stack-allocated buffers with compile-time size guarantees.

## Builder Pattern with Type Safety

Combine builders with typestate to enforce required fields at compile time:

```rust
struct NoHost;
struct HasHost(String);

struct ServerBuilder<H> {
    host: H,
    port: u16,
}

impl ServerBuilder<NoHost> {
    pub fn new() -> Self {
        ServerBuilder { host: NoHost, port: 8080 }
    }

    pub fn host(self, host: impl Into<String>) -> ServerBuilder<HasHost> {
        ServerBuilder { host: HasHost(host.into()), port: self.port }
    }
}

impl ServerBuilder<HasHost> {
    pub fn port(mut self, port: u16) -> Self {
        self.port = port;
        self
    }

    pub fn build(self) -> Server {
        Server { host: self.host.0, port: self.port }
    }
}

// ServerBuilder::new().port(3000).build(); // compile error: no `build` on NoHost
// ServerBuilder::new().host("localhost").build(); // works
```

## Associated Types vs Generic Parameters

Use **associated types** when there is one natural type per implementation:

```rust
trait Iterator {
    type Item;  // each iterator yields one kind of item
    fn next(&mut self) -> Option<Self::Item>;
}
```

Use **generic parameters** when multiple implementations for different types are needed:

```rust
trait Convert<T> {
    fn convert(&self) -> T;
}
// A type can implement Convert<String> AND Convert<i32>.
```

## #[non_exhaustive] for Future-Proofing

Mark public enums and structs with `#[non_exhaustive]` to allow adding variants/fields in minor versions:

```rust
#[non_exhaustive]
pub enum Error {
    NotFound,
    PermissionDenied,
    // Adding a new variant in v1.2 won't break downstream code.
}
```

Downstream code must include a wildcard arm in match, so new variants don't cause compile errors.

## Numeric Conversions: `try_from` over `as`

The `as` operator silently truncates, wraps, or changes sign. Where a value crosses a width or trust boundary (untrusted input, syscall returns, buffer sizes, offsets), a silent truncation is a correctness or security bug, not a rounding detail. Treat every `as` cast as suspect and prefer fallible `TryFrom`.

Enforce this project-wide with clippy lints instead of relying on review vigilance:

```toml
# workspace Cargo.toml
[workspace.lints.clippy]
cast_possible_truncation = "warn"  # u64 -> u32 may drop high bits
cast_possible_wrap = "warn"        # u32 -> i32 may become negative
cast_sign_loss = "warn"            # i32 -> u32 may reinterpret the sign bit
```

With the lints on, narrowing conversions must go through `TryFrom`, making the overflow path explicit and recoverable:

```rust
// Fails loudly if the length does not fit a u32, instead of silently truncating.
let count = u32::try_from(items.len())?;
let fd = RawFd::try_from(raw_return)?;
```

When a cast is *provably* safe, suppress the lint at the single call site with a justification, never with a blanket crate-level `allow`:

```rust
// A struct's compile-time size is bounded well below u32::MAX.
#[allow(clippy::cast_possible_truncation)]
const REQ_SIZE: u32 = std::mem::size_of::<Request>() as u32;
```

For conversions that are sound only on a specific platform, gate a helper on the target width so the assumption is stated once, centrally, and becomes a compile error elsewhere rather than a silent truncation:

```rust
/// Convert a `u64` to `usize`. Sound only on 64-bit targets; the `cfg` turns the
/// assumption into a compile error on narrower platforms.
#[cfg(target_pointer_width = "64")]
#[inline]
pub const fn u64_to_usize(num: u64) -> usize {
    num as usize
}
```

### Intentional Wraparound: `Wrapping<T>`

When arithmetic *should* wrap (ring-buffer indices, sequence counters), encode it in the type. `Wrapping<u16>` documents the intent and opts out of debug overflow panics, whereas a bare `u16 += 1` leaves the reader unable to tell a designed wrap from an overflow bug.

```rust
pub struct RingCursor {
    next_avail: std::num::Wrapping<u16>, // wraps by protocol design
    next_used: std::num::Wrapping<u16>,
}
```

> Source: adapted from firecracker — `cast_*` workspace lints, the
> `target_pointer_width`-gated `u64_to_usize` helper, and `Wrapping<u16>` virtio
> ring indices.

## When to Reach for These Patterns

| Problem | Pattern |
| --- | --- |
| Silent truncation/wrap across a width or trust boundary | `TryFrom` over `as` |
| Arithmetic that must wrap by design | `Wrapping<T>` |
| Mixing up units or IDs of the same primitive type | Newtype |
| Invalid state transitions at runtime | Typestate (phantom types) |
| Fixed-size stack buffers | Const generics |
| Many optional config parameters | Builder |
| Required fields in builders | Builder + typestate |
| Public enum that may grow | `#[non_exhaustive]` |
| One type per trait impl | Associated type |
| Multiple impls for different types | Generic parameter |
