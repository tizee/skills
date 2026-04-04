---
urls:
  - https://rust-lang.github.io/api-guidelines/flexibility.html
  - https://doc.rust-lang.org/std/borrow/enum.Cow.html
  - https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html
---

# Ownership & Borrowing

## Goals

- Make ownership and allocation decisions explicit in function signatures.
- Give callers control over when and whether data is cloned.
- Use `Cow` when a function genuinely needs borrowed-or-owned flexibility, not as a default.

## Guidance

- **If you need ownership, take ownership.** A function that will store or return owned data should accept owned types. Taking `&str` and immediately calling `.to_string()` inside hides the allocation from the caller.
- **If you only read, borrow.** Accept `&T` or `&str` / `&[T]` when the function does not need to keep the data.
- **Use `Cow` for genuine borrowed-or-owned flexibility.** `Cow` is appropriate when most calls can avoid allocation (borrowed path) but some callers need to pass owned data. If every caller always clones anyway, just take `String`.
- **Avoid `Cow` that immediately calls `into_owned`.** That defeats the purpose -- you pay the `Cow` complexity with none of the benefit. Take the owned type directly.
- **Watch for hidden clones in APIs.** A function taking `&T` that internally clones to store the value violates caller-controls-cloning. The API lies about its cost.

## Anti-Pattern: Hidden Clone

```rust
// Caller thinks this is cheap (takes a reference), but it allocates.
pub fn add_tag(tags: &mut Vec<String>, tag: &str) {
    tags.push(tag.to_string()); // hidden allocation
}
```

## Positive Pattern: Take Ownership

```rust
// Caller sees the ownership transfer and decides when to allocate.
pub fn add_tag(tags: &mut Vec<String>, tag: String) {
    tags.push(tag);
}
```

## Positive Pattern: Cow for Real Flexibility

```rust
use std::borrow::Cow;

// Most callers pass &str (zero-copy); some pass owned String.
pub fn add_tag(tags: &mut Vec<String>, tag: Cow<'_, str>) {
    tags.push(tag.into_owned());
}

// Typical usage:
add_tag(&mut tags, Cow::Borrowed("static-tag"));
add_tag(&mut tags, Cow::Owned(dynamic_string));
```

## Anti-Pattern: Cow That Always Owns

```rust
// Every call site builds an owned string, then wraps it in Cow.
// The Cow adds complexity without benefit.
fn process(input: Cow<'_, str>) -> String {
    let owned = input.into_owned(); // always clones or moves
    owned.to_uppercase()
}
```

Just take `String` or `&str` depending on whether you need ownership.

## Cow as a Performance Optimization

`Cow` shines in "usually borrow, occasionally own" hot paths. The core idea: defer allocation until you know mutation is actually needed. If the common case is pass-through, you avoid cloning entirely.

### String Processing: Normalize Only When Needed

```rust
use std::borrow::Cow;

/// Normalize a path by stripping trailing slashes.
/// Most paths are already clean -- avoid allocating for them.
fn normalize_path(path: &str) -> Cow<'_, str> {
    if path.ends_with('/') {
        // Rare case: allocate and modify.
        Cow::Owned(path.trim_end_matches('/').to_string())
    } else {
        // Common case: zero-copy, just borrow the input.
        Cow::Borrowed(path)
    }
}

// 90% of calls return Borrowed (zero allocation).
// 10% of calls return Owned (one allocation, only when truly needed).
```

This pattern applies anywhere a function transforms input conditionally: escaping special characters, case-normalizing, trimming whitespace, URL-encoding. The key property is that **most inputs pass through unchanged**.

### Return Cow From Functions, Not as Parameters

`Cow` is most valuable as a **return type** -- it lets the function decide at runtime whether to allocate. As a parameter type, it is often unnecessary because `&str` or `Into<String>` are simpler:

```rust
// Good: Cow as return type -- function decides borrow vs own.
fn escape_html(input: &str) -> Cow<'_, str> {
    if input.contains(['<', '>', '&', '"']) {
        Cow::Owned(input
            .replace('&', "&amp;")
            .replace('<', "&lt;")
            .replace('>', "&gt;")
            .replace('"', "&quot;"))
    } else {
        Cow::Borrowed(input) // no special chars, zero-copy
    }
}

// Questionable: Cow as parameter when Into<String> is simpler.
fn set_name(name: Cow<'_, str>) { /* ... */ }
// Better:
fn set_name(name: impl Into<String>) { /* ... */ }
```

### Cow in Collections: Shared Configuration

When many entries share the same default value, `Cow` avoids duplicating the default string:

```rust
use std::borrow::Cow;

struct Entry<'a> {
    label: Cow<'a, str>,
    value: i64,
}

fn build_entries(items: &[(Option<&str>, i64)]) -> Vec<Entry<'_>> {
    items.iter().map(|(label, value)| Entry {
        label: match label {
            Some(l) => Cow::Borrowed(*l),
            None => Cow::Borrowed("default"), // static str, no alloc
        },
        value: *value,
    }).collect()
}
```

### Cow With `to_mut()`: Lazy Clone-on-Write

`Cow::to_mut()` clones the borrowed data only on first mutable access -- subsequent mutations reuse the owned allocation:

```rust
use std::borrow::Cow;

fn maybe_append(base: &str, suffix: Option<&str>) -> Cow<'_, str> {
    let mut result = Cow::Borrowed(base);
    if let Some(s) = suffix {
        // First call to to_mut() clones base; second call reuses.
        result.to_mut().push_str(s);
    }
    result // Borrowed if suffix was None, Owned otherwise.
}
```

### When NOT to Use Cow

- **All callers always mutate.** Just take `String` or `Vec<T>`.
- **All callers always borrow.** Just take `&str` or `&[T]`.
- **The type is `Copy`.** `Cow<'_, i32>` is pointless -- copying an `i32` is cheaper than the `Cow` enum overhead.
- **You call `into_owned()` immediately.** The `Cow` wrapper adds complexity with no benefit.
- **The hot path is not allocation-sensitive.** If the function runs once at startup, the `Cow` complexity is not worth the zero-copy gain.

### Decision Guide

| Situation | Use |
| --- | --- |
| Function transforms input, most inputs unchanged | `Cow` return type |
| Function needs owned data, caller might have `&str` or `String` | `impl Into<String>` parameter |
| Collection where most entries share a common borrowed value | `Cow` field |
| Every caller will allocate anyway | `String` / `Vec<T>` directly |
| Only reading, never owning | `&str` / `&[T]` |

## Anti-Pattern: Cloning in Loops

```rust
// Each iteration clones the config -- O(n) allocations.
for item in &items {
    let cfg = config.clone(); // expensive if config is large
    process(item, &cfg);
}
```

If the loop body only reads config, borrow instead:

```rust
for item in &items {
    process(item, &config); // zero-copy
}
```

If mutation is needed per iteration, consider restructuring so only the changing parts are cloned.

## Lifetime Elision and Explicit Annotations

Rust elides lifetimes in common patterns: single reference parameter, or `&self`/`&mut self` with one other reference. When explicit annotations are needed:

- Use descriptive names (`'data`, `'conn`) when multiple lifetimes need distinction.
- Avoid overusing `'static` in generic bounds -- it often indicates a design that forces unnecessary ownership.
- Keep lifetime annotations minimal; if the compiler doesn't require them, removing them improves readability.

## Interior Mutability: Use With Care

`RefCell` and `Cell` allow mutation through shared references, but they shift borrow checking to runtime:

- `RefCell` panics on conflicting borrows at runtime.
- `Mutex` blocks or deadlocks if misused.

Prefer compile-time `&mut` access whenever possible. Reach for interior mutability only when the ownership structure genuinely prevents exclusive references (e.g., shared state in event-driven or graph-like structures).

## Detecting Ownership Smells

Look for these patterns during review:

- `.clone()` / `.to_string()` / `.to_owned()` inside a function that takes `&T` and stores or returns the owned form.
- `Cow` parameters where `into_owned()` is called unconditionally.
- Excessive `.clone()` to satisfy the borrow checker -- often signals a design that mixes read and write responsibilities.
- Cloning inside loops when borrowing would suffice.
- `'static` bounds where a shorter lifetime would work.
