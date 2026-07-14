---
urls:
  - https://go.dev/blog/error-handling-and-go
  - https://go.dev/blog/go1.13-errors
  - https://go.dev/wiki/CodeReviewComments#error-strings
  - https://google.github.io/styleguide/go/decisions#errors
---

# Error Handling

Errors are values in Go, not exceptions. That is the whole model: you return them, inspect them, wrap them, and decide what to do at each call site. Since Go 1.13, the standard library (`errors`, `fmt`) gives you everything you need -- there is no reason to reach for `github.com/pkg/errors` in new code. All the projects studied have migrated to stdlib-only error handling.

## The three building blocks

1. **Wrapping with `%w`** to add context while preserving the chain.
2. **Sentinel errors** (`var ErrFoo = errors.New(...)`) for conditions callers branch on, checked with `errors.Is`.
3. **Custom error types** for errors that carry structured data, inspected with `errors.As`.

Reach for the simplest one that fits. Most errors just need wrapping.

## Wrapping with %w

Wrap an error every time you return one up the stack, adding context about *what you were doing*. The `%w` verb (not `%v`) keeps the original error reachable via `errors.Is`/`errors.As`.

```go
func (s *Store) Load(ctx context.Context, id int64) (*User, error) {
    row, err := s.db.QueryRow(ctx, getUserSQL, id)
    if err != nil {
        return nil, fmt.Errorf("load user %d: %w", id, err)
    }
    ...
}
```

Conventions that matter:
- Error strings are lowercase and do not end in punctuation, because they get concatenated: `"load user 42: query timeout"` reads well; `"Load user 42.: Query timeout."` does not.
- Do not include the word "error" or "failed" in the message -- the fact that it is an error is implied by the type. Write `"open config: %w"`, not `"failed to open config, error: %w"`.
- Add context the caller does not already have. Wrapping `os.Open(path)` with `"open %s: %w"` is useful; wrapping it with `"open file: %w"` adds nothing.

## Sentinel errors

For conditions callers need to recognize and act on (not found, already exists, expired), declare a package-level sentinel and let callers check it with `errors.Is`. `errors.Is` walks the whole `%w` chain, so wrapping does not break the check.

```go
package store

var ErrNotFound = errors.New("not found")

func (s *Store) Get(id int64) (*User, error) {
    u, ok := s.users[id]
    if !ok {
        return nil, fmt.Errorf("get user %d: %w", id, ErrNotFound)
    }
    return u, nil
}

// caller, anywhere up the stack:
u, err := store.Get(42)
if errors.Is(err, store.ErrNotFound) {
    return http.StatusNotFound
}
```

Only export a sentinel if callers genuinely branch on it. An over-exported sentinel becomes part of your API contract forever.

## Custom error types

When an error must carry data (an HTTP status, a field name, a retry hint), define a type. Implement `Error() string` and, if it wraps a cause, `Unwrap() error` so `errors.As` and `errors.Is` traverse it.

```go
type APIError struct {
    Status  int
    Code    string
    Message string
    cause   error
}

func (e *APIError) Error() string {
    if e.cause != nil {
        return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.cause)
    }
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *APIError) Unwrap() error { return e.cause }

// constructors make intent obvious at the call site:
func NotFound(code, msg string) *APIError {
    return &APIError{Status: 404, Code: code, Message: msg}
}

// caller extracts the typed error to read its fields:
var apiErr *APIError
if errors.As(err, &apiErr) {
    w.WriteHeader(apiErr.Status)
}
```

## Cleanup on the error path: named returns + deferred rollback

An operation that acquires resources in several steps -- start a process, write a pid file, enter a namespace -- must undo the steps that *did* succeed if a later step fails. Scattering cleanup into every `return nil, err` branch duplicates it and inevitably drifts. The idiom is a single deferred closure that inspects the **named return** `err` and rolls back exactly what was reached, tracked by small boolean progress flags.

```go
// Named return err lets the deferred cleanup see whether we are failing.
func (b *Backend) LaunchVMProcess(ctx context.Context, spec LaunchSpec) (pid int, err error) {
    started := false
    pidWritten := false
    defer func() {
        if err == nil {
            return // success: keep everything we built
        }
        // failure: undo in reverse order, but only the steps we reached.
        if pidWritten {
            _ = os.Remove(spec.PIDPath)
        }
        if started {
            _ = spec.Cmd.Process.Kill()
            _ = spec.Cmd.Wait()
        }
        if spec.OnFail != nil {
            spec.OnFail()
        }
    }()

    if err = spec.Cmd.Start(); err != nil {
        return 0, fmt.Errorf("exec %s: %w", spec.Name, err)
    }
    started = true
    pid = spec.Cmd.Process.Pid

    if err = writePIDFile(spec.PIDPath, pid); err != nil {
        return 0, fmt.Errorf("write pid file: %w", err)
    }
    pidWritten = true

    if err = waitForSocket(ctx, spec.SockPath); err != nil {
        return 0, err // cleanup kills the process and removes the pid file
    }
    return pid, nil
}
```

Why this shape:
- **One cleanup path, not N.** Every failure return runs the same deferred rollback, so a new failure point added later is covered for free -- you cannot forget to clean up in a branch that does not exist yet.
- **Progress flags, not re-derivation.** `started`/`pidWritten` record what actually happened; the cleanup does not guess by re-`stat`-ing files. Reverse order matches acquisition order.
- **The assignment must target the named `err`.** Write `if err = f(); err != nil`, not `if err2 := f()`, or the defer sees a stale `nil` and skips rollback. This is the one subtlety -- keep every fallible step assigning the named return.
- **Ignore rollback errors deliberately.** Best-effort cleanup uses `_ =`; the original `err` is what the caller must see, and a secondary Kill/Remove failure should not mask it. (If a cleanup failure is itself important, join it with `errors.Join`.)

Reach for this whenever success requires several acquisitions that each need undoing; for a single resource, a plain `defer f.Close()` is enough.

## When to panic (rarely)

`panic` is for truly unrecoverable programmer errors -- a nil dependency that should have been wired at startup, an impossible switch case, a corrupt invariant. It is not for ordinary failures like a missing file or a bad request. Libraries should almost never panic across their public boundary; return an error and let the caller decide. If you must recover (e.g., an HTTP middleware catching a handler panic), recover at a clear boundary and convert it back into an error or a 500 response.

## Anti-Pattern

Discarding context with `%v`, and a useless message:

```go
data, err := os.ReadFile(path)
if err != nil {
    // %v breaks the chain: errors.Is(err, os.ErrNotExist) will now fail.
    // "failed to read file" adds no information the error didn't already have.
    return fmt.Errorf("failed to read file: %v", err)
}
```

## Positive Pattern

`%w` preserves the chain; the message names the operation and the input:

```go
data, err := os.ReadFile(path)
if err != nil {
    return fmt.Errorf("read config %s: %w", path, err)
}
// callers can still do: errors.Is(err, os.ErrNotExist)
```
