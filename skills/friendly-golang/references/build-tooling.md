---
urls:
  - https://go.dev/ref/mod
  - https://go.dev/blog/using-go-modules
  - https://pkg.go.dev/cmd/vet
  - https://golangci-lint.run/
---

# Build & Tooling

Go's tooling is part of the language's value proposition: one formatter everyone uses, a built-in vetter, fast builds, and reproducible modules. The friendly thing to do is lean on it fully rather than fighting it.

## Modules

`go.mod` declares the module path, the Go version, and dependencies; `go.sum` pins their checksums. Both are committed.

```
module github.com/you/myapp

go 1.25

require (
    github.com/spf13/cobra v1.10.2
    golang.org/x/sync v0.19.0
)
```

- The module path is the import prefix and should be the real repo URL so `go get` works.
- The `go 1.x` directive sets the language version and gates which features and standard-library behaviors are available. Set it to a version you actually build against; do not pin to an unreleased toolchain unless you have a reason.
- For a v2+ major version, the module path gets a `/v2` suffix (`github.com/you/myapp/v2`) -- this is how Go does breaking changes without breaking importers of v1.

## Repo and module strategy

Two principles separate the decisions cleanly: **repo structure follows release boundaries; package structure follows dependency direction.** Get those right and most layout debates evaporate.

- **Default to a single repo, single module.** It gives the simplest dependency management, the cleanest CI target, the easiest-to-explain releases, and the most stable `gopls`/IDE experience. A typical Go repo has exactly one root module; the simplest package can sit at the repo root, and multiple binaries become multiple `cmd/` directories sharing a top-level `internal/`.
- **Reach for a multi-module monorepo only when several modules must evolve atomically.** This is an advanced tool, not a starting point. Kubernetes is the canonical example: it keeps `k8s.io/*` modules under `staging/` and commits a `go.work` so they co-evolve -- but `go.mod`/`go.work` become generated artifacts maintained by scripts, with contribution rules forbidding hand-edits. That power is expensive; do not adopt it speculatively.
- **`go.work` is for local multi-module development, not CI.** Do not commit `go.work` for ordinary projects, and set `GOWORK=off` in CI. A committed workspace can make CI test a dependency combination that only holds locally, hiding what real external consumers will actually get. (Kubernetes commits its `go.work` precisely because it *is* the rare "modules only ever used by each other" case.)

## API evolution: add, don't change or remove

For any module others import, treat the exported surface as a contract and evolve it by **addition**. The official compatibility guidance is blunt: you cannot freely change a stable signature, and even a need as basic as "this function now takes a `context.Context`" should be met by adding a new method (e.g., `DoContext`) rather than altering the existing one.

- Need a new parameter? Add a new function or an options struct -- do not change the existing signature.
- A genuine breaking change goes into a new major version with the `/vN` module-path suffix, so v1 importers are never broken.
- Use `//go:linkname`-free, additive changes; mark deprecated-but-kept symbols with a `// Deprecated:` comment so tooling can warn without breaking builds.

Daily commands:

| Command | Purpose |
| --- | --- |
| `go mod tidy` | Add missing and remove unused dependencies; run before committing |
| `go mod download` | Fetch dependencies into the module cache |
| `go get pkg@version` | Add or upgrade a specific dependency |
| `go build ./...` | Build everything |
| `go test ./...` | Test everything |

Keep dependencies few and justified. Every dependency is code you now ship, must trust, and must keep updated. Before adding one, check whether the standard library already covers it (it often does) and whether the dependency is maintained.

## Formatting is not optional

`gofmt` (or `goimports`, which also fixes imports) defines the one true format. There are no style debates in Go because the formatter settles them. Run it on save, and enforce `gofmt -l` (lists unformatted files) or `goimports -l` in CI -- a non-empty list fails the build. Code that is not gofmt'd will look wrong to every Go reviewer.

## go vet

`go vet` catches correct-looking code that is actually wrong: `Printf` format-string mismatches, unreachable code, struct tags that will not parse, locks copied by value, loop variable capture mistakes. It is fast and has effectively no false positives -- run `go vet ./...` in CI alongside tests.

## golangci-lint

For deeper static analysis, `golangci-lint` runs many linters in one pass (and caches results). The trap is enabling everything on day one: a wall of nitpicks trains the team to ignore the tool. Tier the linters by priority and only climb tiers when the team wants to.

- **P0 (always on):** `govet`, `errcheck`, `staticcheck`, `errorlint` (correct error wrapping/comparison), `ineffassign`, `unused`, and a `depguard` rule to fence off banned imports.
- **P1 (recommended):** `gocritic`, `revive`, `misspell`, plus the formatters `gofumpt`, `goimports`, and `gci` (import grouping with a local prefix). Prometheus's own config enables exactly this formatter+linter combination.
- **P2 (team-tolerance dependent):** complexity and API-style checks like `cyclop`, `interfacebloat`, `godot`. Useful, opinionated, noisy -- turn them on deliberately.

`staticcheck` alone catches a large fraction of real Go bugs and belongs in every project. A friendly low-friction starting config:

```yaml
# .golangci.yml
version: "2"
run:
  timeout: 5m
formatters:
  enable: [gofumpt, goimports, gci]
  settings:
    goimports:
      local-prefixes: [github.com/acme/project]
    gci:
      sections: [standard, default, prefix(github.com/acme/project)]
linters:
  enable:
    - errcheck      # unchecked errors
    - errorlint     # correct %w / errors.Is usage
    - govet         # go vet
    - staticcheck   # the big one: bugs, simplifications, deprecations
    - ineffassign   # assignments that are never used
    - unused        # unused code
    - misspell      # typos in comments/strings
    - depguard      # fence off banned imports
```

## A friendly CI baseline

Design CI as "fast feedback, strong gates, weak exceptions": cheap static checks first so failures surface early, then tests, then build, then security as a hard gate. Set `GOWORK=off` so CI tests the same dependency graph external consumers see.

```bash
gofmt -l .                 # fails if anything is unformatted
go vet ./...               # catches obvious correctness bugs
golangci-lint run ./...    # deeper static analysis
go test -count=1 ./...     # tests
go test -count=1 -race ./...   # race detector on
go build ./cmd/...         # ensure binaries compile
govulncheck ./...          # supply-chain gate -- non-zero exit fails the build
```

The order matters: lint failures are cheaper to surface than a failed race test, and `govulncheck` is a *gate*, not an after-the-fact report (see [security-supply-chain.md](security-supply-chain.md)). For releases, `goreleaser` handles cross-compilation, checksums, and changelog generation, with build metadata injected via ldflags (`-X main.version=...`).

## Build constraints

Use build tags to separate platform-specific or test-tier code. File-suffix constraints (`store_linux.go`, `store_windows.go`) are picked up automatically. A `//go:build` line at the top of a file gates compilation; the projects studied use this to split fast unit tests from slow integration tests:

```go
//go:build integration

package repository
// ... tests that need a real database
```

Run the tagged set with `go test -tags=integration ./...`.

## Anti-Pattern

Skipping the toolchain, treating security as optional, and accumulating dependencies for trivial needs:

```bash
# no gofmt check, no vet, no race, no vulnerability gate in CI
go test ./...
govulncheck ./... || true   # scans but ignores the result -> vulns ship

# go.mod pulling in a dependency to pad a string:
require github.com/some/leftpad v1.0.0
```

## Positive Pattern

The full baseline as hard gates, a lean dependency set, and `go mod tidy` kept clean:

```bash
gofmt -l . && go vet ./... && golangci-lint run && \
  go test -race ./... && govulncheck ./...
```

Use `strings`/`fmt` from the standard library instead of a micro-dependency, run `go mod tidy` before every commit so `go.mod`/`go.sum` stay honest, and set `GOWORK=off` in CI so the tested dependency graph matches what real consumers get.
