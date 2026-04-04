---
urls:
  - https://nnethercote.github.io/perf-book/
  - https://bheisler.github.io/criterion.rs/book/
  - https://doc.rust-lang.org/book/ch13-04-performance.html
  - https://www.databend.com/blog/category-engineering/profile-guided-optimization/
---

# Performance & Profiling

## Goals

- Optimize based on measurement, not folklore.
- Provide benchmarking infrastructure so performance regressions are caught early.
- Use Rust's zero-cost abstractions with confidence, but verify when it matters.

## Guidance

- **Measure first.** Rust's iterators, closures, and trait dispatch often compile to code equivalent to hand-written loops. But "zero-cost" means "no cost beyond what you asked for," not "always fast." Profile before rewriting.
- **Use platform profilers.** `perf` on Linux, Instruments on macOS, `cargo flamegraph` for quick flamecharts. The Rust Performance Book covers tool setup in detail.
- **Add bench targets for performance-sensitive code.** A crate with performance claims but no benchmarks is making untestable promises.
- **Prefer Criterion on stable.** The built-in `#[bench]` requires nightly. Criterion provides statistical benchmarking, regression detection, and HTML reports on stable Rust.
- **Profile allocations.** DHAT, jemalloc profiling, or `#[global_allocator]` with a counting allocator can reveal allocation hot spots that iterators and zero-copy patterns can eliminate.
- **Watch for large enum variants.** When one variant is much larger than others, the entire enum pays the size cost. Clippy's `large_enum_variant` lint catches this; boxing the large variant is the usual fix, but measure the tradeoff (one extra indirection vs. smaller moves).

## Anti-Pattern: Optimizing Without Measuring

```rust
// "Surely manual indexing is faster than iterators"
fn sum_manual(data: &[i32]) -> i32 {
    let mut total = 0;
    let mut i = 0;
    while i < data.len() {
        total += data[i]; // also loses bounds-check elision hints
        i += 1;
    }
    total
}
```

## Positive Pattern: Idiomatic and Measurably Equivalent

```rust
fn sum_idiomatic(data: &[i32]) -> i32 {
    data.iter().sum()
}
// Benchmark both; the iterator version is typically identical or faster
// because LLVM can vectorize it more reliably.
```

## Large Enum Variant

```rust
// Bad: entire enum is 8000+ bytes.
enum Msg {
    Ping,
    Payload([u8; 8000]),
}

// Fix: box the large variant. Measure to confirm this is worthwhile.
enum Msg {
    Ping,
    Payload(Box<[u8; 8000]>),
}
```

## Minimal PGO Workflow

Profile-Guided Optimization uses runtime profiling data to guide compiler optimizations. Worth it for CPU-bound release binaries.

1. Install LLVM tools: `rustup component add llvm-tools-preview`
2. Clean old data: `rm -rf /tmp/pgo-data`
3. Build instrumented binary:
   ```bash
   RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" cargo build --release
   ```
4. Run a representative workload to generate `.profraw` files.
5. Merge profiles and rebuild:
   ```bash
   llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data
   RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata" cargo build --release
   ```

PGO quality depends entirely on the fidelity of the profiling workload. Use realistic inputs.

## Criterion Quick Start

```rust
// benches/my_benchmark.rs
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_sum(c: &mut Criterion) {
    let data: Vec<i32> = (0..10_000).collect();
    c.bench_function("sum_idiomatic", |b| {
        b.iter(|| data.iter().sum::<i32>())
    });
}

criterion_group!(benches, bench_sum);
criterion_main!(benches);
```

## Anti-Pattern: Eager Collection When Lazy Suffices

```rust
// Forces allocation of an intermediate Vec.
let names: Vec<String> = users.iter().map(|u| u.name.clone()).collect();
let filtered: Vec<&String> = names.iter().filter(|n| n.starts_with("A")).collect();
```

Prefer chaining iterators lazily -- each element flows through all operations without intermediate allocation:

```rust
let filtered: Vec<&str> = users.iter()
    .map(|u| u.name.as_str())
    .filter(|n| n.starts_with("A"))
    .collect();
```

## Semantic Methods Over Index Arithmetic

Prefer `first()`, `last()`, `split_first()` over `get(0)`, `get(len - 1)`. Semantic methods communicate intent and handle empty cases correctly.

## Flamegraph Quick Start

```bash
cargo install flamegraph
cargo flamegraph --bin myapp
# Opens an SVG flamegraph showing hot paths.
```

For deterministic benchmarking (cache-aware), `iai` uses Cachegrind under the hood and produces measurements immune to system load variation.

## Fuzzing for Parsers and Protocol Code

Performance-sensitive code that handles untrusted input should also be fuzzed:

```bash
cargo install cargo-fuzz
cargo fuzz init
cargo fuzz run my_target
```

Fuzzing finds both crashes and performance pathologies (inputs that cause quadratic behavior).
