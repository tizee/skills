---
urls:
  - https://go.dev/wiki/CodeReviewComments
  - https://google.github.io/styleguide/go/decisions
  - https://go.dev/doc/effective_go
---

# Review Checklist

Quick-reference questions for reviewing Go code. Not every question applies to every review -- pick the ones relevant to the change. When a question points to a deeper topic, read the matching reference file before forming the review.

## Correctness & Errors

- Is every returned error checked, or is one silently dropped with `_`?
- Are errors wrapped with `fmt.Errorf("...: %w", err)` (not `%v`) where context helps?
- Do error strings start lowercase, omit trailing punctuation, and avoid the words "error"/"failed"?
- Are conditions callers branch on exposed as sentinel errors (`var ErrX = errors.New`) and checked with `errors.Is`?
- Do errors carrying data implement a custom type with `Unwrap()` and get inspected with `errors.As`?
- Is `panic` used only for unrecoverable programmer errors, never for ordinary failures across a public boundary?

## Simplicity & Readability

- Is this the obvious implementation, or is it clever in a way the next reader will struggle with?
- Does the happy path stay at the base indentation level via early returns?
- Is there a premature abstraction or interface with only one implementation and no test need?
- Could a little duplication replace a confusing shared helper?

## Naming & Style

- Are package names short, lowercase, single words -- and not `util`/`common`/`helpers`?
- Do exported names avoid stuttering against the package (`http.Server`, not `http.HTTPServer`)?
- Do getters omit `Get` (`u.Name()`)? Do single-method interfaces end in `-er`?
- Is the code gofmt-clean (`gofmt -l` empty) and goimports-clean?

## Project Structure

- Is `internal/` used for private code instead of an over-broad `pkg/`?
- Is `main` thin -- parse, wire, run, shut down -- with logic in importable packages?
- Are packages grouped by domain cohesion, not by layer category (`models/`, `interfaces/`)?
- Do imports flow in one direction without circular-dependency risk?

## Interfaces & Types

- Are interfaces small and defined at the consumer, not published by the implementer?
- Does the code accept interfaces and return concrete types?
- Is the zero value of new types usable, or is there a hidden "must call Init first" trap?
- Are generics used for type-safe containers/concurrency, not to abstract business logic?
- Is embedding used for behavior reuse rather than to fake inheritance?

## Concurrency

- For every `go`, is it clear when the goroutine exits and who waits for it (no leaks)?
- Does `context.Context` flow as the first parameter into every blocking call?
- Is every `context.WithTimeout`/`WithCancel` paired with `defer cancel()`?
- Are mutexes kept off `.await`-style blocking points -- i.e., no lock held across I/O?
- Is the right tool chosen: channels for coordination, `sync`/`atomic` for shared state?
- Does fan-out-that-can-fail use `errgroup`? Are channel parameters direction-restricted?
- Is the code tested with `-race`?

## API Design

- Is the exported surface minimal -- only what callers must use?
- Are struct fields private by default, set via constructor or methods?
- Does a constructor validate required inputs and fail loudly rather than defaulting them away?
- Are many-optional constructors using functional options, while simple ones stay plain?
- Does every exported identifier have a doc comment starting with its name?
- Are unreadable boolean parameters replaced with named types or options?

## Config, Logging & CLI

- Is config validated after loading, with a loud failure on missing required values/secrets?
- Are required secrets refused (not defaulted) when absent?
- Is logging structured (`log/slog` key-values), not `fmt.Sprintf` strings?
- Is each error logged once at a boundary, not logged-and-returned (double reporting)?
- Are secrets/tokens kept out of logs?
- Does a long-running server shut down gracefully on SIGINT/SIGTERM with a bounded context?

## Testing

- Are tests table-driven with descriptive subtest names via `t.Run`?
- Do tests assert error identity (`errors.Is`/`errors.As`), not error strings?
- Are edge cases covered: empty, nil, boundaries, and the error paths?
- Are helpers marked `t.Helper()`, temp dirs from `t.TempDir()`, teardown via `t.Cleanup`?
- Is `go test -race` run for concurrent code? Are golden files in `testdata/` for large output?

## Build & Tooling

- Does CI run `gofmt -l`, `go vet ./...`, `golangci-lint run`, and `go test -race ./...`?
- Is `go mod tidy` clean (no missing/unused dependencies)?
- Is each new dependency justified, maintained, and not replaceable by the standard library?
- Is the `go` directive set to a real, supported version (not an unreleased toolchain without reason)?

## Module & Version Strategy

- Is the project a single repo/single module unless multiple modules genuinely need atomic evolution?
- Is `go.work` kept out of CI (`GOWORK=off`) so the tested dependency graph matches external consumers?
- Does the exported API evolve by addition (new function/option struct), with breaking changes deferred to a new major version?
- For v2+, does the module path carry the `/vN` suffix?

## Security & Supply Chain

- Does CI run `govulncheck ./...` as a hard gate (non-zero exit fails the build), not an ignored advisory?
- Are `go.mod`/`go.sum` committed, tool-maintained, and never hand-edited?
- Is untrusted input validated and size-bounded at the trust boundary?
- Are SQL/shell/path operations parameterized rather than string-concatenated from user input?
- Are required secrets refused when absent (no insecure default) and kept out of logs?

## Performance & Observability

- Is any performance change backed by a before/after benchmark, not a guess?
- Was a `pprof`/`trace` profile consulted before optimizing (rather than optimizing by intuition)?
- Are the common anti-patterns avoided: map-where-slice-fits, hot-path allocation, lock contention mistaken for CPU, concurrency before correctness?
- Are `pprof`/`trace` diagnostic endpoints exposed on an admin/private port, never the public one?
- Does the service emit the four signals: structured logs, metrics (rate/errors/latency + runtime), liveness/readiness probes, diagnostic endpoints?
