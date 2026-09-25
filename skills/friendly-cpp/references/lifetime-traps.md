---
urls:
  - https://eel.is/c++draft/basic.life
  - https://eel.is/c++draft/string.view
  - https://eel.is/c++draft/views.span
  - https://clang.llvm.org/docs/LifetimeSafety.html
  - https://llvm.org/docs/ProgrammersManual.html#passing-strings-the-stringref-and-twine-classes
  - https://github.com/facebook/rocksdb/blob/main/include/rocksdb/file_system.h
  - https://v8.dev/blog/retrofitting-temporal-memory-safety-on-c%2B%2B
---

# Lifetime Traps

With RAII in place, explicit `delete` bugs mostly disappear. What remains is **temporal safety of borrows**: views, temporaries, callbacks, container invalidation, and cross-thread references. V8 and Chromium still need hardening, sanitizers, and static analysis for exactly this class; the language alone does not prevent it.

Every borrow must answer: **who owns the storage, and what guarantees it outlives this use?**

## Dangling Views

`std::string_view` and `std::span` only *refer to* storage. They never keep it alive.

```cpp
// Anti-pattern: returns a view into a destroyed local.
std::string_view make_name() {
    std::string s = "engine";
    return s;
}

// Anti-pattern: temporary dies at the end of the full-expression.
std::string_view v = std::string("temporary");
std::string_view k = get_config().name();   // if get_config() returns by value
std::span<const int> s = std::vector<int>{1, 2, 3};

// Positive: return an owning value.
std::string make_name() { return "engine"; }

// Positive: return a borrow into a longer-lived owner, with the contract stated.
// Returned view is valid while cfg is alive and unmodified.
std::string_view name(const Config& cfg) { return cfg.name(); }
```

Rules:

- `string_view`/`span` are **parameter types** by default. As return types, they need a stated owner. As fields, they need a lifetime comment (see [ownership-lifetime.md](ownership-lifetime.md)).
- `std::string_view` is not NUL-terminated. Passing `sv.data()` to a C API expecting `const char*` is a bug unless the origin guarantees termination. Convert to `std::string` at the C boundary.
- LLVM's rule for `StringRef`/`function_ref` generalizes: store a view only when you can prove the external storage's lifetime; otherwise store the owning type (`std::string`, `std::vector`, `std::function`).

## Temporaries and `auto`

```cpp
// Anti-pattern: range-for over a member of a temporary (fixed only in C++23, P2718).
for (auto& x : make_holder().items()) { ... }   // holder destroyed before loop body

// Anti-pattern: reference to member of a temporary.
const auto& first = get_vector().front();      // vector destroyed; first dangles

// Positive: name the owner.
auto holder = make_holder();
for (auto& x : holder.items()) { ... }
```

Lifetime extension applies only when a temporary binds **directly** to a `const&`/`&&` local. It does not propagate through member function calls, `std::min`/`std::max` returning references, or ternaries that yield references.

```cpp
const int& m = std::max(a + 1, b);   // dangles: max returns a reference to a temporary
int m = std::max(a + 1, b);          // positive: copy the value
```

## Container Invalidation

Pointers, references, and iterators into a container can be invalidated by mutation:

| Container | Invalidated by |
| --- | --- |
| `vector`, `string` | any growth past capacity (all), insert/erase (at and after position) |
| `deque` | insert/erase in the middle (all); push at ends (iterators, not references) |
| `unordered_map/set` | rehash (iterators; references stay valid), erase (the erased element) |
| `map`, `set`, `list` | only erase of that element |

```cpp
// Anti-pattern: reference into a vector that grows.
auto& first = items.front();
items.push_back(make_item());   // may reallocate
use(first);                     // UAF

// Anti-pattern: erase while iterating.
for (auto it = v.begin(); it != v.end(); ++it)
    if (bad(*it)) v.erase(it);  // it invalidated

// Positive
std::erase_if(v, bad);          // C++20; pre-C++20: v.erase(std::remove_if(...), v.end())
```

Objects that store element pointers/iterators must document the mutation contract. Otherwise store an index or key, choose an address-stable structure (`std::deque` end-pushes, `std::list`, node-based maps, `vector<unique_ptr<T>>`), or separate the build phase from the read phase.

## Lambda Captures

A lambda that outlives its scope is a stored borrow.

```cpp
// Anti-pattern: [&] or [this] escaping into an async context.
void Client::fetch() {
    std::string url = build_url();
    executor_.post([&] { http_get(url); });      // url destroyed before task runs
    timer_.on_fire([this] { refresh(); });       // Client may be destroyed first
}

// Positive: capture by value what the task needs; promote weakly for self.
void Client::fetch() {
    executor_.post([url = build_url()] { http_get(url); });
    timer_.on_fire([weak = weak_from_this()] {
        if (auto self = weak.lock()) self->refresh();
    });
}
```

- `[&]` is fine for lambdas that run synchronously within the scope (`std::sort` comparators, `std::for_each`, immediately-invoked).
- `[&]` or `[this]` in anything stored, posted, passed to a thread, or registered as a callback is a blocking finding until a lifetime proof is written down.
- `[=]` implicitly captures `this` (deprecated in C++20) -- it is **not** a by-value copy of the object. Prefer explicit capture lists.
- If the object cannot be `shared_ptr`-owned, alternatives: cancel/unregister the callback in the destructor (the registry must support this synchronously), or give the callback a cancellation token checked under the registry's lock.

## Non-Owning Fields

```cpp
class Parser {
    std::string_view input_;   // lifetime-sensitive field
};
```

For each such field, answer: who owns the storage? Does the owner provably outlive `Parser`? Can a move or reallocation change the address? If any answer is unclear, store `std::string input_;`, or restructure so the owner is a member of the same object or a strictly enclosing scope.

Good APIs put the lifetime source in the contract. RocksDB's `RandomAccessFile::Read` documents that the returned `Slice` may point into the caller-provided `scratch` buffer, so `scratch` must stay alive while `result` is used.

## Moved-From Objects

After `std::move(x)`, `x` is valid but unspecified (for standard types). Reading its value is a logic bug; only assign to it or destroy it. clang-tidy `bugprone-use-after-move` catches most cases.

## `this` During Construction and Destruction

- Virtual calls in constructors/destructors dispatch to the current class, not the derived one.
- Registering `this` with an external registry in a constructor exposes a half-built object to other threads; unregistering in the destructor happens after derived members are already destroyed. Use a factory that registers after construction and an explicit `stop()` before destruction.

## Anti-Pattern -> Refactor Table

| Anti-pattern | Mechanism | Refactor |
| --- | --- | --- |
| `string_view`/`span`/`T*` to a temporary or local | owner already dead | return/store an owning value, or extend the real owner |
| Reference/iterator held across container mutation | reallocation / rehash / erase | index/key, stable container, or phase separation |
| `[&]`/`[this]` in a stored or async callback | captured scope/object dies first | capture by value, move ownership in, or `weak_from_this()` + `lock()` |
| Range-for over `temp().member()` | temporary destroyed before body (pre-C++23) | name the temporary |
| `const T& r = f(temp)` where `f` returns a reference | no lifetime extension through calls | copy the value |
| `sv.data()` passed to a C string API | not NUL-terminated | `std::string(sv).c_str()` at the boundary |
| Reading a moved-from object | unspecified state | reassign before use, or don't move |

## Review Questions

- Every returned or stored view/pointer/reference/iterator: owner named, outlives the holder?
- Any view built from a temporary, a by-value return, or a local?
- Any container mutated while a pointer/reference/iterator into it is live?
- Any `[&]`, `[this]`, or `[=]` lambda that escapes its scope?
- Any use after `std::move`?
