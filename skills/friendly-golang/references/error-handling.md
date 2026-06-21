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
