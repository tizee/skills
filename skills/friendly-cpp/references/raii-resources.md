---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rr-raii
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rc-zero
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rc-move-noexcept
  - https://eel.is/c++draft/unique.ptr
  - https://eel.is/c++draft/thread.jthread.class
  - https://en.cppreference.com/w/cpp/memory/out_ptr_t
---

# RAII and Resources

RAII is not about heap memory. Files, sockets, mutexes, transactions, mapped regions, GPU handles, database handles, C library objects -- anything with an `acquire()`/`release()` pair -- is released by a destructor, so cleanup runs on every path: normal return, early return, and exception.

## Rule of Zero First

A class that owns resources by composing existing RAII types needs no destructor, copy, or move. The compiler generates correct ones (Core Guidelines C.20).

```cpp
class Session {
public:
    Session(std::unique_ptr<Connection> conn, std::vector<std::byte> buffer)
        : conn_(std::move(conn)), buffer_(std::move(buffer)) {}
private:
    std::unique_ptr<Connection> conn_;
    std::vector<std::byte> buffer_;
};  // move-only because unique_ptr is; destructor releases both
```

**Review signal:** a hand-written destructor in a class that is not a low-level resource wrapper usually means ownership is expressed with raw pointers. Fix the members, then delete the destructor.

## Rule of Five, Only in Resource Wrappers

If a class must define any of destructor / copy ctor / copy assign / move ctor / move assign, it must consciously define or `= delete` all five (C.21). Such classes should wrap **exactly one** resource and do nothing else.

A canonical handle:

```cpp
class Socket {
public:
    explicit Socket(int fd = -1) noexcept : fd_(fd) {}
    ~Socket() noexcept { close_if_valid(); }

    Socket(const Socket&) = delete;
    Socket& operator=(const Socket&) = delete;

    Socket(Socket&& other) noexcept : fd_(std::exchange(other.fd_, -1)) {}
    Socket& operator=(Socket&& other) noexcept {
        if (this != &other) {
            close_if_valid();
            fd_ = std::exchange(other.fd_, -1);
        }
        return *this;
    }

    [[nodiscard]] int get() const noexcept { return fd_; }

private:
    void close_if_valid() noexcept {
        if (fd_ >= 0) {
            ::close(fd_);
            fd_ = -1;
        }
    }
    int fd_ = -1;
};
```

Invariants to check in every handle:

- Each live OS handle has exactly one owner.
- After a move, the source no longer owns anything and is safe to destroy and to assign to.
- The destructor can always run safely, including on a moved-from object.
- Move operations are `noexcept`. `std::vector` uses `std::move_if_noexcept` during reallocation; a potentially-throwing (or un-annotated user-declared) move silently degrades to copies for copyable types, and loses the strong exception guarantee for move-only types (C.66).
- Copy is either deleted or deep. A defaulted copy of a raw handle is a double-close.

## Prefer `unique_ptr` With a Deleter Over a Hand-Written Handle

For pointer-shaped C handles, a deleter gives Rule of Zero for free:

```cpp
// Anti-pattern: fclose skipped on throw or early return.
void process() {
    FILE* f = std::fopen("data.bin", "rb");
    if (!f) throw std::runtime_error("open failed");
    parse(f);           // throws -> leak
    std::fclose(f);
}

// Positive
struct FileCloser {
    void operator()(std::FILE* f) const noexcept { std::fclose(f); }
};
using FilePtr = std::unique_ptr<std::FILE, FileCloser>;

FilePtr open_file(const char* path) {
    FilePtr f{std::fopen(path, "rb")};
    if (!f) throw std::system_error(errno, std::generic_category(), path);
    return f;
}

void process() {
    auto f = open_file("data.bin");
    parse(f.get());     // borrow only
}                       // fclose automatically
```

Notes:

- `unique_ptr` never calls its deleter on null, so the deleter does not need a null check.
- **Deleters must not throw.** A throwing deleter on the destruction path is undefined behavior / `std::terminate`. Handle and log errors inside.
- `unique_ptr<T, DeleterA>` and `unique_ptr<T, DeleterB>` are different types; `shared_ptr<T>` type-erases the deleter into the control block. Choose accordingly for API boundaries.
- Prefer a stateless function-object deleter over a function pointer (`unique_ptr<FILE, decltype(&fclose)>`): it keeps `sizeof(unique_ptr) == sizeof(T*)` and avoids calling through a pointer.
- Pair allocation and release exactly: `new`/`delete`, `new[]`/`delete[]` (use `unique_ptr<T[]>` or better `vector`), `lib_create`/`lib_destroy`. Freeing across module/ABI boundaries needs the allocating module's release function.

## C APIs That Fill `T**`

```cpp
// Anti-pattern: raw out-pointer, manual handoff, leak if anything between throws.
Decoder* raw = nullptr;
if (decoder_create(&raw) != 0) return error();
DecoderPtr d(raw);

// C++23: out_ptr resets the smart pointer with the result when the temporary dies.
DecoderPtr d;
if (decoder_create(std::out_ptr(d)) != 0) return error();
```

Use `std::inout_ptr` when the C API may replace an existing handle. Without C++23, keep the raw out-pointer confined to a single tiny adapter function that immediately wraps it.

## Scope Guards for One-Off Cleanup

For cleanup that is not a resource type (rolling back a partial mutation, restoring a flag), use a scope guard rather than duplicated cleanup on each exit path. Use the project's existing one (`absl::Cleanup`, `gsl::finally`, `folly::ScopeGuard`, `std::experimental::scope_exit`) rather than inventing another.

```cpp
state_.begin_batch();
auto end_batch = gsl::finally([&] { state_.end_batch(); });
apply_all(ops);   // may throw; end_batch still runs
```

## Locks and Threads Are Resources

- Never call `mutex.lock()`/`unlock()` by hand. Use `std::scoped_lock` (multiple mutexes, deadlock-free) or `std::unique_lock` (needs unlock/condvar).
- A joinable `std::thread` destroyed without `join()`/`detach()` calls `std::terminate`. In C++20 use `std::jthread`: its destructor requests stop and joins. Pre-C++20, wrap `std::thread` in a joining RAII type.
- `detach()` is almost always a lifetime bug: the thread outlives every object it references. Treat it as a blocking finding unless the thread provably touches only static-lifetime or owned-by-copy data.

## Two-Phase Init and "Zombie" Objects

```cpp
// Anti-pattern: object exists in an invalid state between ctor and init().
Database db;
if (!db.init(path)) { ... }
db.query(...);   // what if init was forgotten?

// Positive: construction establishes the invariant, or you get no object.
class Database {
public:
    static std::expected<Database, DbError> open(const std::filesystem::path& path);
private:
    explicit Database(Connection conn);   // only open() can construct
    Connection conn_;
};
```

If exceptions are banned, a static factory returning `std::expected`/`std::optional`/`absl::StatusOr` with a private constructor is the standard shape.

## Review Questions

- Does every resource enter an RAII owner at the line it is acquired?
- Does any non-wrapper class have a hand-written destructor or copy/move? Can members make it Rule of Zero?
- Does every resource wrapper define-or-delete all five, keep moves `noexcept`, and leave moved-from objects destructible?
- Any `lock()`/`unlock()` pair, un-joined `std::thread`, or `detach()`?
- Any deleter or destructor that can throw?
