---
urls:
  - https://go.dev/doc/effective_go
  - https://go.dev/wiki/CodeReviewComments
  - https://go-proverbs.github.io/
  - https://google.github.io/styleguide/go/
---

# Core Principles

## Goals

- Write the obvious code. A reader should understand a function on the first pass without holding much in their head.
- Make the zero value useful so callers can use a type without ceremony.
- Future maintainers should find intent, boundaries, and change points quickly. Go is built for large teams reading each other's code over years.

## Decision Order

1. Correctness and clear boundaries
2. Simplicity and readability
3. Idiomatic Go
4. Performance and optimization

## Principles

- **Clear is better than clever.** Go deliberately omits features (no inheritance, no exceptions, no generics-everywhere) so that code stays boring and legible. Embrace that constraint instead of fighting it.
- **Handle every error explicitly.** An ignored error is a latent bug. The `if err != nil` block is verbose on purpose: it makes failure paths visible at the call site. Do not paper over it with `_`.
- **Accept interfaces, return structs.** Functions should accept the smallest interface they actually use, and return concrete types so callers keep full access. Define the interface where it is *consumed*, not where the implementation lives.
- **A little copying is better than a little dependency.** Do not build a premature abstraction or pull in a dependency to save three lines. Duplication is cheaper to fix than the wrong abstraction.
- **The zero value should be useful.** `var buf bytes.Buffer` works without a constructor. `sync.Mutex{}` is ready to lock. Design types so the zero value is a valid, usable state when you can.
- **Fail loudly at boundaries.** Validate inputs at public API surfaces and return meaningful errors. Never silently substitute a default that masks a missing config or broken dependency -- a loud crash at startup beats silent corruption downstream.
- **Measure before optimizing.** Use `go test -bench`, `pprof`, and the race detector. Intuition about Go performance is frequently wrong; the compiler and GC are good.

## Naming

- Package names are short, lowercase, single words: `http`, `json`, `user`. Avoid `util`, `common`, `helpers`, `base` -- they are dumping grounds that signal missing structure.
- Exported identifiers are not stuttered against their package: `http.Server` not `http.HTTPServer`; `user.New` not `user.NewUser`.
- Getters drop the `Get` prefix: `u.Name()` not `u.GetName()`. Setters keep `Set`.
- Interface names for single-method interfaces end in `-er`: `Reader`, `Writer`, `Stringer`.

## Anti-Pattern

Cramming unrelated helpers into a grab-bag package and swallowing errors:

```go
// package util -- nobody knows what lives here, and the error vanishes
func DoThing(path string) string {
    data, _ := os.ReadFile(path) // ignored error -> phantom failure later
    return strings.TrimSpace(string(data))
}
```

The ignored error means a missing file silently returns an empty string, and the bug surfaces somewhere far away with no clue to the cause.

## Positive Pattern

A focused package, an explicit error, a useful return:

```go
// package config
func Load(path string) (string, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return "", fmt.Errorf("read config %s: %w", path, err)
    }
    return strings.TrimSpace(string(data)), nil
}
```

The caller decides what to do with the failure, and the wrapped error names exactly what went wrong and where.
