---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines
  - https://google.github.io/styleguide/cppguide.html
  - https://eel.is/c++draft/basic.life
---

# Core Principles

## Goals

- Every resource has exactly one visible owner, and its release point can be read from the code.
- Every non-owning reference can answer "who guarantees this is still alive?"
- Invalid states are unrepresentable, or at least rejected at construction.
- A reviewer can understand a function without loading the rest of the program.

## The Project Baseline in One Sentence

> **Value semantics first; when a heap object is needed, default to unique ownership; shared ownership requires an explicit reason; every non-owning pointer is a borrow; every resource is wrapped in an RAII object; any borrow that crosses a scope, a thread, or a callback must re-prove its lifetime.**

This is the C++ Core Guidelines resource model (R.1, R.3, R.20-R.24) and Google's "prefer a single, fixed owner" rule, compressed.

## Why Lifetime Is a Type-Design Problem

The standard says an object may only be accessed normally while its lifetime has begun and not ended. Destruction, storage release, or storage reuse ends it; touching it afterwards through an old pointer or reference is, in most cases, undefined behavior ([basic.life]). RAII turns that language rule into an engineering tool: **bind the resource's lifetime to an object's lifetime**, and the compiler inserts the release on every path, including exceptions and early returns.

So the question "is this memory-safe?" becomes "do the types express who owns what?" If they do, most bugs are structurally impossible. If they do not, no amount of careful `delete` placement will survive the next refactor.

## Principles

- **Values before pointers.** A member `Config cfg_;` beats `std::unique_ptr<Config> cfg_;`, which beats `Config* cfg_;` (owning). Reach for the heap only for polymorphism, size unknown at compile time, lifetime that must outlive the scope, or address stability.
- **Owners are types, not comments.** `unique_ptr`, `shared_ptr`, containers, and RAII handles own. Raw `T*` and `T&` never own. A raw owning pointer in business code is a blocking defect.
- **Borrows are short by default.** A `T&`/`T*`/`string_view`/`span` parameter is valid for the call. Storing one beyond the call is a lifetime coupling that must be documented and justified.
- **Rule of Zero.** Compose existing RAII types so the compiler writes the destructor, copy, and move. Hand-written special members are for the few classes that directly wrap a raw resource.
- **Fail at construction.** A constructor either establishes the class invariant or throws / is replaced by a factory returning `expected`/`optional`. No `init()` after construction, no half-built objects.
- **Say it in the signature.** Const-correctness, `explicit`, `[[nodiscard]]`, `noexcept`, `enum class`, and strong types carry intent the compiler can check. Comments cannot be checked.
- **Boring code wins.** Agents and humans alike over-engineer: deep hierarchies, template metaprogramming, singletons, managers of managers. The simplest code that makes ownership obvious is the target.
- **Measure before optimizing.** `shared_ptr` refcount contention, allocator swaps, hazard pointers, intrusive refcounts are all legitimate -- after a profile proves the hot path.

## Anti-Pattern

Ownership hidden in raw pointers and manual cleanup:

```cpp
class Pipeline {
public:
    Pipeline() : decoder_(new Decoder), buf_(new char[4096]) {}
    ~Pipeline() { delete decoder_; delete[] buf_; }   // copy = double free
    void run() {
        Frame* f = decoder_->next();                  // owned? borrowed?
        if (!f->valid()) return;                      // leaks f if owned
        process(f);
        delete f;                                     // skipped on throw
    }
private:
    Decoder* decoder_;
    char* buf_;
};
```

Four questions, zero answers visible in types: copying `Pipeline` double-frees, `Frame*` ownership is guesswork, early return and exceptions leak.

## Positive Pattern

```cpp
class Pipeline {
public:
    void run() {
        std::unique_ptr<Frame> f = decoder_.next();   // caller owns, by type
        if (!f->valid()) return;                      // released automatically
        process(*f);                                  // borrow for the call
    }
private:
    Decoder decoder_;                                 // value member
    std::vector<char> buf_ = std::vector<char>(kBufferBytes);
};                                                    // Rule of Zero: no dtor, copy/move correct or deleted by members
```
