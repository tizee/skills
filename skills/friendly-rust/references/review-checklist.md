---
urls:
  - https://rust-lang.github.io/api-guidelines/
  - https://doc.rust-lang.org/nomicon/
  - https://std-dev-guide.rust-lang.org/policy/safety-comments.html
---

# Review Checklist

Quick-reference questions for reviewing Rust code. Not every question applies to every review -- pick the ones relevant to the change.

## Correctness & Safety

- Does the code work with the borrow checker, or does it clone/unsafe its way around ownership issues?
- Are there `unwrap()` calls in library code that should be `?` or `expect()` with a message?
- Does `Result<_, ()>` appear in any public API?
- Do error types implement `Error + Send + Sync + 'static`?
- Are error variants caller-actionable (retry, not-found, invalid) rather than dependency-origin (db, http)?

## Unsafe

- Is every `unsafe` block accompanied by a `// SAFETY:` comment?
- Does every `pub unsafe fn` have a `# Safety` doc section?
- Are unsafe-relevant fields private, contained within a module boundary?
- Could a safe alternative replace the unsafe operation?

## Ownership & Borrowing

- Do function signatures reflect actual ownership needs (owned vs borrowed)?
- Are there hidden `.clone()` / `.to_string()` inside functions that take references?
- Is `Cow` used only where borrowed-or-owned flexibility is genuinely needed?

## Async & Concurrency

- Is there blocking I/O or heavy computation on an async executor thread?
- Are locks (`MutexGuard`) held across `.await` points?
- Do spawned tasks meet `Send + 'static` bounds?
- Is `.abort()` called on `spawn_blocking` handles? (It won't stop a running task.)
- Do custom `Future` impls update stored wakers on every poll?

## API Surface

- Are public items documented with `///` doc comments?
- Do functions returning `Result` have `# Errors` doc sections?
- Do functions that can panic have `# Panics` doc sections?
- Are struct fields private by default?
- Does the type implement expected standard traits (`Debug`, `Clone`, `PartialEq`, `From`, etc.)?
- Is visibility `pub(crate)` by default, promoted to `pub` only when needed?

## Performance

- Are performance claims backed by benchmarks?
- Is there premature optimization without profiling evidence?
- Are there large enum variants that inflate the enum size? (Clippy: `large_enum_variant`)

## Build & Dependencies

- Does CI include `cargo fmt --check`, `cargo clippy`, `cargo test`, `cargo test --doc`?
- Is `cargo audit` or `cargo deny` in the CI pipeline?
- Are Cargo features additive and documented?
- Are new dependencies justified? Check maintenance status and transitive dependency count.

## Documentation

- Do doc examples use `?` instead of `unwrap()`?
- Is `#![deny(missing_docs)]` enabled for libraries?
- Are crate-level docs present with a usage example?
