---
urls:
  - https://go.dev/blog/pipelines
  - https://go.dev/blog/context
  - https://go.dev/blog/race-detector
  - https://pkg.go.dev/golang.org/x/sync/errgroup
  - https://go.dev/wiki/CodeReviewComments#goroutine-lifetimes
---

# Concurrency

"Don't communicate by sharing memory; share memory by communicating." Go's concurrency is cheap to start and expensive to get wrong. The discipline that keeps it correct: every goroutine has a known owner and a known way to stop, and `context.Context` flows through every call that can block.

## Goroutine lifetimes

The most common concurrency bug in Go is the leaked goroutine -- one that blocks forever on a channel nobody will write to, or runs after the work that spawned it is gone. Before writing `go`, answer two questions: **When does this goroutine exit? Who is waiting for it?** If you cannot answer both, the design is wrong.

```go
// BAD: who stops this? what if the channel never receives? it leaks.
go func() {
    for msg := range ch {
        process(msg)
    }
}()

// GOOD: lifetime tied to context; caller can stop it; WaitGroup tracks it.
var wg sync.WaitGroup
wg.Add(1)
go func() {
    defer wg.Done()
    for {
        select {
        case <-ctx.Done():
            return
        case msg, ok := <-ch:
            if !ok {
                return
            }
            process(msg)
        }
    }
}()
// later, at shutdown: cancel(); wg.Wait()
```

## context.Context propagation

`context.Context` is the standard mechanism for cancellation, deadlines, and request-scoped values. Rules the whole ecosystem follows:

- Pass `ctx` as the **first parameter**, named `ctx`, never store it in a struct field.
- Derive child contexts with `context.WithTimeout` / `context.WithCancel` and **always** `defer cancel()` -- failing to cancel leaks the timer and the context.
- Thread `ctx` into every blocking call: DB queries, HTTP requests, channel sends in long-running loops.
- Use `context.Context` for cancellation, not for passing optional parameters. `ctx.Value` is for request-scoped data (trace IDs, auth), not a general-purpose bag.

```go
func (s *Store) Fetch(ctx context.Context, id int64) (*Row, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()
    return s.db.QueryRow(ctx, sql, id)
}
```

## Channels vs sync

Pick the simpler tool for the job. Channels are for *transferring ownership* of data and *coordinating* goroutines (pipelines, fan-out/fan-in, signaling). Mutexes are for *protecting shared state* that several goroutines read and write. Reaching for a channel to guard a counter is overengineering; a `sync.Mutex` (or `sync/atomic`) is clearer and faster.

| Use | Tool |
| --- | --- |
| Pass data between goroutines, pipelines, signaling | channels (`chan T`, `select`) |
| Protect a shared map/slice/counter | `sync.Mutex` / `sync.RWMutex` |
| Lock-free counters and flags | `sync/atomic` (`atomic.Int64`, `atomic.Bool`) |
| Run something exactly once | `sync.Once` |
| Wait for N goroutines to finish | `sync.WaitGroup` |
| Deduplicate concurrent identical calls | `golang.org/x/sync/singleflight` |

Direction-restrict channel parameters to document intent and let the compiler enforce it: `func produce(out chan<- T)` (send-only), `func consume(in <-chan T)` (receive-only).

## errgroup for concurrent work that can fail

When you fan out several operations that each return an error and you want the first failure to cancel the rest, `golang.org/x/sync/errgroup` is the idiomatic choice -- it bundles a `WaitGroup`, a shared cancellable context, and first-error capture.

```go
g, ctx := errgroup.WithContext(ctx)
for _, id := range ids {
    id := id // capture before Go 1.22; harmless after
    g.Go(func() error {
        return fetchAndStore(ctx, id) // first error cancels ctx for the rest
    })
}
if err := g.Wait(); err != nil {
    return fmt.Errorf("fetch all: %w", err)
}
```

Use `g.SetLimit(n)` to bound concurrency. For long-lived worker pools rather than a bounded fan-out, a dedicated pool library (e.g. `pond`) or a fixed set of worker goroutines reading a job channel is appropriate -- but reach for those only when a plain `errgroup` or a handful of goroutines is genuinely insufficient.

## Always test with the race detector

Run `go test -race ./...` in CI. The race detector catches data races that are invisible in normal runs and impossible to reproduce reliably. A race that "never happens" in testing will happen in production under load.

## Anti-Pattern

A goroutine with no exit path and a mutex held across a blocking call:

```go
func (s *Service) watch() {
    go func() {            // never stops; leaks for the process lifetime
        for {
            s.mu.Lock()
            resp, _ := http.Get(s.url) // holding the lock across network I/O!
            s.cache = resp
            s.mu.Unlock()
            time.Sleep(time.Second)
        }
    }()
}
```

## Positive Pattern

Cancellable lifetime, and the lock scope kept tiny -- never held across I/O:

```go
func (s *Service) watch(ctx context.Context) {
    ticker := time.NewTicker(time.Second)
    defer ticker.Stop()
    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            data, err := s.fetch(ctx) // network call outside the lock
            if err != nil {
                s.log.Warn("watch fetch", "err", err)
                continue
            }
            s.mu.Lock()
            s.cache = data            // lock only guards the assignment
            s.mu.Unlock()
        }
    }
}
```
