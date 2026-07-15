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

## Kani: Bounded Model Checking and Proofs

Miri and fuzzing *sample* the input space; Kani *exhausts* a bounded slice of it. Kani translates a harness into a SAT/SMT problem and proves that, for every input the solver can construct, no panic, overflow, or assertion failure occurs. Reach for it on code that parses attacker-controlled input or must conform to a protocol spec, where "we tried a million random cases" is weaker evidence than a proof.

Harnesses live in `#[cfg(kani)]` modules, mirroring `#[cfg(test)]`. `kani::any()` produces a symbolic value standing for *all* values of its type:

```rust
#[cfg(kani)]
mod verification {
    use super::*;

    #[kani::proof]
    #[kani::unwind(0)]
    fn add_used_advances_cursor_exactly_once() {
        let mut queue: Queue = kani::any();      // every reachable queue state
        let index: u16 = kani::any();
        let used = queue.next_used;
        if queue.add_used(index, kani::any()).is_ok() {
            assert_eq!(queue.next_used, used + Wrapping(1));
        } else {
            assert_eq!(queue.next_used, used);   // failure leaves state untouched
            assert!(index >= queue.size);        // and only fails out of bounds
        }
    }
}
```

### Function Contracts

Attach `requires` (preconditions) and `ensures` (postconditions) to a function, then prove the contract holds for all inputs. Verified functions can be *stubbed* by their contract in downstream proofs, keeping each proof tractable:

```rust
#[cfg_attr(kani, kani::requires(x > 0 && y > 0))]
#[cfg_attr(kani, kani::ensures(|&r| r != 0 && x % r == 0 && y % r == 0))]
fn gcd(x: u64, y: u64) -> u64 { /* ... */ }

#[kani::proof_for_contract(gcd)]
fn gcd_contract_harness() { /* kani::any() inputs */ }
```

### Taming Non-Determinism

Real code touches the clock, FFI, or the OS, which Kani cannot model. Stub those out so the proof stays about *your* logic:

```rust
#[kani::proof]
#[kani::stub(std::time::Instant::now, stubs::fixed_instant)]
#[kani::stub_verified(gcd)]   // reuse gcd's proven contract, don't re-explore it
fn verify_token_bucket_new() { /* ... */ }
```

Bound loops with `#[kani::unwind(N)]` and constrain inputs with `kani::any_where(...)` to keep the solver's state space finite. Run harnesses in CI (`cargo kani`) for guest-facing or safety-critical crates — it is the practical rung above Miri on the verification ladder.

> Source: adapted from firecracker — Kani proofs of virtio queue `add_used` /
> notification-suppression (VirtIO spec 2.6.7.2), the `gcd` contract, and the
> `TokenBucket::new` invariant with a stubbed `Instant::now`.

## Coverage

`cargo-llvm-cov` and `cargo-tarpaulin` generate coverage reports. Coverage guides testing effort but is not a quality metric -- assertion quality matters more than line counting. A test that executes every line but asserts nothing is worse than no test.

```bash
cargo install cargo-llvm-cov
cargo llvm-cov --html
```
