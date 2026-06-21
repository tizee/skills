---
urls:
  - https://go.dev/wiki/CodeReviewComments#interfaces
  - https://go.dev/blog/laws-of-reflection
  - https://go.dev/doc/tutorial/generics
  - https://google.github.io/styleguide/go/best-practices#interfaces
---

# Interfaces & Types

Go's type system is structural for interfaces (implicit satisfaction) and nominal for everything else. The two most important habits: keep interfaces small and define them where they are used, and design types whose zero value already works.

## Accept interfaces, return structs

A function should accept the narrowest interface it actually needs and return a concrete type. Returning a concrete type gives the caller full access to the value and its methods; accepting an interface keeps the function decoupled from any specific implementation.

```go
// Accepts the minimal capability it uses; returns a concrete result.
func Copy(dst io.Writer, src io.Reader) (int64, error) { ... }

// Returns *Client, not some Clienter interface -- callers get everything.
func NewClient(cfg Config) *Client { ... }
```

## Define interfaces at the consumer

This is the single most distinctive Go interface idiom, and every project studied follows it. The package that *uses* a dependency declares the interface describing exactly the methods it needs. The implementing package returns its concrete type and never imports the interface.

```go
// package billing -- it needs to read users, so it declares what it needs.
type userReader interface {
    GetByID(ctx context.Context, id int64) (*user.User, error)
}

type Service struct {
    users userReader // any type with GetByID satisfies this, implicitly
}
```

Why this beats the Java-style "implementer publishes the interface": the interface is tiny (one method, not the whole repository surface), it lives next to the code that depends on it, and the implementing package has zero knowledge of who consumes it -- so there is no import coupling and tests can pass a trivial stub.

## Keep interfaces small

The standard library's most-used interfaces have one method: `io.Reader`, `io.Writer`, `fmt.Stringer`. Small interfaces are easy to implement, easy to mock, and compose freely (`io.ReadWriter` is just `Reader` + `Writer`). A ten-method interface is a design smell -- it usually means you are describing a concrete type, not an abstraction.

Do not create an interface "just in case." Add one when you have a *second* implementation or a genuine need to mock in tests. A single-implementation interface is premature abstraction.

## Useful zero values

Design types so the zero value is immediately usable. This removes the need for a constructor in simple cases and prevents the "forgot to call Init" class of bugs.

```go
var mu sync.Mutex        // ready to Lock, no constructor
var buf bytes.Buffer     // ready to Write
var b strings.Builder    // ready to use

// Your own types: pick field types whose zero values combine into a valid state.
type Counter struct {
    mu    sync.Mutex
    count int // zero value 0 is a valid starting count
}
// var c Counter is fully usable.
```

When a type genuinely needs setup (open connections, validated config), provide a `New` constructor that returns the concrete type and an error, and document that the zero value is not usable.

## Embedding over inheritance

Go has no inheritance. Composition through embedding gives you method promotion without the fragility of a class hierarchy. Embed to *reuse behavior*, not to model "is-a".

```go
type LoggingStore struct {
    *Store          // promotes Store's methods
    log *slog.Logger
}

func (s *LoggingStore) Get(id int64) (*User, error) {
    s.log.Info("get", "id", id)
    return s.Store.Get(id) // call through to the embedded type explicitly
}
```

## Generics: when (and when not)

Generics (Go 1.18+) earn their place in two situations: type-safe container and algorithm code (a generic `Map[K]V`, `Set[T]`, `slices`/`maps` style helpers), and concurrency-safe wrappers over those. The `crush` project, for example, has an internal `csync` package with generic mutex-guarded `Map[K,V]`, `Slice[T]`, and `Value[T]` types -- write the locking once, reuse it for every element type.

```go
// A concurrency-safe map, written once, reused for any key/value types.
type Map[K comparable, V any] struct {
    mu sync.RWMutex
    m  map[K]V
}

func (m *Map[K, V]) Get(k K) (V, bool) {
    m.mu.RLock()
    defer m.mu.RUnlock()
    v, ok := m.m[k]
    return v, ok
}
```

Do **not** reach for generics to abstract business logic or to avoid writing two slightly different functions. "A little copying is better than a little dependency" applies to generics too: if a type parameter makes a signature harder to read for no real reuse, write the concrete version.

## Anti-Pattern

A fat interface published by the implementer, forcing every caller to depend on the whole surface and making stubs painful:

```go
// package store -- publishes a 9-method interface nobody fully uses.
type UserRepository interface {
    Create(...); GetByID(...); GetByEmail(...); Update(...); Delete(...)
    List(...); Count(...); Search(...); BulkInsert(...)
}
// A consumer that only reads one user must still mock all nine methods to test.
```

## Positive Pattern

The consumer declares the one method it needs; testing is a two-line stub:

```go
// package billing
type userByID interface {
    GetByID(ctx context.Context, id int64) (*user.User, error)
}

// test stub:
type fakeUsers struct{}
func (fakeUsers) GetByID(context.Context, int64) (*user.User, error) {
    return &user.User{ID: 1}, nil
}
```
