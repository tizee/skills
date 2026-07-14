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

One sanctioned exception: when a package's *purpose* is a pluggable contract with multiple interchangeable backends (the `database/sql`/`driver` shape), the interface lives in the parent package with implementations in subpackages -- see the "two legitimate homes for an interface" section in project-structure.md.

## Keep interfaces small

The standard library's most-used interfaces have one method: `io.Reader`, `io.Writer`, `fmt.Stringer`. Small interfaces are easy to implement, easy to mock, and compose freely (`io.ReadWriter` is just `Reader` + `Writer`). A ten-method interface is a design smell -- it usually means you are describing a concrete type, not an abstraction.

Do not create an interface "just in case." Add one when you have a *second* implementation or a genuine need to mock in tests. A single-implementation interface is premature abstraction.

## Capability interfaces: opt-in behavior via type assertion

When some implementations of a base interface support an extra capability and others do not, do not widen the base interface to carry optional methods everyone must stub. Declare the capability as its own tiny interface and let a caller *discover* it with a type assertion. This is exactly how the standard library exposes `io.WriterTo`, `http.Flusher`, and `http.Hijacker`: a value opts in by implementing the smaller interface, and the consumer probes for it.

```go
// The base contract every backend implements.
type Hypervisor interface {
    Type() string
    Start(ctx context.Context, refs []string) ([]string, error)
    // ... the methods all backends share
}

// Optional capabilities, each its own small interface. A backend opts in
// simply by implementing the methods; nothing forces the ones that can't.
type Hibernator interface {
    Hibernate(ctx context.Context, ref string, persist func(cfg *Config, dir string) error) error
}

type Watchable interface {
    WatchPath() string
}
```

The consumer asks whether *this* value supports the capability, and degrades cleanly when it does not:

```go
// A backend that cannot hibernate fails loudly with a precise message,
// instead of every backend being forced to implement a no-op stub.
hib, ok := hyper.(Hibernator)
if !ok {
    return fmt.Errorf("backend %s does not support hibernate", hyper.Type())
}
return hib.Hibernate(ctx, ref, persist)

// Skip-and-continue when the capability is genuinely optional:
for _, h := range backends {
    w, ok := h.(Watchable)
    if !ok {
        continue // this backend just isn't watchable; that's fine
    }
    watch(w.WatchPath())
}
```

Why this beats a fat base interface: backends that lack a capability never grow meaningless stub methods, each capability interface stays one or two methods (trivial to implement and mock), and adding a new capability does not touch the base contract or any backend that ignores it. Keep the assertion honest with a compile-time check on the implementers that *do* support it: `var _ Hibernator = (*Firecracker)(nil)`.

## Template method via injected closures

To share an orchestration skeleton across implementations that differ only in a few steps, do not reach for inheritance or an abstract base type -- Go has neither. Pass the varying steps as function fields in a *spec* struct, and let one shared method run the fixed skeleton while calling the injected hooks at the right points. This is the Go answer to the template-method pattern.

```go
// The spec carries the steps that vary per backend; the skeleton owns the
// order, the locking, and the error handling that must be identical.
type StartSpec struct {
    RuntimeFiles []string
    Launch       func(ctx context.Context, rec *VMRecord, sock string) (int, error)
    PostLaunch   func(ctx context.Context, rec *VMRecord, sock string, pid int) error
    Wrap         func(rec *VMRecord, fn func() error) error // optional
}

// One shared skeleton, written once, correct for every backend: it holds the
// ops lock, validates invariants, then calls the injected steps in order.
func (b *Backend) StartSequence(ctx context.Context, id string, spec StartSpec) error {
    unlock, err := b.lockOps(ctx, id)
    if err != nil {
        return err
    }
    defer unlock()
    rec, err := b.prepare(ctx, id, spec.RuntimeFiles)
    if err != nil {
        return err
    }
    return runWrapped(rec, spec.Wrap, func() error {
        pid, err := spec.Launch(ctx, rec, sockPath(rec))
        if err != nil {
            return fmt.Errorf("launch VM: %w", err)
        }
        if spec.PostLaunch != nil {
            if err := spec.PostLaunch(ctx, rec, sockPath(rec), pid); err != nil {
                return fmt.Errorf("configure VM: %w", err)
            }
        }
        return nil
    })
}

// runWrapped applies an optional wrapper hook; a nil hook is a no-op.
func runWrapped(rec *VMRecord, wrap func(*VMRecord, func() error) error, fn func() error) error {
    if wrap != nil {
        return wrap(rec, fn)
    }
    return fn()
}
```

Each backend supplies only its own steps; the tricky invariants (lock ordering, state flips, cleanup on failure) live in exactly one place:

```go
func (fc *Firecracker) startOne(ctx context.Context, id string) error {
    return fc.StartSequence(ctx, id, StartSpec{
        RuntimeFiles: runtimeFiles,
        Launch:       func(ctx context.Context, rec *VMRecord, sock string) (int, error) { return fc.launch(ctx, rec, sock) },
        PostLaunch:   func(ctx context.Context, rec *VMRecord, sock string, _ int) error { return fc.configure(ctx, rec, sock) },
    })
}
```

Use this when the *order and safety* of steps must be identical across implementations but individual steps differ. Prefer it over embedding when the shared logic is a *procedure* (a sequence with locking and error handling) rather than a *set of reusable methods*. Do not use it for two implementations that share nothing but a signature -- a little copying is cheaper than a hook nobody else uses. Optional hooks should be nil-tolerant (guard with `if spec.X != nil` or a `runWrapped`-style helper) so a backend pays only for the steps it needs.

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

When a value is *deserialized* rather than constructed (loaded from JSON, an empty store, a snapshot), the zero value can be almost-usable but for a few nil maps or slices. Rather than scatter `if m == nil { m = map[...]{} }` across every reader, let the type opt into a small repair interface the loader calls once:

```go
// Initer is optionally implemented by T to initialize zero-value fields
// (e.g. nil maps) after deserialization or when the backing store is empty.
type Initer interface {
    Init()
}

// The loader repairs the value once, centrally, before handing it to callers.
func (s *Store[T]) load() (*T, error) {
    v := new(T)
    if err := s.decode(v); err != nil {
        return nil, err
    }
    if init, ok := any(v).(Initer); ok {
        init.Init() // fill nil maps/slices so callers see a valid zero state
    }
    return v, nil
}
```

This keeps the "make the zero value valid" work in one place and off every call site, without forcing types that need no repair to implement anything.

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
