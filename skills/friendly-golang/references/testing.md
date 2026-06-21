---
urls:
  - https://go.dev/doc/tutorial/add-a-test
  - https://go.dev/blog/subtests
  - https://go.dev/wiki/TableDrivenTests
  - https://pkg.go.dev/testing
---

# Testing

Go's testing story is deliberately minimal: one `testing` package, `go test`, and a few strong conventions. The friendly default is to use the standard library and table-driven tests. Reach for third-party assertion or mocking libraries only when they genuinely earn their weight.

## Table-driven tests

The dominant Go test pattern, used in every project studied and throughout the standard library. Define a slice of cases, then loop and run each as a subtest with `t.Run`. Subtests give you isolated failures, named output, and the ability to run one case with `-run`.

```go
func TestParseDuration(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    time.Duration
        wantErr bool
    }{
        {name: "seconds", input: "30s", want: 30 * time.Second},
        {name: "minutes", input: "5m", want: 5 * time.Minute},
        {name: "invalid", input: "abc", wantErr: true},
        {name: "empty", input: "", wantErr: true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseDuration(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("ParseDuration(%q) err = %v, wantErr %v", tt.input, err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("ParseDuration(%q) = %v, want %v", tt.input, got, tt.want)
            }
        })
    }
}
```

Give each case a descriptive `name` -- it is what shows up in failure output and `-run` filters.

## Stdlib testing vs testify

Both are common and both are fine; choose deliberately:

- **Stdlib only** (`t.Fatalf` / `t.Errorf`): zero dependencies, explicit comparisons, the standard-library house style. Several mature projects use nothing else. The verbosity is the point -- the failure message says exactly what you compared.
- **testify** (`require`/`assert`): terser assertions and readable diffs on complex structs. `require.Equal(t, want, got)` stops the test on failure; `assert.Equal` continues. Reasonable when you compare large structs often.

Do not mix idioms randomly within a project -- pick one and stay consistent.

## Error assertions

Test error *identity*, not error strings. String matching is brittle and breaks when you improve a message. Use `errors.Is` for sentinels and `errors.As` for typed errors.

```go
_, err := store.Get(missingID)
if !errors.Is(err, store.ErrNotFound) {
    t.Fatalf("got %v, want ErrNotFound", err)
}
```

## Mocks: prefer hand-written stubs

Because interfaces are small and defined at the consumer, mocking is usually a five-line struct, not a generated framework. Define a stub that implements the tiny interface the code under test needs. Embedding the interface lets you stub only the one method you care about and leave the rest as nil (they will panic if unexpectedly called, which is a useful signal).

```go
type fakeUsers struct {
    service.UserRepository // embed: only override what the test exercises
    user *User
}

func (f fakeUsers) GetByID(_ context.Context, _ int64) (*User, error) {
    return f.user, nil
}
```

Reach for a mock-generation tool (mockgen, mockery) only for large interfaces you cannot shrink -- which itself is a hint the interface is too big.

## Test helpers and the toolkit

- `t.Helper()` in any helper function so failures point at the caller, not the helper.
- `t.TempDir()` for temp directories -- auto-cleaned, no manual `os.RemoveAll`.
- `t.Cleanup(fn)` to register teardown that runs even if the test fails.
- `t.Parallel()` to run independent tests concurrently; combine with `-race` to surface data races. (In Go 1.22+ loop variables are per-iteration, so the old `tt := tt` capture is no longer needed.)
- `httptest.NewServer` / `httptest.NewRecorder` for HTTP handler tests without a real network.

## Golden file tests

For functions whose output is large or formatted (rendered UI, generated code, serialized documents), golden files beat hand-written expected strings. Store expected output in `testdata/`, compare against it, and regenerate with a `-update` flag when the output legitimately changes. The `crush` TUI project leans heavily on this (hundreds of `.golden` files) because eyeballing rendered terminal output inline is hopeless.

```go
func TestRender(t *testing.T) {
    got := Render(input)
    golden := filepath.Join("testdata", "render.golden")
    if *update {
        os.WriteFile(golden, []byte(got), 0o644)
    }
    want, _ := os.ReadFile(golden)
    if got != string(want) {
        t.Errorf("output mismatch; run with -update to regenerate")
    }
}
```

`testdata/` is special: the Go tool ignores it for builds, so it is the conventional home for all test fixtures.

## What to test

- Test behavior through the public API, not private internals. Use a `package foo_test` external test package when you want to verify the package as a consumer sees it.
- Cover edge cases explicitly: empty input, nil, boundaries, the error paths. The error branches are where bugs hide because they run rarely.
- Run `go test -race ./...` in CI for any code with concurrency.

## Anti-Pattern

Brittle string matching and a repetitive non-table test:

```go
func TestGetMissing(t *testing.T) {
    _, err := store.Get(99)
    if err.Error() != "get user 99: not found" { // breaks if the message changes
        t.Fail() // and t.Fail with no message tells the reader nothing
    }
}
```

## Positive Pattern

Identity check, descriptive failure, edge cases as table rows:

```go
func TestGet(t *testing.T) {
    tests := []struct {
        name    string
        id      int64
        wantErr error
    }{
        {name: "found", id: 1, wantErr: nil},
        {name: "missing", id: 99, wantErr: store.ErrNotFound},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            _, err := store.Get(tt.id)
            if !errors.Is(err, tt.wantErr) {
                t.Fatalf("Get(%d) err = %v, want %v", tt.id, err, tt.wantErr)
            }
        })
    }
}
```
