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

## When to Reach for These Patterns

| Problem | Pattern |
| --- | --- |
| Mixing up units or IDs of the same primitive type | Newtype |
| Invalid state transitions at runtime | Typestate (phantom types) |
| Fixed-size stack buffers | Const generics |
| Many optional config parameters | Builder |
| Required fields in builders | Builder + typestate |
| Public enum that may grow | `#[non_exhaustive]` |
| One type per trait impl | Associated type |
| Multiple impls for different types | Generic parameter |
