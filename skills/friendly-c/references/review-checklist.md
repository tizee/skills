---
urls:
  - https://spinroot.com/gerard/pdf/P10.pdf
  - https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard
---

# Review Checklist

Quick-reference questions for reviewing C. Not every question applies to every change -- pick the ones relevant to the diff. Work top-down: a correctness defect outranks every structural finding below it.

## Correctness and Undefined Behavior

- Is every fallible call's return value checked, including `snprintf`, `fclose`, `write`, and every allocation?
- Can any signed arithmetic overflow? Is any overflow check written *after* the operation (itself UB)?
- Does any shift use a count >= the type width, or left-shift a signed value into the sign bit?
- Is any `size_t` subtraction able to wrap (`len - 1` with `len == 0`)?
- Does any comparison mix signed and unsigned?
- Is any pointer cast to a more strictly aligned type, or punned without `memcpy`?
- Is `memcpy` ever called with a possibly-`NULL` pointer, or with overlapping regions?
- Is any object read before it is initialized?
- Is any variable modified twice without a sequence point, or is any side effect inside a condition or argument list?
- Does any buffer write lack a bound? Any `strcpy`/`strcat`/`sprintf`? Is `strncpy` used where NUL termination is assumed?
- Is `snprintf` truncation detected (`ret >= sizeof buf`)?
- Are format specifiers matched to argument types (`%zu` for `size_t`, `PRId64` for `int64_t`)?

## Memory and Resources

- Does every `_create` have exactly one `_destroy`, and does `_destroy` accept `NULL`?
- Is every allocation size computed as `count * sizeof *p`, with overflow checked before the call?
- Is `realloc`'s result assigned to a temporary, so a failure does not leak the original?
- Is every acquired resource released on every failure path, next to its acquisition?
- Does any `goto` appear? If so: does its label do more than return, and is there a comment justifying it?
- Does `MODULE_TRY` appear in any function that acquires something? (Banned.)
- Is the ownership of every pointer parameter and return value stated in the contract comment?
- After a failure, is the object's state stated in the contract (strong guarantee preferred) and does the code deliver it?
- Are freed pointers set to `NULL` when they remain reachable?

## Error Handling

- Does every fallible function return the module's status enum, with `0` as a named success?
- Does any function return `bool` when it can fail more than one way, or use a valid value as a failure sentinel?
- How many lines produce each error value? Reduce toward one.
- Does anything below the top of the call chain log, or convert a status to a different vocabulary without an adapter?
- Are libc/errno conventions confined to adapter functions?

## Functions and Control Flow

- Any function over 40 lines, or nested deeper than 2?
- Any contract comment containing "and"? Split the function.
- Is every function purely an orchestrator, a leaf, or an adapter -- never a mix of plan and arithmetic?
- Any helper whose most honest name just paraphrases its body? Inline it.
- Any parameter list past 4? Any parameter order violating context, outputs, inputs? Any buffer separated from its length?
- Any `static` local that is not a `static const` table?
- Any loop without a statically evident upper bound, or without a nonterminating marker?
- Any recursion, direct or indirect?
- Any loop body over 10 lines that should be a named function?
- Does every `switch` have a `default` and end every case in `break` or an explicit `/* fallthrough */`?

## Boundaries and Assertions

- Does every public entry point validate its arguments exactly once, returning `ERR_ARG`?
- Do internal helpers re-validate instead of asserting?
- Does every state-mutating leaf assert at least one invariant?
- Is any `assert` applied to data from outside the process? (Must be a validated status instead.)
- Does any `assert` contain a side effect? (`NDEBUG` deletes it.)
- Could any runtime check be a `static_assert` instead?

## Types and Data

- Fixed-width types used throughout, `size_t` for sizes and indices?
- `const` on every pointer parameter not written through?
- Is every variable initialized at declaration, and declared at its first valid value?
- Does any struct initialization rely on field order instead of designated initializers?
- Does every union carry a tag in the same struct?
- Any dereference chain deeper than one level (`a->b->c`)?
- Any function pointer outside a `static const` dispatch table?
- Any `if`/`else if` chain that is really a lookup table?
- Any typedef'd pointer type?

## Naming and Constants

- Any literal other than `0` or `1` in logic? Name it.
- Does every constant have exactly one definition site, with units in the name?
- Are derived constants computed rather than restated?
- Does every external symbol carry the module prefix? Do statics carry it too?
- Any abbreviation outside `buf`, `len`, `ctx`, `cfg`, `idx`?
- Any negated predicate (`is_not_ready`)? Any `_create` paired with `_deinit` or similar mismatched lifetime vocabulary?

## File and Header Structure

- Does the `.c` file follow the order: file comment, includes, constants, types, static prototypes, public definitions, static definitions?
- Does every static function have a prototype at the top with a contract comment?
- Does the header expose only what callers need -- no bodies, no variables, guard present?
- Does any file rely on a transitive include?
- Any commented-out code? Any comment restating *what* instead of *why*?

## Duplication

- Is any logic pasted twice? Any mutation sequence written in two branches?
- Is any string literal repeated?
- Would adding the next variant (a new cell type, a new verb, a new error) require editing more than one place?

## Macros

- Is every macro one that a `static inline` function could not replace?
- Are all arguments and the whole body parenthesized? Multi-statement bodies in `do { } while (0)`?
- Does any macro evaluate an argument twice, or contain `return`/`goto`/`break`/`continue` (other than the one sanctioned `MODULE_TRY`)?
- Is any `#ifdef` inside a function body where a per-platform file would be clearer?

## Build and Tests

- Does it compile clean under `-Wall -Wextra -Werror -Wconversion -Wshadow`?
- Did the test suite run under ASan+UBSan?
- Does every named error value have a test that produces it?
- Do tests cover the boundaries: 0, 1, capacity-1, capacity, capacity+1?
- Does any new parser of external bytes have a fuzz target?
- Do the tests themselves follow these rules (named constants, checked calls)?

## Final Gate

- Does the change stay within the requested scope, or has a fix grown into a header change?
- Is every deviation from these rules commented at the deviation site, naming the constraint?
- Were any required checks skipped? Say which command did not run rather than claiming compliance.
