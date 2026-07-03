---
name: friendly-golang
description: Practical guidance for writing, refactoring, and reviewing friendly Go code that is simple, idiomatic, and maintainable. Use whenever working with Go (.go) files, designing Go packages or APIs, structuring a new Go project, reviewing Go code, or refactoring Go modules. Also use when the user mentions goroutines, channels, context, error wrapping, interfaces, go.mod, package layout (cmd/internal/pkg), or Go project structure. Even if the user doesn't say "Go" explicitly, trigger this skill when the context involves .go files or go.mod/go.sum.
---

# friendly-golang

Concise guidance for writing Go code that is simple, idiomatic, and pleasant to maintain. Go rewards clarity over cleverness: "Clear is better than clever." The goal of this skill is to encode the consensus the wider community has converged on, grounded in real production projects, so that new code reads like it belongs in the standard library.

## Purpose and Triggers

- Use when writing new Go code, refactoring, reviewing, designing packages/APIs, or laying out a new project.
- Go source files (`.go`), `go.mod`/`go.sum`, or any Go module.
- Prefer simplicity and readability; reach for abstraction only when duplication actually hurts.

## Decision Order

1. **Correctness and clear boundaries** -- handle every error, propagate `context`, validate at edges
2. **Simplicity and readability** -- the obvious code over the clever code; small packages with clear names
3. **Idiomatic Go** -- accept interfaces, return structs; zero values that work; composition over inheritance
4. **Performance** -- profile with `pprof` before optimizing; do not guess

The ordering matters because Go's whole design philosophy is that a large team should be able to read and change each other's code years later. Optimizing for the reader is optimizing for the project's survival.

## Workflow

> **MANDATORY FIRST STEP:** When reviewing Go code, read [references/review-checklist.md](references/review-checklist.md) in full before producing any review. Then read the topic-specific reference file(s) relevant to the change (see Topics table below). Do not review from memory -- the reference files are the source of truth.

1. Read [references/review-checklist.md](references/review-checklist.md) (mandatory for any review).
2. Locate the relevant topic below and read its linked reference file.
3. Apply the guidance and compare against anti-pattern / positive-pattern examples.
4. Confirm the change against every applicable checklist item before reporting.

For any non-trivial change, run the toolchain (`gofmt`, `go vet`, `golangci-lint`, `go test ./...`) -- see [references/build-tooling.md](references/build-tooling.md). Formatting and vetting are not optional style preferences in Go; they are the baseline the entire ecosystem assumes. The deeper goal across these references is to **make the correct path the narrow default**: save triggers `gofmt`, commit triggers lint, merge triggers test + race + `govulncheck`. Discipline that lives in a pipeline survives; discipline that lives in a wiki does not.

## Topics

| Topic | Guidance | Reference |
| --- | --- | --- |
| Principles | Simplicity first, clarity over cleverness, accept interfaces return structs | [references/principles.md](references/principles.md) |
| Project Structure | `cmd/`, `internal/`, `pkg/` layout; package naming and boundaries | [references/project-structure.md](references/project-structure.md) |
| Source File Discipline | Single const/var blocks, exported-above ordering, comment density, zero bare TODO/FIXME | [references/source-file-discipline.md](references/source-file-discipline.md) |
| Error Handling | Wrap with `%w`, sentinel errors, `errors.Is/As`, custom error types | [references/error-handling.md](references/error-handling.md) |
| Interfaces & Types | Small consumer-side interfaces, zero values, embedding, generics | [references/interfaces-types.md](references/interfaces-types.md) |
| Concurrency | `context` propagation, goroutine lifecycle, channels, `sync`, `errgroup` | [references/concurrency.md](references/concurrency.md) |
| API Design | Functional options, constructors, doc comments, exported surface | [references/api-design.md](references/api-design.md) |
| Config, Logging & CLI | viper/yaml config, `log/slog`, cobra subcommands, graceful shutdown | [references/config-logging-cli.md](references/config-logging-cli.md) |
| Testing | Table-driven tests, subtests, `t.Parallel`, golden files, mocks | [references/testing.md](references/testing.md) |
| Security & Supply Chain | `govulncheck` as a CI gate, module proxy/checksum integrity, deserialization boundaries, dependency upgrade policy | [references/security-supply-chain.md](references/security-supply-chain.md) |
| Performance & Observability | Measure-first profiling (`pprof`, `trace`), PGO, structured logs, metrics, health probes | [references/performance-observability.md](references/performance-observability.md) |
| Build & Tooling | `go.mod`, modules, repo/version strategy, `gofmt`, `go vet`, `golangci-lint`, CI | [references/build-tooling.md](references/build-tooling.md) |
| Review | Quick-reference checklist covering all topics | [references/review-checklist.md](references/review-checklist.md) |

## References

- Each topic file lists source URLs in its frontmatter `urls`.
- Primary canonical sources: Effective Go, Go Code Review Comments, the Go standard library, and the official [Go module layout guidance](https://go.dev/doc/modules/layout).
