---
urls:
  - https://doc.rust-lang.org/nomicon/
  - https://std-dev-guide.rust-lang.org/policy/safety-comments.html
  - https://rust-lang.github.io/api-guidelines/documentation.html
---

# Unsafe Discipline

## Goals

- Keep unsafe usage minimal, documented, and contained behind safe APIs.
- Use module boundaries and privacy as the primary tool for soundness containment.
- Ensure safe callers can never trigger undefined behavior.

## Guidance

- **Unsafe correctness is non-local.** The Rustonomicon emphasizes that whether an unsafe block is sound depends on invariants maintained by surrounding safe code. A correct unsafe block today can become UB if someone later makes a private field public. This is why containment matters more than the unsafe block itself.
- **Contain unsafe behind module boundaries with private fields.** The module boundary + field privacy is your primary defense. If invariant-preserving fields are `pub`, any code can break your safety contract. Keep unsafe-relevant state private and expose only safe operations.
- **Every `unsafe` block needs a `// SAFETY:` comment.** The comment should explain which invariants are relied upon and why they hold at this point. This is not bureaucracy -- it is the proof obligation that makes review possible.
- **Every `pub unsafe fn` needs a `# Safety` doc section.** This documents the caller's obligations. Without it, callers cannot know how to use the function correctly.
- **Scope unsafe operations tightly.** Even inside an `unsafe fn`, wrap individual unsafe operations in `unsafe {}` blocks (enabled by `#[deny(unsafe_op_in_unsafe_fn)]`) so each operation gets its own safety justification.
- **Prefer safe alternatives.** Before reaching for unsafe, check if a safe abstraction exists (e.g., `slice::get` instead of pointer arithmetic, `MaybeUninit` instead of `mem::uninitialized`).

## Anti-Pattern: Unsafe Without Reasoning

```rust
pub fn read_at(p: *const u8, i: usize) -> u8 {
    unsafe { *p.add(i) } // no explanation of why this is safe
}
```

## Positive Pattern: Documented Unsafe With Bounds Check

```rust
/// Reads a byte at index `i` from a buffer of `len` bytes.
///
/// # Safety
///
/// `p` must point to at least `len` allocated bytes.
pub unsafe fn read_at(p: *const u8, i: usize, len: usize) -> u8 {
    assert!(i < len, "index {i} out of bounds for length {len}");
    // SAFETY: caller guarantees `p` points to `len` bytes; we checked `i < len`.
    unsafe { *p.add(i) }
}
```

## Anti-Pattern: Leaky Containment

```rust
pub struct RingBuffer {
    pub buf: *mut u8,  // public! anyone can corrupt invariants
    pub len: usize,
    pub cap: usize,
}
```

## Positive Pattern: Private Invariants, Safe API

```rust
pub struct RingBuffer {
    buf: *mut u8,   // private: only this module can touch these
    len: usize,
    cap: usize,
}

impl RingBuffer {
    pub fn push(&mut self, byte: u8) {
        assert!(self.len < self.cap);
        // SAFETY: len < cap guarantees buf.add(len) is within allocation.
        unsafe { self.buf.add(self.len).write(byte) }
        self.len += 1;
    }
}
```

## Lint Enforcement

Use crate-level attributes to enforce documentation discipline:

```rust
#![deny(unsafe_op_in_unsafe_fn)]
#![deny(clippy::undocumented_unsafe_blocks)]
#![deny(clippy::missing_safety_doc)]
```

httparse is a good real-world model of this approach: strict lint denial at crate root, unsafe contained in a submodule with documented invariants.

## Challenge Unsafe Before Writing It

Research suggests 77% of `unsafe` usage stems from unawareness of safe alternatives. Before writing unsafe, exhaust these options:

- Restructure code to satisfy the borrow checker.
- Use interior mutability (`RefCell`, `Cell`, `Mutex`) when compile-time checking is too restrictive.
- Use `Rc`/`Arc` for shared ownership instead of raw pointers.
- Check if a safe abstraction exists in `std` or a well-vetted crate.

Only 23% of developers report being always certain their unsafe encapsulation is correct. When unsafe is unavoidable, require thorough testing, multiple review rounds, and Miri validation.

## Miri for Unsafe Validation

Miri interprets Rust's MIR to detect undefined behavior at runtime: use-after-free, data races, stacked borrows violations, invalid pointer operations. It runs slower than native execution but catches UB that tests alone miss.

```bash
# Run tests under Miri
cargo +nightly miri test

# Run a specific binary
cargo +nightly miri run
```

Integrate Miri into CI for any crate containing `unsafe` blocks. It is the closest thing to a soundness proof you can get without formal verification.

## FFI and Raw Pointers

When bridging to C via FFI:

- **Check raw pointers for null before dereference.** Use `as_ref()` / `as_mut()` which return `Option`, forcing explicit null handling.
- **Document lifetime expectations across the FFI boundary.** C does not track lifetimes; the Rust side must enforce them.
- **Use `CStr` / `CString` for string interop.** Never assume a C `char*` is valid UTF-8.
- **Wrap FFI types in safe Rust abstractions** with proper `Drop` implementations for cleanup.
