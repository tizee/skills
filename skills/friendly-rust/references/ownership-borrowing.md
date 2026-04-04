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

## Detecting Ownership Smells

Look for these patterns during review:

- `.clone()` / `.to_string()` / `.to_owned()` inside a function that takes `&T` and stores or returns the owned form.
- `Cow` parameters where `into_owned()` is called unconditionally.
- Excessive `.clone()` to satisfy the borrow checker -- often signals a design that mixes read and write responsibilities.
