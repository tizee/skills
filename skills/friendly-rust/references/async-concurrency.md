---
urls:
  - https://tokio.rs/tokio/tutorial
  - https://doc.rust-lang.org/book/ch16-00-concurrency.html
  - https://docs.rs/tokio/latest/tokio/task/fn.spawn.html
  - https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html
---

# Async & Concurrency

## Goals

- Make thread-safety contracts visible in types and bounds (`Send`, `Sync`).
- Avoid blocking the async executor with CPU-heavy or synchronous I/O work.
- Handle cancellation and task lifecycle correctly.

## Guidance

- **Async futures are lazy state machines.** Nothing happens until polled. This means dropping a future cancels it -- code after the last `.await` may never run. Design with cancellation in mind.
- **`Send + 'static` for spawned tasks.** `tokio::spawn` requires the future to be `Send + 'static`. If your future captures non-Send references, use `spawn_local` or restructure. Encode these bounds in your public APIs so callers don't discover the constraint at `spawn` time.
- **Never block in async context.** File I/O, DNS lookups, heavy computation, and mutex waits (non-async) will stall the executor. Use `spawn_blocking` for unavoidable blocking operations.
- **`spawn_blocking` tasks cannot be aborted.** Calling `.abort()` on a `JoinHandle` from `spawn_blocking` only prevents the task from starting if it hasn't already; it will not interrupt a running blocking task. If you need cancellation, pass a cooperative flag (e.g., `AtomicBool` or `CancellationToken`) and check it periodically inside the blocking closure.
- **Do not hold locks across `.await` points.** A `MutexGuard` (from `std::sync::Mutex`) held across an `.await` can cause deadlocks because the future may be suspended and resumed on a different thread. Either use an async-aware mutex (e.g., `tokio::sync::Mutex`) or restructure to drop the guard before awaiting.
- **Update stored wakers in custom `Future` implementations.** If your `Future::poll` stores a waker, it must update it on every poll call -- the executor may provide a different waker each time.

## Anti-Pattern: Blocking in Async

```rust
async fn read_config() -> Config {
    // std::fs blocks the executor thread.
    let content = std::fs::read_to_string("config.toml").unwrap();
    toml::from_str(&content).unwrap()
}
```

## Positive Pattern: Offload to Blocking Thread

```rust
async fn read_config() -> Result<Config, Box<dyn std::error::Error + Send + Sync>> {
    let content = tokio::task::spawn_blocking(|| {
        std::fs::read_to_string("config.toml")
    }).await??;
    Ok(toml::from_str(&content)?)
}
```

## Anti-Pattern: Lock Held Across Await

```rust
async fn update_cache(cache: &std::sync::Mutex<HashMap<String, String>>, key: String) {
    let mut guard = cache.lock().unwrap();
    let value = fetch_value(&key).await; // guard held across await!
    guard.insert(key, value);
}
```

## Positive Pattern: Drop Guard Before Await

```rust
async fn update_cache(cache: &std::sync::Mutex<HashMap<String, String>>, key: String) {
    let value = fetch_value(&key).await; // no lock held here
    let mut guard = cache.lock().unwrap();
    guard.insert(key, value);
}
```

## Anti-Pattern: Aborting spawn_blocking

```rust
let handle = tokio::task::spawn_blocking(|| heavy_cpu_work());
handle.abort(); // does NOT stop the work if already running
```

## Positive Pattern: Cooperative Cancellation

```rust
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

let cancel = Arc::new(AtomicBool::new(false));
let cancel_clone = cancel.clone();

let handle = tokio::task::spawn_blocking(move || {
    for chunk in data.chunks(1024) {
        if cancel_clone.load(Ordering::Relaxed) {
            return Err(Cancelled);
        }
        process_chunk(chunk);
    }
    Ok(())
});

// To cancel:
cancel.store(true, Ordering::Relaxed);
```

## Send/Sync Testing

Add compile-time assertions for public types that participate in concurrency:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn assert_send<T: Send>() {}
    fn assert_sync<T: Sync>() {}

    #[test]
    fn types_are_thread_safe() {
        assert_send::<MyService>();
        assert_sync::<MyService>();
    }
}
```
