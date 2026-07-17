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

## First Principles: Memory Traffic Is the Cost

Every byte moved through the memory hierarchy costs bandwidth and energy,
whether or not an allocator was involved. Reason about hot paths in terms of
**how many times the same data crosses memory**, not just how many times
`malloc` runs:

- **Zero allocation is not zero copy.** A reused scratch buffer (`Vec` field,
  `clear()`-not-drop, capacity retained) eliminates malloc/free churn but
  still writes every element out to memory and reads it back in a second
  pass. On a hot path producing thousands of small items per iteration, that
  write-then-reread is two full trips through L1/L2 -- and it evicts the
  producer's still-warm data on the way.
- **Count passes over the data, not allocations.** The question is "how many
  times does each element transit memory between its producer and its final
  sink?" One pass is the floor; every extra materialization adds a round
  trip.
- **If the consumer is single-pass, stream.** When the only consumer of a
  collection iterates it exactly once, front to back, the collection is pure
  overhead: replace the `Vec` handoff with an `impl Iterator` return and let
  each element flow producer → transform → sink while it is still in
  registers. RPIT + `flat_map`/`filter_map` monomorphize to the same machine
  code as a hand-written nested loop.
- **Materialize only for multi-pass or reordering needs.** Sorting, binary
  search, random access, retry/replay, or handing data across a thread
  boundary genuinely require an owned collection. Single forward consumption
  never does.

### Anti-Pattern: Materializing Between Producer and Single-Pass Consumer

```rust
// "Optimized": the scratch Vec is reused across frames, zero allocation in
// steady state -- yet every changed cell is written to the Vec and read
// back, doubling memory traffic on the hot path.
fn end_frame(&mut self) -> String {
    self.scratch.clear();
    diff_into(&self.prev, &self.curr, &mut self.scratch); // pass 1: write all
    serialize(&self.scratch)                              // pass 2: read all
}
```

### Positive Pattern: Stream With `impl Iterator`

```rust
// Each changed cell flows straight from the diff into the serializer while
// still in registers. No scratch state, no second pass. Measured ~6% faster
// on a damage-heavy frame diff than the reused-Vec version above.
fn diff_iter<'a>(prev: &'a Grid, curr: &'a Grid) -> impl Iterator<Item = Update> + 'a {
    (0..curr.rows()).flat_map(move |y| {
        row_span(prev, curr, y).filter_map(move |x| changed_cell(prev, curr, x, y))
    })
}

fn end_frame(&mut self) -> String {
    serialize(diff_iter(&self.prev, &self.curr)) // single pass
}
```

The consumer takes `impl Iterator<Item = T>` instead of `&[T]`; a test that
wants the materialized form calls `.collect()` at its own edge.

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
