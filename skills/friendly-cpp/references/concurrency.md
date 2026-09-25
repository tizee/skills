---
urls:
  - https://eel.is/c++draft/util.smartptr.shared#general-4
  - https://eel.is/c++draft/util.smartptr.atomic
  - https://eel.is/c++draft/thread.jthread.class
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-concurrency
  - https://clang.llvm.org/docs/ThreadSafetyAnalysis.html
---

# Concurrency

Most concurrency bugs in agent-written C++ come from one confusion: believing `shared_ptr` or `std::atomic` somewhere nearby makes the data thread-safe. Separate three layers and check each one.

## Three Layers

| Layer | Question | Guaranteed by |
| --- | --- | --- |
| **Ownership bookkeeping** | Can threads copy/destroy *different* `shared_ptr` instances to the same object concurrently? | Yes -- the control block's refcount is thread-safe. |
| **The pointee `T`** | Can threads read/write `*p` concurrently? | **Nothing automatic.** Needs a mutex, immutability, or atomics. |
| **The pointer variable itself** | Can threads read/write the *same* `shared_ptr` object concurrently? | Only with external locking or C++20 `std::atomic<std::shared_ptr<T>>`. |

```cpp
// Anti-pattern: ownership is safe, the vector is a data race.
auto p = std::make_shared<std::vector<int>>();
std::thread a([p] { p->push_back(1); });
std::thread b([p] { p->push_back(2); });
```

## Immutable Snapshot + Atomic Publication

A strong production pattern for configuration, routing tables, and other read-mostly state:

```cpp
std::atomic<std::shared_ptr<const Config>> current;   // C++20

void publish(std::shared_ptr<const Config> cfg) {
    current.store(std::move(cfg), std::memory_order_release);
}

void handle_request() {
    auto cfg = current.load(std::memory_order_acquire);  // hold for the whole request
    use(*cfg);
}
```

`const Config` makes the pointee immutable, so readers need no lock.

**Portability trap:** libc++ (Clang's default on macOS, still as of LLVM 22) does not implement `std::atomic<std::shared_ptr<T>>`; it fails to compile with "requires that 'T' be a trivially copyable type". libstdc++ has it since GCC 12, MSVC since 16.7. Where the standard library lacks it, guard the pointer variable with a mutex -- copy under the lock, use outside:

```cpp
class ConfigStore {
public:
    void publish(std::shared_ptr<const Config> cfg) {
        std::scoped_lock lock(mu_);
        current_ = std::move(cfg);
    }
    std::shared_ptr<const Config> load() const {
        std::scoped_lock lock(mu_);
        return current_;          // copy under lock; caller uses it lock-free
    }
private:
    mutable std::mutex mu_;
    std::shared_ptr<const Config> current_;   // guarded by mu_
};
```

The deprecated `std::atomic_load/atomic_store` free-function overloads for `shared_ptr` also work but are removed in C++26.

If the pointee is mutable, the atomic pointer protects only publication; the data needs its own synchronization.

## Mutexes

- Pair each mutex with the data it guards and say so at the declaration. With Clang, use Thread Safety Analysis annotations (`GUARDED_BY`, `REQUIRES`) or `absl::Mutex` so the compiler checks it.
- Lock with RAII only: `std::scoped_lock` (one or more mutexes, deadlock-avoiding), `std::unique_lock` (condition variables, deferred locking). Never raw `lock()`/`unlock()`.
- Keep critical sections small; never call unknown code (callbacks, virtual functions, logging sinks that may re-enter) while holding a lock.
- Never return a reference or pointer to guarded data from a locked accessor -- the lock is released at return.

```cpp
// Anti-pattern: reference escapes the lock.
const std::vector<Item>& Registry::items() {
    std::scoped_lock lock(mu_);
    return items_;
}

// Positive: return a copy (or a snapshot shared_ptr<const ...>).
std::vector<Item> Registry::items() const {
    std::scoped_lock lock(mu_);
    return items_;
}
```

- `mutable std::mutex mu_;` is the correct way to lock in `const` members.
- `std::condition_variable::wait` always takes a predicate: `cv.wait(lock, [&]{ return ready_; });`. A bare `wait` is a spurious-wakeup bug.

## Atomics

- `std::atomic<T>` makes single operations atomic, not sequences. `if (count.load() > 0) count--;` is a race; use `fetch_sub` / `compare_exchange` loops, or a mutex.
- Default to `memory_order_seq_cst`. Weaker orderings need a comment explaining the happens-before edge they rely on.
- `volatile` is not a synchronization primitive in C++. Any `volatile` used for inter-thread signaling is a bug.
- A plain `bool stop_ = false;` flag written by one thread and read by another is a data race (UB), not "harmless". Use `std::atomic<bool>` or `std::stop_token`.

## Threads

- Prefer `std::jthread` + `std::stop_token` (C++20) for owned threads: destruction requests stop and joins, so early returns and exceptions cannot leave a joinable thread (which would `std::terminate`).
- Prefer a task/executor abstraction the project already has over spawning raw threads per operation.
- `detach()` breaks the ownership model: the thread outlives everything it references. Blocking finding unless proven to touch only static or owned-by-copy data.
- Static-lifetime objects destroyed at exit while background threads still run is a classic shutdown crash. Join all threads before `main` returns.

## Destruction Thread

The last `shared_ptr` owner destroys the object on whatever thread drops it. For objects with heavy or thread-affine destructors (UI, GPU, thread-local resources, real-time threads), design teardown explicitly: post the final release to the owning thread, or require `shutdown()` on the right thread before dropping.

## Callbacks Across Threads

Any borrow crossing a thread boundary must re-prove lifetime. See the lambda-capture section in [lifetime-traps.md](lifetime-traps.md): capture by value, move ownership into the task, or `weak_from_this()` + `lock()`.

## Review Questions

- For every shared object: is ownership, pointee access, and pointer-variable access each synchronized?
- Does every mutex name the data it guards? Any raw `lock()`/`unlock()`? Any reference escaping a lock?
- Any check-then-act on an atomic? Any non-default memory order without a comment? Any `volatile` for threading?
- Any plain (non-atomic) flag shared between threads?
- Any `std::thread` that can be destroyed joinable, or any `detach()`?
- Was the concurrent code run under TSan ([tooling-testing.md](tooling-testing.md))?
