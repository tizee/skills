---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-resource
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rf-conventional
  - https://google.github.io/styleguide/cppguide.html#Ownership_and_Smart_Pointers
  - https://eel.is/c++draft/smartptr
---

# Ownership and Borrowing

The single most useful review habit: read every signature and field as an ownership statement. If the type does not say who owns, the code is under-specified.

## Ownership Vocabulary

Adopt one vocabulary project-wide and read every API through it:

| Type in an API | Meaning |
| --- | --- |
| `T` / `const T` | Value. The function gets its own object. |
| `T&` / `const T&` | Non-null borrow, normally valid only for the call. |
| `T*` / `const T*` | Nullable borrow. Never owning. |
| `std::span<T>` (C++20) | Borrow of a contiguous range, with its size. Replaces `T* + size_t`. |
| `std::string_view` | Borrow of character data. |
| `std::unique_ptr<T>` | Transfer of exclusive ownership. |
| `std::shared_ptr<T>` | Acquire / share lifetime ownership. |
| `std::weak_ptr<T>` | Observe a shared lifetime without extending it. |
| `T&&` | Sink: the callee may steal the contents. |

Owning edges decide lifetime; borrow edges never change it; weak edges break cycles in shared graphs. Draw the graph for any non-trivial subsystem before reviewing its bodies.

```text
Factory --creates--> unique_ptr<T> --std::move--> Service  (owns)
Service - - borrow T& / T* / span - - > Observer            (does not extend lifetime)
Service --only with true shared lifetime--> shared_ptr<T> --> control block --> T
weak_ptr<T> - - observes - - > control block; lock() -> temporary shared_ptr<T>
```

## Parameters: Smart Pointers Only When Lifetime Is the Point

A smart pointer in a parameter list claims the function participates in lifetime. If it only uses the object, pass the object (Core Guidelines R.30-R.37, F.7).

| Intent | Signature |
| --- | --- |
| Read an object | `void f(const Widget&)` |
| Modify an object | `void f(Widget&)` |
| Object may be absent | `void f(const Widget*)` or `std::optional<std::reference_wrapper<...>>` sparingly |
| Take ownership | `void f(std::unique_ptr<Widget>)` (by value) |
| Reseat the caller's pointer | `void f(std::unique_ptr<Widget>&)` (rare) |
| Keep a share of lifetime | `void f(std::shared_ptr<Widget>)` (by value, then `std::move` into storage) |
| Maybe keep a share | `void f(const std::shared_ptr<Widget>&)` (rare) |
| Cheap-to-copy input (<= 2-3 words) | by value: `int`, `string_view`, `span`, iterators |
| Input you will store | by value, then `std::move` into the member |

```cpp
// Anti-pattern: implies shared lifetime, forces callers to heap-allocate,
// and pays an atomic increment per call.
void render(std::shared_ptr<Scene> scene);

// Positive: pure borrow for the duration of the call.
void render(const Scene& scene);
```

```cpp
// Sink parameter: take by value, move into place. Callers pass lvalues (copy)
// or rvalues (move) with one overload.
class Logger {
public:
    explicit Logger(std::string prefix) : prefix_(std::move(prefix)) {}
private:
    std::string prefix_;
};
```

## Returns

- Return values, not out-parameters. RVO/NRVO and move make this cheap; `std::optional`, `std::expected`, structs, or `std::pair`/`tuple` (prefer named structs) handle multiple results.
- Factories return `std::unique_ptr<T>` (or `T` by value). Callers who need shared ownership can convert: `std::shared_ptr<T> s = make_widget();`.
- Never return a reference, pointer, `string_view`, or `span` into a local or a temporary. Returning a borrow into `*this` or a parameter is fine only when the contract states "valid while X lives".

## Fields

- An owning field is a value, a container, a `unique_ptr`, or (justified) a `shared_ptr`.
- A non-owning field (`T*`, `T&`, `string_view`, `span`, iterator) is a **lifetime coupling**. Every one needs, at the declaration, a comment naming the owner and why it outlives `*this`. If that comment cannot be written honestly, store a value instead.
- Prefer `T*` over `T&` for non-owning fields: reference members make the class non-assignable and cannot be reseated. Chromium goes further and uses `raw_ptr<T>`/`raw_ref<T>` for fields to harden UAF -- the owner/lifetime contract must still exist.

```cpp
class Parser {
public:
    // input is borrowed and must outlive this Parser.
    explicit Parser(std::string_view input) : input_(input) {}
private:
    // Borrowed. Owner: the std::string in parse_document(), which constructs,
    // uses, and destroys this Parser within one scope.
    std::string_view input_;
};
```

## Explicit Allocation Goes Straight Into an Owner

- No `new`/`delete` in business code. Use `std::make_unique`, `std::make_shared`, containers, or a dedicated RAII wrapper.
- If `new` is unavoidable (private constructor with a friend factory, placement new in an allocator), the result enters an owner **in the same expression** (Core Guidelines R.11-R.13).
- `malloc`/`free` belong only in C-interop adapters wrapped by a `unique_ptr` with a deleter.
- `.release()` is rare and local: the released pointer goes immediately into another owner-taking API on the same line or the next. With C++23, prefer `std::out_ptr`/`std::inout_ptr` for C APIs taking `T**`.

```cpp
// Anti-pattern: two allocations in one full-expression -- pre-C++17 leak risk,
// and the raw new is unreadable ownership regardless.
process(std::shared_ptr<A>(new A), std::shared_ptr<B>(new B));

// Positive
process(std::make_shared<A>(), std::make_shared<B>());
```

## Review Questions

- Can you point to the owner of every heap object and handle from its type alone?
- Does every smart-pointer parameter actually transfer or share lifetime?
- Does every stored non-owning pointer/view/reference name its owner and prove it outlives the holder?
- Are `new`, `delete`, `malloc`, `free`, `.release()` absent outside low-level, commented adapters?
