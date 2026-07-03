---
urls:
  - https://go.dev/doc/modules/layout
  - https://go.dev/blog/organizing-go-code
  - https://go.dev/wiki/CodeReviewComments
---

# Project Structure

Go's layout conventions are lighter than most languages: there is no enforced framework directory, just a few load-bearing conventions (`internal/`, `cmd/`) the toolchain understands, plus community consensus. Start small and add structure only when the project earns it. The official guidance (go.dev/doc/modules/layout) is explicit that a tiny package can be a single `.go` file at the repo root.

## The three load-bearing directories

| Directory | Meaning | When to use |
| --- | --- | --- |
| `cmd/<name>/` | Entry points. One subdirectory per binary, each with `package main` and a thin `main.go`. | As soon as you have one or more binaries, especially multiple. |
| `internal/` | Private code. The compiler **forbids** imports from outside the parent module. | The default home for almost all your code. Reach for this before `pkg/`. |
| `pkg/` | Public library code intended for external consumption. | Only if you are publishing a reusable library. Most apps never need it. |

The key insight: `internal/` is enforced by the Go toolchain, so it is your strongest tool for keeping a clean public surface. `pkg/` is purely convention and is *overused* -- if nobody imports your code from another module, it does not belong in `pkg/`. Put it in `internal/`.

## Recommended layouts

**Small project (a single binary, a few packages):** keep it flat. No `cmd/`, no `internal/` -- just packages at the root. Adding directories before you need them is friction without benefit.

```
myapp/
├── go.mod
├── main.go
├── server.go
└── store.go
```

**Standard application (the consensus across the projects studied):**

```
myapp/
├── go.mod
├── cmd/
│   └── server/
│       └── main.go          # thin: parse flags, wire deps, run
├── internal/
│   ├── config/              # config loading + validation
│   ├── server/              # HTTP server, router, middleware
│   ├── handler/             # request handlers
│   ├── service/             # business logic
│   ├── repository/          # data access (db, cache)
│   └── pkg/                 # cross-cutting internal helpers (logger, errors)
└── config.example.yaml
```

**CLI with subcommands (cobra idiom):** each subcommand gets its own package under `cmd/<app>/`, receiving dependencies through a constructor or `Dependencies` struct:

```
myagent/
├── cmd/
│   └── myagent/
│       ├── main.go
│       ├── root.go          # newRootCmd() wires subcommands
│       ├── runcmd/          # one package per subcommand
│       └── servecmd/
├── internal/                # private packages live here at module root
│   ├── bus/
│   └── logutil/
└── agent/                   # domain packages can sit at root too
```

**Larger multi-binary service (the report's bootstrap template):** when a service grows several binaries and clear layers, separate orchestration, domain, and infrastructure inside `internal/`. The guiding rule is that **dependencies point inward** -- infrastructure depends on domain, never the reverse -- so business rules stay free of database and transport concerns.

```
project/
├── cmd/
│   ├── api/main.go          # entry points only
│   └── worker/main.go
├── internal/
│   ├── app/                 # use-case orchestration (wires domain + platform)
│   │   ├── api/
│   │   └── worker/
│   ├── domain/              # business models and rules, no infra imports
│   │   ├── user/
│   │   └── order/
│   ├── platform/            # infrastructure adapters
│   │   ├── config/  db/  httpx/  logx/  metrics/  tracing/
│   └── testutil/
├── api/                     # external contracts (OpenAPI, proto)
├── configs/                 # example configs (dev.yaml, prod.yaml)
├── deployments/             # Dockerfile, k8s manifests
├── scripts/                 # lint.sh, test.sh, release.sh
├── .golangci.yml
├── Makefile
└── go.mod
```

The payoff: dependency direction is legible at review time, infrastructure never pollutes `domain`, and a reviewer can immediately tell whether a change touches a business boundary (`domain`), a use case (`app`), or a delivery boundary (`platform`/`deployments`). Do not adopt this whole structure for a small service -- it is the *destination* a growing service moves toward, not the starting point.

## Package design rules

- **Packages are units of cohesion, not categories.** Group by what the code *does* (the `user` domain), not by what kind of thing it is (`models`, `controllers`). Layer-named packages (`models/`, `dto/`, `interfaces/`) create import fan-out and circular-dependency headaches.
- **Keep `main` thin.** `cmd/server/main.go` should parse flags, load config, construct dependencies, start the server, and handle shutdown signals -- nothing more. All real logic lives in importable packages so it is testable.
- **Avoid `util`/`common`/`helpers`.** They accumulate unrelated functions and become a magnet for circular imports. If you genuinely need shared helpers, name the package after the concept (`stringext`, `logutil`, `fsext`).
- **Push interfaces to the consumer.** Define an interface in the package that *uses* it, not the package that implements it. This keeps the implementation package free of import dependencies and lets each consumer declare exactly the methods it needs.
- **`pkg/` is not privileged.** Go gives no special meaning to `pkg/`; `internal/` is the one the toolchain enforces. If you do publish reusable code, put it under a single top-level directory (`pkg/` or a named SDK directory) and treat its API as a contract. Otherwise, default to `internal/`.

## The two legitimate homes for an interface

"Push interfaces to the consumer" is the default, but it is not the only sanctioned pattern. There are exactly two, and choosing between them is a design decision worth making explicitly:

**1. Consumer-side interface (the default).** The package that *uses* a dependency declares the minimal interface it needs. Use this for business dependencies: a `billing` service that needs users declares its own two-method `UserStore`. Each consumer states its true requirements, implementations stay import-free, and mocks are trivial.

**2. Provider-side interface in the parent, implementations in subpackages.** When a package's *purpose* is to define a pluggable contract with multiple interchangeable backends, the interface lives in the parent package and each implementation gets a subpackage. This is the `database/sql`/`driver` shape, and it is the right one for swappable infrastructure:

```
internal/storage/
├── storage.go           # type Store interface { Get, Put, Delete }, shared errors
├── postgres/            # package postgres: implements storage.Store
├── s3/                  # package s3: implements storage.Store
└── memory/              # package memory: in-memory Store for tests
```

Rules that keep this shape healthy:

- The parent package contains the interface, shared sentinel errors (`storage.ErrNotFound`), and common option/config types -- **no implementation**. Subpackages import the parent, never each other, and never siblings.
- Constructors return the concrete type (`postgres.New(...) *postgres.Store`), which satisfies `storage.Store` at the wiring site (`cmd/` or `internal/app/`). Verify the contract at compile time in each implementation: `var _ storage.Store = (*Store)(nil)`.
- Consumers depend on `storage.Store` and stay ignorant of which subpackage is wired in.

How to choose: if the interface answers "what does *this consumer* need?", define it consumer-side. If it answers "what must *any backend* provide?", define it provider-side in the parent with subpackage implementations. A codebase that applies both patterns in their right places -- and neither anywhere else -- is what "interface in the parent package, implementation in subpackages" discipline actually means.

## Anti-Pattern

Layer-named packages forcing artificial imports and risking cycles:

```
internal/
├── models/      # User, Order, Product -- everything imports this
├── interfaces/  # all interfaces, far from their implementations
├── services/    # imports models AND interfaces
└── utils/       # imports everything, imported by everything -> cycles
```

## Positive Pattern

Domain packages that own their types, interfaces, and logic together:

```
internal/
├── user/        # User type, UserStore interface (defined here, used here), logic
├── order/       # Order type, its store, its service
└── billing/     # depends on user + order via their small interfaces
```

Each package is self-contained, imports flow in one direction, and a reader looking for "how users work" finds everything in one place.
