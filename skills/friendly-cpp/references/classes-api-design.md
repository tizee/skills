---
urls:
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-class
  - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-interfaces
  - https://google.github.io/styleguide/cppguide.html#Classes
  - https://abseil.io/tips/
---

# Classes and API Design

A class exists to protect an invariant. If it has no invariant, it is a `struct` of public data. If it has one, every constructor establishes it, every public member preserves it, and no member exposes a way to break it.

## Struct or Class

- **Plain aggregate** (`struct`, public members, no invariant): config records, DTOs, results. Initialize with designated initializers (C++20) or brace-init. No getters/setters.
- **Class** (private data, invariant): constructors establish the invariant; members preserve it.

```cpp
// Anti-pattern: Java-style accessors around data with no invariant.
class Point {
public:
    int getX() const { return x_; }
    void setX(int x) { x_ = x; }
    int getY() const { return y_; }
    void setY(int y) { y_ = y; }
private:
    int x_, y_;          // also uninitialized
};

// Positive
struct Point {
    int x = 0;
    int y = 0;
};
```

A setter that validates nothing on a class with an invariant is worse: it is a hole in the invariant.

## Constructors

- Single-argument constructors and conversion operators are `explicit` unless implicit conversion is the point (`string_view` from `string`).
- Initialize every member: default member initializers (`int count_ = 0;`) plus the constructor initializer list. Members initialize in **declaration order**, not initializer-list order (`-Wreorder`).
- No work that can half-fail in a constructor without throwing. Without exceptions, use a static factory returning `expected`/`optional` (see [raii-resources.md](raii-resources.md)).
- Do not call virtual functions from constructors or destructors.
- Delegate between constructors or use default arguments rather than duplicating init logic.

## Const-Correctness

- Member functions that do not change observable state are `const`.
- Parameters not modified are `const&` (or by value for cheap types). `const` by-value parameters in declarations are noise; in definitions they are optional.
- Return `const&` to internal state only when lifetime is clearly tied to `*this`; otherwise return by value.
- `mutable` is for caches and mutexes only, never to cheat const.
- Do not `const_cast` away const to write. Writing to an originally-const object is UB.

## Inheritance and Polymorphism

- **Prefer composition.** Inherit only for genuine is-a with runtime polymorphism, or for mixin utilities like `enable_shared_from_this`.
- A base class used polymorphically (deleted via base pointer) has a `public virtual` destructor; otherwise a `protected` non-virtual one (C.35). Missing virtual destructor + `unique_ptr<Base>` owning a `Derived` = UB and leak.
- Mark overrides `override` (or `final`), never repeat `virtual` on overrides. `-Wsuggest-override` / `-Winconsistent-missing-override`.
- Polymorphic bases suppress public copy/move to prevent slicing (C.67): `= delete` them or make them `protected`.
- Keep hierarchies shallow (1-2 levels). A deep hierarchy of `BaseManager -> AbstractManager -> ManagerImpl` is an agent smell; replace with composition, `std::variant`, or a function object.
- An interface with one implementation and no test double is speculative; remove the interface.

```cpp
// Anti-pattern: no virtual destructor; deleting via base is UB.
struct Shape { virtual double area() const = 0; };
struct Circle : Shape { std::vector<double> samples; double area() const override; };
std::unique_ptr<Shape> s = std::make_unique<Circle>();   // ~Circle never runs

// Positive
class Shape {
public:
    virtual ~Shape() = default;
    virtual double area() const = 0;
protected:
    Shape() = default;
    Shape(const Shape&) = default;              // protected: no slicing from outside
    Shape& operator=(const Shape&) = default;
};
```

For a closed set of alternatives, `std::variant` + `std::visit` is often clearer than a hierarchy: exhaustiveness is checked, no heap, value semantics.

## Types That Carry Meaning

- `enum class` over plain `enum` or `#define` constants: scoped, no implicit int conversion.
- Strong types for units and IDs that are easy to mix up: `struct UserId { std::uint64_t value; };` rather than bare `uint64_t` for both user and order IDs.
- `std::optional<T>` for "maybe a value" instead of sentinel values (`-1`, empty string, null pointer used as "none").
- `std::variant` for sum types instead of a `type` field plus a `union` or a pile of nullable members.
- `bool` parameters that change behavior (`render(true, false)`) become an `enum class` or separate functions.
- `[[nodiscard]]` on functions whose result must not be ignored (results, handles, `empty()`-like queries).

## Interfaces

- Keep public surfaces small; free functions in the same namespace are part of the interface (and extend it without friendship).
- Parameters: at most ~4; otherwise pass a named options struct.
- Out-parameters only when an API contract forbids returning (C APIs); otherwise return values.
- Document preconditions, ownership, lifetime of returned borrows, thread-safety, and error behavior at the declaration.
- Hide implementation: pimpl (`std::unique_ptr<Impl>` with the destructor defined in the `.cpp`) for ABI stability or heavy headers. Do not pimpl everything by default.

## Singletons and Globals

- Mutable global state and singletons are hidden dependencies: untestable, order-dependent at startup/shutdown (static initialization order fiasco), and thread-unsafe by default.
- Pass dependencies explicitly (constructor injection). If a process-wide instance is truly needed, expose it through a function-local static (initialization is thread-safe) and keep it immutable after startup.
- Non-trivially-destructible globals are destroyed at exit in reverse order, possibly while other threads still use them. Google style bans them for this reason. Prefer `constexpr` data, or an intentionally leaked function-local static with a comment:

```cpp
Registry& registry() {
    static auto* r = new Registry();   // intentionally leaked: avoids exit-time destruction races
    return *r;
}
```

## Operators

- Overload operators only with their conventional meaning. `operator==` implies `operator!=`; in C++20 `= default` `operator<=>` and `operator==`.
- Symmetric binary operators are non-member (possibly `friend`) so both operands convert equally.

## Review Questions

- Does each class have an invariant? If not, is it a plain struct without accessors?
- Are all members initialized? Single-arg constructors `explicit`?
- Any polymorphic base without a virtual (or protected) destructor? Any missing `override`? Any slicing copy of a polymorphic type?
- Any hierarchy deeper than 2, or an interface with one implementation and no test seam?
- Any sentinel values, bool flag parameters, or plain enums where `optional`/`enum class`/strong types fit?
- Any mutable global, singleton, or non-trivially-destructible static?
