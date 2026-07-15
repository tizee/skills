---
urls:
  - https://rust-lang.github.io/api-guidelines/interoperability.html
  - https://fast.github.io/blog/stop-forwarding-errors-start-designing-them/
  - https://doc.rust-lang.org/std/error/trait.Error.html
---

# Error Design

## Goals

- Make error types express domain boundaries and caller responsibility.
- Control error visibility to avoid leaking internal details.
- Preserve diagnostic context for debugging and tracing.

## Guidance

- **Design error semantics before propagation.** Decide what callers can do about each failure (retry, report, skip) and shape error kinds around those actions, not around which dependency failed.
- **Never use `()` as an error type in public APIs.** It discards all diagnostic information and breaks composition with `?`.
- **Error types should implement `Error + Send + Sync + 'static`.** This ensures errors work across threads, with `?`, and with downcasting. If your error type doesn't meet these bounds, it will surprise consumers in async or threaded contexts.
- **Map errors at boundaries, don't blindly forward.** The failure mode to avoid is one flat, app-wide error enum that `#[from]`-mirrors your entire dependency graph, so the caller sees `Db`/`Http` and cannot tell "not found" from "connection lost". `#[from]` itself is fine — even excellent — when each *subsystem* owns a small error enum and `#[from]` absorbs only the layer directly beneath it at a real module boundary (see the middle-path section below).
- **Document error conditions.** Public functions that return `Result` should have an `# Errors` section in rustdoc describing when and why each error variant occurs.
- **Use `?` in examples, not `unwrap`.** Users copy-paste doc examples. Model good error handling.

## Anti-Pattern: Origin-Based Error Enums

Mirroring dependencies and forwarding without context:

```rust
#[derive(Debug, thiserror::Error)]
pub enum ServiceError {
    #[error("db error: {0}")]
    Db(#[from] sqlx::Error),
    #[error("http error: {0}")]
    Http(#[from] reqwest::Error),
}

pub fn handle(req: Request) -> Result<Response, ServiceError> {
    let user = db_get(req.user_id)?; // caller can't distinguish "not found" from "connection lost"
    let data = fetch_api(user.api_key)?;
    Ok(render(data)?)
}
```

The caller sees `ServiceError::Db` but has no idea whether to retry, show 404, or alert ops.

## Positive Pattern: Actionable Error Kinds

Error kinds based on what the caller should do:

```rust
#[derive(Debug, Clone, Copy)]
pub enum ErrorKind {
    NotFound,
    RateLimited,
    InvalidInput,
    Temporary,
}

#[derive(Debug)]
pub struct AppError {
    kind: ErrorKind,
    message: String,
}

impl AppError {
    pub fn new(kind: ErrorKind, msg: impl Into<String>) -> Self {
        Self { kind, message: msg.into() }
    }

    pub fn kind(&self) -> ErrorKind {
        self.kind
    }
}

impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for AppError {}

pub fn fetch_user(id: &str) -> Result<User, AppError> {
    let raw = call_upstream(id)
        .map_err(|_| AppError::new(ErrorKind::Temporary, format!("fetch_user {id}")))?;
    parse_user(&raw)
        .map_err(|_| AppError::new(ErrorKind::NotFound, format!("user {id}")))
}
```

## The `#[from]` Middle Path: Per-Subsystem Boundary Translation

The origin-based anti-pattern above is one *global* enum mirroring every dependency. The scalable alternative is not "never use `#[from]`" but **one small error enum per subsystem**, where `#[from]` translates the immediately-lower layer as it crosses that subsystem's boundary. Each layer's error is only as wide as its own module, so a variant like `QueueError` inside `NetError` names a real architectural seam, not a leaked dependency.

`displaydoc` keeps this terse by turning the doc comment into the `Display` string, so the variant and its message stay in one place:

```rust
#[derive(Debug, thiserror::Error, displaydoc::Display)]
pub enum NetError {
    /// Open tap device failed: {0}
    TapOpen(TapError),
    /// Writing to guest memory failed: {0}
    GuestMemory(#[from] VolatileMemoryError),  // absorbs the layer below
    /// Virtio queue error: {0}
    Queue(#[from] QueueError),                 // absorbs a sibling subsystem
    /// MTU {0} is out of range [68, 65535]
    InvalidMtu(u16),                           // this layer's own domain error
}
```

Two refinements worth copying:

- **Struct errors for a single rich failure.** When one variant needs several named fields, a `#[error("...")]` struct reads better than an enum with one populated case:
  ```rust
  #[derive(Debug, thiserror::Error, PartialEq, Eq)]
  #[error("available descriptors {reported} exceed queue size {size}")]
  pub struct InvalidAvailIdx { size: u16, reported: u16 }
  ```
- **Don't hand-roll `impl std::error::Error`.** Let `thiserror` derive it; a `error_impl_error` lint can flag manual impls so the whole workspace stays consistent.

> Source: adapted from firecracker — per-subsystem `thiserror` + `displaydoc`
> enums (`NetError`, `QueueError`) using `#[from]` as boundary translation, the
> `InvalidAvailIdx` struct error, and the `error_impl_error` workspace lint.

## Anti-Pattern: Panicking in Library Code

```rust
// Library function that panics on normal error paths.
pub fn parse_port(s: &str) -> u16 {
    s.parse::<u16>().unwrap()
}
```

## Positive Pattern: Propagate Meaningful Errors

```rust
pub fn parse_port(s: &str) -> Result<u16, std::num::ParseIntError> {
    s.parse::<u16>()
}
```

Reserve `unwrap`/`expect` for cases where you can prove the value is always `Some`/`Ok`, and add a comment explaining why. In library code, prefer `?` unconditionally.
