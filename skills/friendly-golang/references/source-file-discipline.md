---
urls:
  - https://google.github.io/styleguide/go/decisions
  - https://github.com/uber-go/guide/blob/master/style.md
  - https://go.dev/doc/comment
  - https://go.dev/wiki/CodeReviewComments
---

# Source File Discipline

Package layout decides where code lives; this file decides how a single `.go` file is ordered inside. Intra-file order is the discipline a reader feels first -- and the one automated reviewers flag most reliably, because it is pure local structure: declaration grouping, exported-above ordering, comment density, and TODO hygiene. A codebase that holds these invariants reads uniformly, file after file, with zero per-file surprises.

## Declaration grouping: one const block, one var block

Group related package-level declarations into a **single `const (...)` block and a single `var (...)` block** near the top of the file, after imports. Scattered one-line `const`/`var` declarations interleaved with functions force the reader to scan the whole file to learn the package state.

```go
const (
    defaultTimeout = 30 * time.Second
    maxRetries     = 3
)

var (
    ErrNotFound = errors.New("not found")
    ErrExpired  = errors.New("expired")
)
```

Refinements:

- An `iota` enumeration gets **its own block** -- do not mix unrelated constants into it, because inserting a line silently renumbers everything below.

```go
type State int

const (
    StateIdle State = iota
    StateRunning
    StateStopped
)
```

- Split into a second block only when the groups are genuinely unrelated (e.g., sentinel errors vs. tuning knobs) -- then each block is one theme, and the split itself carries meaning.
- Keep declarations close to use for *function-local* values; the single-block rule is about **package-level** state, which is global and therefore must be discoverable in one place.

## Exported above unexported

Within a file, the reader should meet the public contract before the private machinery. The canonical top-to-bottom order:

1. Package doc comment (on the `package` clause; `doc.go` for larger packages)
2. `const` block, then `var` block
3. The core exported type(s)
4. Constructor (`New`, `NewThing`)
5. Exported methods, in rough call order or logical grouping
6. Unexported methods and helper functions last

Two corollaries:

- **Group functions by receiver.** All methods of a type sit together, after the type's definition -- do not interleave methods of two types.
- **Helpers sink to the bottom.** An unexported helper appears after its first caller, never before. A file that opens with three private utility functions buries the lede.

This mirrors how `go doc` and pkg.go.dev present the package: contract first, mechanism second. A file ordered this way needs no roadmap comment.

## Comment density: doc comments plus why, nothing else

Every exported identifier gets a doc comment (see api-design.md). Beyond that, the target density is **low and intentional**:

- Comment **why**, never **what**. `// retry because the upstream LB drops idle conns after 60s` earns its line; `// increment counter` above `n++` is noise that rots.
- **No commented-out code.** Version control remembers deleted code; a commented block in the file is a question every future reader must re-ask ("is this coming back? is it load-bearing?"). Delete it.
- **No section banners.** `// ---- helpers ----` dividers signal the file should be split or reordered, not decorated. Correct declaration order makes banners redundant.
- **No narrating the obvious flow.** If a function needs step-by-step comments to be followed, restructure it (extract, rename, early-return) until it does not.

The test for any non-doc comment: *would the code be misunderstood without it?* If not, remove it.

## Zero TODO/FIXME in committed code

A bare `TODO` is a decision deferred with no owner and no deadline -- it survives for years and trains readers to ignore markers. The policy:

- **Do it, or ticket it.** Either finish the work before merging, or file an issue and link it: `// TODO(#123): remove after the v2 migration completes.` The tracker owns the lifecycle; the comment is just a pointer.
- **Never merge a bare `TODO`, `FIXME`, or `XXX`** with no reference. Review should flag them the same way it flags an ignored error.
- Enforce mechanically, not socially: `golangci-lint` includes the `godox` linter, which fails the build on unreferenced TODO markers. Discipline that lives in a pipeline survives.

## Anti-Pattern

Scattered declarations, helper-first ordering, noise comments, and an orphan TODO:

```go
package cache

// ---- helpers ----

// checkKey checks the key.
func checkKey(k string) bool { // private helper opens the file
    return k != ""
}

var ErrMiss = errors.New("miss")

const defaultTTL = time.Minute

// TODO: handle eviction properly
type Cache struct{ ... }

var maxEntries = 1024 // second var declaration, far from the first

func (c *Cache) Get(k string) ([]byte, error) {
    // check the key
    if !checkKey(k) { ... }
    // old implementation:
    // v, ok := c.m[k]
    // if !ok { return nil, ErrMiss }
    ...
}
```

Every problem here is local and mechanical -- which is exactly why it erodes trust fastest: it signals nobody is holding the line.

## Positive Pattern

One const block, one var block, contract before machinery, comments that earn their lines:

```go
// Package cache provides an in-memory TTL cache safe for concurrent use.
package cache

const (
    defaultTTL = time.Minute
    maxEntries = 1024
)

var ErrMiss = errors.New("miss")

// Cache is a bounded in-memory cache. The zero value is not usable; use New.
type Cache struct{ ... }

// New returns a Cache holding at most maxEntries items.
func New() *Cache { ... }

// Get returns the value for key k, or ErrMiss if absent or expired.
func (c *Cache) Get(k string) ([]byte, error) {
    // Expiry is checked lazily on read: a background sweeper would cost a
    // goroutine per cache for little gain at this size.
    ...
}

func (c *Cache) evictOldest() { ... } // unexported machinery sinks below
```
