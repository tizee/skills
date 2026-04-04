---
urls:
  - https://doc.rust-lang.org/book/ch11-00-testing.html
  - https://docs.rs/proptest/latest/proptest/
  - https://docs.rs/mockall/latest/mockall/
  - https://github.com/rust-fuzz/cargo-fuzz
  - https://github.com/rust-lang/miri
---

# Testing

## Goals

- Catch bugs before they reach production through layered testing strategies.
- Use Rust's type system and tooling to make tests precise and maintainable.
- Validate unsafe code with specialized tools (Miri, fuzzing), not just unit tests.

## Unit Tests

Place unit tests in a `#[cfg(test)]` module inside the same file. Tests can access private items via `use super::*`, which is useful for testing implementation details when the public API alone isn't sufficient.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_valid_port() {
        assert_eq!(parse_port("8080").unwrap(), 8080);
    }

    #[test]
    fn parse_invalid_port() {
        assert!(parse_port("not_a_number").is_err());
    }
}
```

Use `assert_eq!` and `assert_ne!` over plain `assert!` -- they print both values on failure, making diagnosis faster.

## Integration Tests

Integration tests live in `tests/` and can only access the public API:

```
tests/
  common/
    mod.rs          # shared test utilities and fixtures
  api_test.rs       # API integration tests
  cli_test.rs       # CLI integration tests
```

Use shared fixtures for setup/teardown. Implement `Drop` on test context structs for automatic cleanup:

```rust
pub struct TestApp { /* state */ }

impl TestApp {
    pub fn new() -> Self { /* setup */ }
}

impl Drop for TestApp {
    fn drop(&mut self) { /* teardown */ }
}
```

## Documentation Tests

Doc examples are compiled and run by `cargo test`. Use them to verify that examples in documentation actually work:

- Default code blocks (` ```rust `) compile and execute.
- `no_run` compiles without executing -- for examples that need network/filesystem.
- `should_panic` expects a panic, useful for documenting error conditions.
- `ignore` skips entirely.

Always use `?` in doc examples, not `unwrap()`. Users copy-paste from docs.

## Property-Based Testing with proptest

When correctness depends on invariants across many inputs, proptest generates random inputs and shrinks failures to minimal cases:

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn encode_decode_roundtrip(input: Vec<u8>) {
        let encoded = encode(&input);
        let decoded = decode(&encoded).unwrap();
        prop_assert_eq!(input, decoded);
    }
}
```

Particularly valuable for serialization, parsing, and data structure operations where edge cases are hard to enumerate manually.

## Mocking with mockall

For testing code that depends on traits (database, HTTP, filesystem), generate mocks:

```rust
use mockall::automock;

#[automock]
trait Storage {
    fn get(&self, key: &str) -> Option<String>;
}

#[test]
fn cache_returns_stored_value() {
    let mut mock = MockStorage::new();
    mock.expect_get()
        .with(eq("key"))
        .returning(|_| Some("value".into()));

    let cache = Cache::new(mock);
    assert_eq!(cache.lookup("key"), Some("value".into()));
}
```

For simple cases, a manual fake implementing the trait is lighter than mockall.

## Fuzzing

Fuzzing generates random inputs to find crashes and edge cases in parsers, protocol implementations, and any code handling untrusted input:

```bash
cargo install cargo-fuzz
cargo fuzz init
cargo fuzz run my_target
```

Fuzzing is especially valuable for code with `unsafe` blocks, where a crash may indicate undefined behavior.

## Miri

Miri interprets Rust's MIR to detect undefined behavior: use-after-free, data races, stacked borrows violations. Essential for validating `unsafe` code:

```bash
cargo +nightly miri test
```

Miri runs significantly slower than native execution, so it's typically used on targeted test suites rather than the full suite. Add it to CI for any crate containing `unsafe`.

## Coverage

`cargo-llvm-cov` and `cargo-tarpaulin` generate coverage reports. Coverage guides testing effort but is not a quality metric -- assertion quality matters more than line counting. A test that executes every line but asserts nothing is worse than no test.

```bash
cargo install cargo-llvm-cov
cargo llvm-cov --html
```
