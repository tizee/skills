---
urls:
  - https://go.dev/blog/pprof
  - https://go.dev/doc/diagnostics
  - https://go.dev/blog/pgo
  - https://pkg.go.dev/runtime/pprof
  - https://pkg.go.dev/log/slog
---

# Performance & Observability

Two linked disciplines: measuring before you change anything, and leaving enough signal in production to diagnose what you cannot reproduce. Go's tooling makes both cheap, so guessing is never justified.

## Measure first -- the optimization order

Go's compiler and garbage collector are good; intuition about what is slow is frequently wrong. Follow a strict order and stop as soon as the numbers are acceptable:

1. **Benchmark** the hot path (`go test -bench`) so you have a baseline number to beat.
2. **Profile** to find where the time and allocations actually go (`pprof`).
3. **Fix the data structure or algorithm** -- this is where most real wins come from.
4. **Only then** consider compiler-level help (PGO, inlining hints).

A change without a before/after benchmark is not an optimization; it is a guess that happens to compile.

## pprof and trace

Every Go program can expose rich profiles with no extra dependencies.

```go
import _ "net/http/pprof" // registers /debug/pprof/* on the default mux

// Expose on a private/admin port, never the public one:
go func() { log.Println(http.ListenAndServe("localhost:6060", nil)) }()
```

Available profiles and what each answers:

| Profile | Question it answers |
| --- | --- |
| CPU | Where is wall-clock CPU time spent? |
| heap | What is allocating, and what is retained? |
| goroutine | How many goroutines exist, and where are they stuck? (leak hunting) |
| block | What is blocking on synchronization? |
| mutex | Where is lock contention? |
| threadcreate | Why are OS threads being created? |

For scheduling, syscalls, GC pauses, and task-level annotation, `runtime/trace` gives a timeline view that `pprof` cannot. Collect a profile in a benchmark with `go test -cpuprofile cpu.out -memprofile mem.out`, then explore with `go tool pprof`.

## Profile-Guided Optimization (PGO)

PGO (stable since Go 1.21) feeds a production CPU profile back into the compiler so it inlines and optimizes the hot paths your workload actually exercises. The official typical win is **2-7% CPU improvement** for representative workloads. Drop a `default.pgo` file next to `main` and the build picks it up automatically.

PGO is not for every project, but it is worth a release experiment for high-QPS services, latency-sensitive gateways, rule engines, and serialization-heavy hot paths -- anywhere a few percent of CPU is real money or real tail latency.

## The four common performance anti-patterns

Most "Go is slow here" reports trace back to one of these, and the fix is usually choosing the right data structure, not going lower-level:

1. **Using a `map` where a `slice` would do.** Maps have hashing and pointer-chasing overhead; if you index by small dense integers or iterate in order, a slice is faster and allocates less. (The classic Go profiling blog post gets most of its win exactly this way.)
2. **Allocating in the hot path.** Repeated `+` string concatenation, per-call slice/map allocation, and boxing into `interface{}` create GC pressure. Reuse buffers (`strings.Builder`, `bytes.Buffer`, `sync.Pool`) and preallocate slices with a known capacity (`make([]T, 0, n)`).
3. **Mistaking lock contention for a CPU problem.** A profile showing high CPU may actually be threads spinning on a contended mutex. Check the mutex/block profiles before optimizing the wrong thing; reduce lock scope or shard the lock.
4. **Going concurrent before going correct.** Adding goroutines to a problem that is actually allocation- or algorithm-bound just adds scheduling overhead and bugs. Profile first.

## Observability: the four signals

A service that cannot be diagnosed in production is unfinished. Diagnosis speed is decided *before* launch, by whether these four surfaces exist:

1. **Structured logs** -- `log/slog` with key-value fields, not formatted strings. Queryable, filterable, machine-parseable.
2. **Metrics** -- request rate, error rate, latency (the RED method), plus queue depth and runtime stats (goroutine count, GC pauses, heap). Prometheus-style export is the ecosystem default.
3. **Health probes** -- distinguish *liveness* (the process is alive) from *readiness* (it can serve traffic). Orchestrators need both to route and restart correctly.
4. **Diagnostic endpoints** -- `pprof` and `trace` behind an admin port or authenticated path, so you can profile a misbehaving instance without redeploying.

## Anti-Pattern

Hot-path string concatenation that allocates on every iteration:

```go
func Encode(items []string) string {
    s := ""
    for _, it := range items {
        s += it + "," // each += allocates a new string -> O(n^2) garbage
    }
    return s
}
```

## Positive Pattern

A reused builder, preallocated where the size is known:

```go
func Encode(items []string) string {
    var b strings.Builder
    b.Grow(len(items) * 8) // hint capacity to avoid regrowth
    for i, it := range items {
        if i > 0 {
            b.WriteByte(',')
        }
        b.WriteString(it)
    }
    return b.String()
}
```

And for fan-out, bound concurrency with a known exit instead of unbounded `go`:

```go
func Fanout(ctx context.Context, tasks <-chan Task, n int) error {
    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(n) // bounded; no goroutine explosion
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case t, ok := <-tasks:
            if !ok {
                return g.Wait()
            }
            g.Go(func() error { return handle(ctx, t) })
        }
    }
}
```
