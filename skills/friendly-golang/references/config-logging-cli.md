---
urls:
  - https://pkg.go.dev/log/slog
  - https://github.com/spf13/cobra
  - https://github.com/spf13/viper
  - https://gobyexample.com/signals
---

# Config, Logging & CLI

These three concerns surround almost every Go service. The community has clear defaults, but also real divergence -- this file gives the consensus plus the tradeoffs so you can choose deliberately rather than by habit.

## Configuration

There are two well-trodden approaches, and the projects studied split between them:

1. **viper** (`github.com/spf13/viper`) -- layered config: defaults, then a YAML/TOML file, then environment variables, with one merged view. Best when you need env-var overrides, multiple search paths, and live-ish reconfiguration. The idiom: set defaults, configure an env replacer (`.` -> `_`), `AutomaticEnv()`, read the file (optional), then `Unmarshal` into a struct with `mapstructure` tags.

```go
viper.SetConfigName("config")
viper.SetConfigType("yaml")
viper.AddConfigPath(".")
viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
viper.AutomaticEnv()           // DATABASE_HOST overrides database.host
setDefaults()                  // viper.SetDefault(...) for every key
_ = viper.ReadInConfig()       // missing file is fine -> use defaults
var cfg Config
if err := viper.Unmarshal(&cfg); err != nil {
    return nil, fmt.Errorf("unmarshal config: %w", err)
}
```

2. **Hand-rolled `gopkg.in/yaml.v3`** -- unmarshal a YAML file directly into a tagged struct. Best when config is a single file with no env-override matrix; it is simpler, dependency-light, and the struct *is* the schema. Use dual tags (`yaml:"port" json:"port"`) if the same struct is also serialized to JSON.

Whichever you pick, **validate exhaustively after loading and fail loudly**. A `Validate()` method that returns `fmt.Errorf("server.port must be 1-65535, got %d", p)` for every constraint turns misconfiguration into an immediate, legible startup error instead of a mysterious runtime failure. Never default-away a required secret -- if `jwt.secret` is empty in production, refuse to start.

## Logging

Default to the standard library's **`log/slog`** (Go 1.21+) for new code. It is structured, in the stdlib (no dependency), and supports text and JSON handlers. Reach for `zap` only when you have measured a logging-throughput bottleneck, or `logrus` only to match an existing codebase -- both are fine, but `slog` is the friendly default now.

```go
logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))
slog.SetDefault(logger)

// structured key-value pairs, not formatted strings:
slog.Info("request handled", "method", r.Method, "path", r.URL.Path, "status", 200)
slog.Error("upstream call failed", "url", url, "err", err)
```

Logging rules:
- Log structured key-value pairs, not `fmt.Sprintf` strings -- structure is queryable.
- Pass a `*slog.Logger` into components (via constructor/options); avoid scattering global `slog.Info` calls through library code so callers can control output.
- Do not log and return the same error -- that double-reports it. Log it once, at the boundary that decides to stop propagating it (usually the top-level handler).
- Never log secrets, tokens, or full request bodies.

## CLI

For anything beyond a couple of flags, use **`github.com/spf13/cobra`**, the de facto standard (and what `kubectl`, `hugo`, and the projects studied use). For a flag-only tool, the stdlib `flag` package is enough -- do not pull in cobra for two flags.

The cobra idiom that scales: a thin `main`, a `newRootCmd()` that wires subcommands, and **one package per subcommand** under `cmd/<app>/<name>cmd/`, each exposing a `New(...)` that returns a `*cobra.Command`. Inject dependencies into subcommands through a constructor or a `Dependencies` struct of function closures, so subcommands stay testable and decoupled from global state.

```go
func newRootCmd() *cobra.Command {
    root := &cobra.Command{Use: "myapp", Short: "..."}
    root.PersistentFlags().String("config", "", "config file path")
    root.AddCommand(servecmd.New(deps))
    root.AddCommand(migratecmd.New(deps))
    return root
}

func main() {
    if err := newRootCmd().Execute(); err != nil {
        os.Exit(1) // cobra already printed the error
    }
}
```

Bind build metadata via ldflags rather than hardcoding: `-X main.version={{.Version}}`.

## Graceful shutdown

A long-running server must drain in-flight work on SIGINT/SIGTERM, not drop it. The canonical pattern: start the server in a goroutine, block on a signal channel, then `Shutdown` with a timeout-bounded context.

```go
srv := &http.Server{Addr: ":8080", Handler: router}
go func() {
    if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
        slog.Error("listen", "err", err)
        os.Exit(1)
    }
}()

quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
<-quit

ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
if err := srv.Shutdown(ctx); err != nil {
    slog.Error("shutdown", "err", err)
}
```

## Anti-Pattern

Config defaults that hide a missing secret, and logging the same error twice:

```go
secret := os.Getenv("JWT_SECRET")
if secret == "" {
    secret = "dev-secret" // ships to prod, silently insecure
}
...
if err := doThing(); err != nil {
    slog.Error("doThing failed", "err", err)
    return err // already logged; the caller logs it again -> duplicate noise
}
```

## Positive Pattern

Refuse to start without the secret; log at the boundary only:

```go
secret := os.Getenv("JWT_SECRET")
if secret == "" {
    return fmt.Errorf("JWT_SECRET is required") // loud failure at startup
}
...
// deep in the stack: just wrap and return, do not log.
if err := doThing(); err != nil {
    return fmt.Errorf("handle login: %w", err)
}
// at the top-level handler: log once, respond.
```
