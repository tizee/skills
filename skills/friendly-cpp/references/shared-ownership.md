---
urls:
  - https://eel.is/c++draft/util.smartptr.shared
  - https://eel.is/c++draft/util.smartptr.weak
  - https://eel.is/c++draft/util.smartptr.enab
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rr-unique
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rr-weak_ptr
  - https://google.github.io/styleguide/cppguide.html#Ownership_and_Smart_Pointers
  - https://www.boost.org/libs/smart_ptr
  - https://github.com/facebook/folly/blob/main/folly/docs/Hazptr.md
---

# Shared Ownership

`std::shared_ptr` is the most over-used type in agent-written C++. It looks like "safe memory management", but it widens lifetimes, hides the release point, introduces cycles, and makes destruction thread non-deterministic. It is correct only when **several independent entities may each decide the object must keep living**.

## When `shared_ptr` Is Justified

The PR (or a comment at the declaration) should name the independent owners. Legitimate cases:

- An async task and its initiator both need the object alive, and either may finish first.
- Several long-lived components hold the same **immutable** configuration / snapshot.
- A graph node genuinely kept alive by multiple roots.

If you cannot name at least two independent owners with independent lifetimes, use `unique_ptr` or a value.

```cpp
// Anti-pattern: no sharing exists.
void calculate() {
    auto p = std::make_shared<BigObject>();
    p->run();
}

// Positive
void calculate() {
    BigObject obj;          // or make_unique if it must be on the heap
    obj.run();
}
```

## Compare the Three Smart Pointers

| Property | `unique_ptr<T>` | `shared_ptr<T>` | `weak_ptr<T>` |
| --- | --- | --- | --- |
| Owns | exclusively | shared | observes the ownership group |
| Copy | no | yes, adds an owner | yes |
| Move | yes, source becomes null | yes, source becomes null | yes |
| Extends `T` lifetime | yes | yes | no |
| Release point | owner leaves scope / `reset` | last strong owner goes away | never destroys `T` |
| Custom deleter | part of the type | stored in control block | n/a |
| Concurrency | like any object | refcount is thread-safe; pointee is **not** | `lock()` acquires atomically |
| Typical bugs | leaked `.release()`, adopting a borrowed pointer | cycles, double control blocks, over-sharing, destructor on arbitrary thread | using without `lock()`, long-lived weak refs retaining storage |

## Prefer `make_unique` / `make_shared`

They keep `new` out of code and allocate once (for `make_shared`, object and control block usually together).

Trade-off to note in reviews: with co-allocation, when the last strong owner dies the object is destroyed but the storage is freed only when the last `weak_ptr` also dies. For very large objects observed by long-lived weak caches, measure whether this retention matters; if it does, construct with `std::shared_ptr<T>(new T(...))` in one place, or restructure the cache.

## Double Control Blocks

Ownership identity is the control block, not the address.

```cpp
// Anti-pattern: two independent ownership groups -> double delete.
Widget* raw = new Widget;
std::shared_ptr<Widget> a(raw);
std::shared_ptr<Widget> b(raw);

// Positive: create once, copy the owner.
auto a = std::make_shared<Widget>();
auto b = a;
```

The same bug in disguise:

```cpp
// Anti-pattern
class Worker {
public:
    std::shared_ptr<Worker> self() {
        return std::shared_ptr<Worker>(this);   // new control block -> double delete
    }
};

// Positive
class Worker : public std::enable_shared_from_this<Worker> {
public:
    std::shared_ptr<Worker> self() { return shared_from_this(); }
};
```

`shared_from_this()` requires the object already be owned by a `shared_ptr` (C++17: throws `bad_weak_ptr` otherwise). Never call it from a constructor. Make such classes constructible only via a factory returning `shared_ptr`.

## Cycles

Reference counting cannot collect cycles (Core Guidelines R.24). Common shapes: parent <-> child, subject <-> observer, object -> stored callback -> `shared_from_this()`, cache <-> entry.

```cpp
// Anti-pattern: Session -> callback_ -> shared_ptr<Session> -> Session. Never freed.
class Session : public std::enable_shared_from_this<Session> {
public:
    void start() {
        callback_ = [self = shared_from_this()] { self->poll(); };
    }
private:
    std::function<void()> callback_;
};

// Positive: the back edge is weak.
void Session::start() {
    callback_ = [weak = weak_from_this()] {
        if (auto self = weak.lock()) self->poll();
    };
}
```

For parent/child trees, the parent owns children (`unique_ptr` or `shared_ptr`), children hold a raw `Parent*` (if the parent strictly outlives them) or `weak_ptr<Parent>`.

Note: capturing `shared_from_this()` in a callback that is **posted to an executor and not stored by the object** is fine and often intended -- it keeps the object alive until the task runs. The bug is when the object itself stores that callback.

## Use `weak_ptr` Through `lock()` Only

```cpp
// Anti-pattern: check and acquire are separate; the last owner can vanish in between.
if (!weak.expired()) {
    auto p = weak.lock();
    p->use();              // p may be null
}

// Positive: single atomic acquisition, and p keeps the object alive for the whole use.
if (auto p = weak.lock()) {
    p->use();
}
```

Do not call `lock()` repeatedly in one operation -- lock once, hold the result.

## Aliasing Constructor

`std::shared_ptr<Member>(owner, &owner->member)` shares ownership of `owner` while pointing at a member. Legitimate, but a raw pointer extracted from it must not outlive `owner`'s group. Flag any code that extracts `.get()` from a shared pointer and stores it.

## `use_count()` Is a Diagnostic, Not Logic

Other threads can change the count at any moment. Any `if (p.use_count() == 1)` used for correctness is a race. `unique()` was removed in C++20 for this reason.

## Destruction Happens Wherever the Last Owner Dies

The last `shared_ptr` release may occur on any thread holding a copy -- a worker, a network callback, a real-time audio thread. Heavy destructors, thread-affine resources (GUI, GL context, thread-local handles) inside shared objects need an explicit teardown design (post the final release to the owning thread, or explicit `shutdown()` before release).

## Beyond `shared_ptr`

- **Intrusive refcounting** (`boost::intrusive_ptr`, Chromium `scoped_refptr`): refcount inside the object, pointer is word-sized. Justified by a framework/ABI requirement or a profile. You own memory ordering (`fetch_add` relaxed, `fetch_sub` acq_rel, delete at 1->0), delete policy, and cycle strategy; it still leaks cycles.
- **Hazard pointers / RCU / epoch reclamation** (Folly `hazptr`, C++26 `<hazard_pointer>`, `<rcu>`): for read-heavy concurrent data structures where refcount contention is proven hot. They protect reclamation, not the data inside.

Keep these at the data-structure layer. Spreading them into domain code costs more in review than it saves in atomics.

## Review Questions

- For each `shared_ptr`, who are the independent owners? No answer -> `unique_ptr` or value.
- Any `shared_ptr` constructed from a raw pointer that may already be owned? Any `shared_ptr(this)`?
- Draw the shared graph: any strong cycle? Is every back edge weak or raw-with-proof?
- Does every `weak_ptr` use go through a single `lock()` held for the whole use?
- Any `use_count()` in logic? Any stored `.get()` from a shared pointer?
- Is the destruction thread of each shared object acceptable?
