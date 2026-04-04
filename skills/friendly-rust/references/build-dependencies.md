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
