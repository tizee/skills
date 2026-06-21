---
urls:
  - https://go.dev/doc/security/best-practices
  - https://go.dev/blog/govulncheck
  - https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck
  - https://go.dev/ref/mod#module-proxy
  - https://sum.golang.org/
---

# Security & Supply Chain

Security in Go is most effective when it is a *pipeline action*, not a written policy nobody runs. The official guidance gives a concrete order, and mature projects (Moby, Prometheus) wire it into CI as a hard gate rather than a post-incident scramble. The friendly default: make the secure path the automatic path.

## The official security workflow, in order

1. **Keep the Go toolchain and dependencies current.** Security fixes land in releases; staying behind means shipping known-vulnerable code. (But do not blind-upgrade -- see the upgrade policy below.)
2. **Run `govulncheck`** against source or binaries to find vulnerabilities that actually reach your code.
3. **Fuzz** parsers, decoders, and anything handling untrusted input.
4. **Run the race detector** (`go test -race`) on concurrent code.
5. **Run `go vet`** for correctness issues that are also security-relevant (format strings, etc.).

This is a layered net: each step catches a class the others miss.

## govulncheck

`govulncheck` (`golang.org/x/vuln/cmd/govulncheck`) is the standard vulnerability scanner, and its key virtue is **low noise**. Unlike a generic CVE-list dump, it uses static analysis of your call graph to report only vulnerabilities your code can actually reach. A vulnerable function in a dependency you never call is not flagged -- so when it does report something, it is worth acting on.

```bash
govulncheck ./...                 # scan the module's reachable code
govulncheck -mode=binary ./bin/app  # scan a compiled binary
govulncheck -format=sarif ./...   # SARIF for security platforms / GitHub code scanning
```

It supports JSON, SARIF, and VEX output, so it slots directly into CI and security tooling. Treat a non-empty reachable-vulnerability result as a **build failure**, not a warning -- a vulnerability you can reach is one an attacker can reach.

## The module supply chain is your default integrity layer

Go's module ecosystem ships with a built-in supply-chain integrity story; use it rather than working around it.

- **`go.sum`** pins a cryptographic hash of every dependency's content. It is committed and is the contract that the code you build is the code that was reviewed. Never hand-edit `go.sum`; let `go mod tidy`/`go get` maintain it.
- **The module mirror** (`proxy.golang.org`) and **checksum database** (`sum.golang.org`) guarantee that a given `module@version` resolves to the same source for everyone, forever, and that it has not been tampered with. This is what makes builds reproducible across machines and time.
- If you run a **private proxy** (Athens, JFrog, etc.), preserve these verifiable semantics -- keep checksum verification on for public modules, and scope `GONOSUMCHECK`/`GOPRIVATE` only to genuinely private modules.

```
# Typical hardened module env:
GOFLAGS=-mod=readonly        # CI fails if go.mod/go.sum would change
GOPRIVATE=github.com/acme/*  # private modules bypass the public sum DB
```

## Dependency upgrade policy

"Always upgrade" and "never upgrade" are both wrong. The friendly middle:

- **Toolchain:** track at least the current supported minor Go release. The supported window is short (the two most recent major releases), and falling out of it means no security backports.
- **Third-party deps:** small steps, frequently, with a freeze before releases. Every bump goes through changelog review and the full test suite. Bumping ten dependencies in one unreviewed commit is how a compromised release slips in.
- **Security fixes:** give them a fast lane -- a dedicated, expedited path that does not wait for the normal cadence.
- Run `go mod tidy` before every commit so `go.mod`/`go.sum` never drift from reality.

## Handling untrusted input

- Validate and bound everything that crosses a trust boundary: request bodies, query params, file uploads, deserialized data. Set explicit size limits (`http.MaxBytesReader`) so a malicious client cannot exhaust memory.
- Never build SQL, shell commands, or paths by string concatenation from user input -- use parameterized queries, `exec.Command` with separate args, and `filepath.Clean` + containment checks.
- Keep secrets out of logs, errors, and source. Load them from the environment or a secrets manager, and refuse to start if a required secret is absent (fail loud, do not default).

## Anti-Pattern

Treating vulnerability scanning as advisory, and editing `go.sum` to make a build pass:

```bash
# CI: scans but ignores the result -- vulnerabilities ship anyway.
govulncheck ./... || true

# Worse: a developer hand-edits go.sum to silence a checksum mismatch,
# defeating the entire integrity guarantee.
```

## Positive Pattern

`govulncheck` as a hard gate, `go.sum` maintained only by the tool, deps in read-only mode:

```yaml
# .github/workflows/ci.yml (excerpt)
- name: Govulncheck
  run: |
    go install golang.org/x/vuln/cmd/govulncheck@latest
    govulncheck ./...        # non-zero exit fails the job

- name: Verify modules are tidy
  run: |
    go mod tidy
    git diff --exit-code go.mod go.sum   # fails if tidy changed anything
```
