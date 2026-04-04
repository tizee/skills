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
- **Map errors at boundaries instead of forwarding.** A `#[from]` on every dependency error creates a 1:1 mirror of your dependency graph in your error type. Instead, translate at module boundaries into domain-meaningful kinds.
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
