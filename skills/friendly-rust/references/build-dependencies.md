---
urls:
  - https://doc.rust-lang.org/cargo/
  - https://doc.rust-lang.org/cargo/reference/features.html
  - https://doc.rust-lang.org/cargo/reference/workspaces.html
  - https://rustsec.org/
  - https://www.databend.com/blog/category-product/2023-04-20-optimizing-compilation-for-databend/
---

# Build & Dependencies

## Goals

- Keep edit-build-test latency low for day-to-day development.
- Make Cargo features intentional and documented.
- Catch dependency vulnerabilities before they reach production.

## Compile Time

- **Measure before tuning.** Use `cargo build --timings` to visualize where compile time is spent. The HTML Gantt chart shows crate-level parallelism bottlenecks.
- **Use a fast linker.** `mold` on Linux, `lld` on Linux/Windows. On macOS, set `split-debuginfo = "unpacked"` to skip `dsymutil`.
  ```toml
  # .cargo/config.toml (Linux)
  [target.x86_64-unknown-linux-gnu]
  linker = "clang"
  rustflags = ["-C", "link-arg=-fuse-ld=mold"]
  ```
- **Remove unused dependencies.** `cargo-machete` is fast (heuristic); `cargo-udeps` is accurate (but slower, requires nightly).
- **Split oversized crates.** Large crates serialize compilation. Extracting internal modules into workspace members improves parallelism.
- **`codegen-units = 1` for release, higher for slow crates.** A single codegen unit improves optimization but slows codegen. Override per-crate if needed:
  ```toml
  [profile.release]
  codegen-units = 1

  [profile.release.package.slow-crate]
  codegen-units = 4
  ```
- **Keep toolchains current.** Upstream improvements regularly reduce compile times and improve diagnostics.

## Cargo Features

- **Features should be additive.** Enabling a feature should add capability, never remove it. A feature that disables functionality is a maintenance trap.
- **Document features.** List what each feature enables in `Cargo.toml` comments or crate-level docs.
- **Avoid fragile default-feature sets.** If `default = ["a", "b"]` and `a` assumes `b` is present, you have an implicit dependency that breaks when a consumer uses `default-features = false`.

## Workspace Hygiene

- **Use workspace-level dependency inheritance.** `[workspace.dependencies]` avoids version drift across members.
  ```toml
  # root Cargo.toml
  [workspace.dependencies]
  serde = { version = "1", features = ["derive"] }

  # member Cargo.toml
  [dependencies]
  serde = { workspace = true }
  ```
- **Centralize lint policy with `[workspace.lints]`.** Encode your team's discipline once at the root so every member inherits it, turning "reviewers should check X" into a compiler warning. This is how a large codebase enforces safety norms uniformly instead of hoping each author remembers.
  ```toml
  # root Cargo.toml
  [workspace.lints.rust]
  missing_debug_implementations = "warn"

  [workspace.lints.clippy]
  undocumented_unsafe_blocks = "warn"  # every unsafe block must justify itself
  cast_possible_truncation = "warn"    # every narrowing cast is suspect
  error_impl_error = "warn"            # nudge toward thiserror over hand-rolled
  or_fun_call = "warn"                 # catch eager allocation in `unwrap_or`

  # member Cargo.toml
  [lints]
  workspace = true
  ```
  Prefer `warn` + a `-D warnings` gate in CI over crate-level `#![deny(...)]`: `warn` keeps local iteration unblocked while CI still fails the build.
- **Quarantine generated code.** Put bindgen / prost / build-script output under a `generated/` module and blanket-`#![allow(...)]` its lints, so machine noise never dilutes the strict lint policy applied to hand-written code.
  ```rust
  // src/.../generated/mod.rs
  #![allow(non_camel_case_types, dead_code, clippy::all)]
  ```
- **Choose the panic strategy deliberately.** For security-critical or FFI-heavy binaries, `panic = "abort"` removes unwinding — smaller code, no unwind across an FFI or trust boundary, and a panic becomes a clean crash instead of an ambiguous half-unwound state.
  ```toml
  [profile.release]
  panic = "abort"
  ```

> Source: adapted from firecracker — `[workspace.lints]` enforcing
> `undocumented_unsafe_blocks`, `cast_*`, `error_impl_error`, `missing_debug_implementations`;
> bindgen output isolated under `generated/`; `panic = "abort"` on all profiles.
- **Consolidate integration tests.** A `tests/it/` structure with a single test binary avoids compiling many small binaries.
- **Share CI caches wisely.** `sccache` works well for clean CI builds. Incremental compilation often hurts CI due to extra I/O overhead.

## Security Audits

- **Run `cargo audit` in CI.** Checks `Cargo.lock` against the RustSec advisory database. Catches known vulnerabilities in dependencies.
- **Use `cargo deny` for broader policy.** Checks licenses, banned crates, duplicate versions, and advisories in one tool.
  ```bash
  # CI step
  cargo install cargo-deny
  cargo deny check
  ```
- **Review new dependencies before adding.** Check maintenance status, download counts, and whether the crate pulls in unexpected transitive dependencies.

## CI Pipeline Essentials

A minimal Rust CI should include:

```yaml
# Pseudocode, adapt to your CI system
steps:
  - cargo fmt --check          # formatting consistency
  - cargo clippy --all-targets --all-features -- -D warnings  # lint hygiene
  - cargo test                 # correctness
  - cargo test --doc           # doc examples compile and pass
  - cargo deny check           # security and license policy
```
