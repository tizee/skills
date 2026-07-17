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
- Is there one small error enum per subsystem (with `#[from]` translating the layer below at its boundary), rather than one flat app-wide enum mirroring every dependency?
- Is `std::error::Error` derived via `thiserror` rather than hand-rolled?

## Unsafe

- Is every `unsafe` block accompanied by a `// SAFETY:` comment?
- Does every `pub unsafe fn` have a `# Safety` doc section?
- Are unsafe-relevant fields private, contained within a module boundary?
- Does a POD marker impl (`ByteValued`/`Pod`/`FromBytes`) sit on a `#[repr(C)]` type with no padding and no niche types (`bool`/`char`/`enum`/`NonZero`)?
- Is memory a guest/device/other process can mutate accessed through `VolatileSlice`/`read_volatile`, not a plain `&T`?
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
- Zero allocation is not zero copy: does the hot path move the same bytes through memory more than once (write to a buffer, then re-read to consume)?
- Is data materialized into a collection -- including a *reused scratch buffer* -- between a producer and a consumer that iterates it exactly once? Stream it with an `impl Iterator` return instead; materialize only for multi-pass, reordering, or cross-thread handoff.

## Build & Dependencies

- Does CI include `cargo fmt --check`, `cargo clippy`, `cargo test`, `cargo test --doc`?
- Is `cargo audit` or `cargo deny` in the CI pipeline?
- Is shared lint discipline centralized in `[workspace.lints]` rather than duplicated (or forgotten) per crate?
- Is generated/bindgen code quarantined under a `generated/` module so its `#![allow(...)]` does not weaken the workspace lint policy?
- Are Cargo features additive and documented?
- Are new dependencies justified? Check maintenance status and transitive dependency count.

## Numeric Safety

- Are `as` casts used where a value could truncate, wrap, or lose its sign? Should they be `TryFrom`?
- Are `cast_possible_truncation` / `cast_possible_wrap` / `cast_sign_loss` clippy lints enabled at the workspace level?
- Where `#[allow(clippy::cast_*)]` suppresses a cast lint, is there a justification comment proving the cast is safe?
- Is platform-dependent narrowing (e.g. `u64` -> `usize`) gated behind a `cfg(target_pointer_width)` helper rather than scattered `as`?
- Is intentional wraparound expressed with `Wrapping<T>` / `wrapping_*` rather than a bare arithmetic op that hides overflow intent?

## Type Safety

- Are there stringly-typed APIs where an enum would be safer?
- Are boolean parameters unreadable at call sites? (Consider enums or builder.)
- Are newtypes used for domain-specific quantities (e.g., `Meters` vs raw `f64`)?
- Is `Deref` used only for smart pointers, not for simulating inheritance?
- Could phantom types or typestate encode invalid state transitions at compile time?

## Testing

- Do unit tests exist for core logic? Are edge cases covered?
- Is property-based testing (proptest) used for invariant-heavy code?
- Is `cargo fuzz` set up for parsers or code handling untrusted input?
- Is Miri in CI for crates with `unsafe` blocks?
- For code parsing untrusted input or implementing a protocol spec, would a Kani proof (`#[kani::proof]`, contracts) give stronger evidence than sampled tests?
- Do integration tests use only the public API?

## Documentation

- Do doc examples use `?` instead of `unwrap()`?
- Is `#![deny(missing_docs)]` enabled for libraries?
- Are crate-level docs present with a usage example?
- Do `// SAFETY:` comments explain why, not just what?
- Are sealed traits and `#[non_exhaustive]` used where future additions are expected?
