---
urls:
  - https://go.dev/blog/package-names
  - https://go.dev/doc/comment
  - https://commandcenter.blogspot.com/2014/01/self-referential-functions-and-design.html
  - https://google.github.io/styleguide/go/best-practices#option-structure
---

# API Design

A good Go API is small, hard to misuse, and documented at the point of declaration. The exported surface is a contract you will struggle to change later, so expose as little as possible and make what you expose obvious.

## Constructors

When a type needs validated setup or initialized fields, provide a `New` constructor. Name it `New` if the package name already conveys the type (`http.NewRequest`, not `http.NewHTTPRequest`); name it `NewThing` when a package has several constructors. Return the concrete type plus an error if construction can fail.

```go
func New(cfg Config) (*Client, error) {
    if cfg.BaseURL == "" {
        return nil, errors.New("config: BaseURL is required")
    }
    return &Client{baseURL: cfg.BaseURL, http: http.DefaultClient}, nil
}
```

Validate required inputs in the constructor and fail loudly. A constructor that silently substitutes defaults for missing required config hides misconfiguration until it causes a confusing failure far away.

## Functional options for extensible configuration

When a constructor has many optional parameters and you expect to add more over time, the functional options pattern keeps the call site readable and the API backward-compatible. This is the dominant idiom for configurable servers and clients across the projects studied.

```go
type Server struct {
    addr    string
    timeout time.Duration
    log     *slog.Logger
}

type Option func(*Server)

func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }
func WithLogger(l *slog.Logger) Option   { return func(s *Server) { s.log = l } }

func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second, log: slog.Default()} // sane defaults
    for _, opt := range opts {
        opt(s)
    }
    return s
}

// call site reads clearly and only sets what it cares about:
srv := NewServer(":8080", WithTimeout(5*time.Second), WithLogger(myLog))
```

Use functional options when there are several optionals *and* you expect the set to grow. For two or three stable fields, a plain `Config` struct passed to `New` is simpler and just as good -- do not cargo-cult options onto everything.

## Doc comments

Every exported identifier gets a doc comment, and the comment **starts with the name** so `go doc` and pkg.go.dev render it correctly. Write what the thing does and any non-obvious behavior (does it block? is it safe for concurrent use? what does it return on the empty case?), not how it is implemented.

```go
// Client talks to the upstream API. A Client is safe for concurrent use by
// multiple goroutines.
type Client struct { ... }

// Fetch returns the user with the given id. It returns ErrNotFound if no such
// user exists, and wraps any transport error from the underlying HTTP client.
func (c *Client) Fetch(ctx context.Context, id int64) (*User, error) { ... }
```

A package gets a package comment on the `package` clause of one file (conventionally `doc.go` for larger packages) explaining what the package is for and showing a minimal usage example.

## Minimize the exported surface

Export only what callers must use. Everything else is lowercase and private. A smaller surface means fewer things you are committed to keeping stable, more freedom to refactor internals, and a cleaner pkg.go.dev page. Unexport struct fields by default and expose them through methods or set them in the constructor -- exported mutable fields let callers put your type into invalid states.

## Prefer values that read well at the call site

- Replace boolean parameters with named types or options when the call site would be unreadable: `Open(path, true, false)` tells the reader nothing; `Open(path, ReadOnly)` does.
- Return early to keep the happy path un-indented. The common Go shape is a stack of `if err != nil { return ... }` guards followed by the main logic at the base indentation level.

## Anti-Pattern

Exported mutable fields and an unreadable boolean-soup signature:

```go
type Cache struct {
    TTL      time.Duration // caller can set this to a negative value -> broken
    Capacity int
    mu       sync.Mutex
}

func NewCache(c int, t time.Duration, evict bool, lru bool, sync bool) *Cache { ... }
// NewCache(100, time.Minute, true, false, true) -- what do those booleans mean?
```

## Positive Pattern

Private fields, a constructor that validates, options that name their intent:

```go
type Cache struct {
    ttl      time.Duration
    capacity int
    mu       sync.Mutex
}

func NewCache(capacity int, opts ...Option) (*Cache, error) {
    if capacity <= 0 {
        return nil, fmt.Errorf("cache: capacity must be positive, got %d", capacity)
    }
    c := &Cache{capacity: capacity, ttl: time.Minute}
    for _, opt := range opts {
        opt(c)
    }
    return c, nil
}

// NewCache(100, WithTTL(5*time.Minute), WithEviction(LRU))
```
