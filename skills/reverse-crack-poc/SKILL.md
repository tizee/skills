---
name: reverse-crack-poc
description: >-
  Guide a reverse-engineering proof-of-concept on a macOS crackme or local
  license-check binary for learning and interview preparation. Use this whenever
  the user is analyzing an app's authorization or license-gating module and wants
  to reconstruct its gating model, call chain, architecture differences (arm64,
  x86_64, or universal Mach-O), or validate a minimal patch with LLDB and code
  signing. Also use it for debugger-free keygen/patch automation, semantic
  signatures across app versions, fail-closed compatibility profiles, or
  diagnosing why a binary matcher broke after a minor update. Trigger on crackme,
  license-check PoC, Mach-O, IDA, LLDB, objc_msgSend, gating branches, patch
  validation, universal slices, keygen-me vs patch-me, semantic patch locators,
  or CTF-style binary patching — even when the user does not say "skill".
---

# Reverse-Crack PoC

A workbench for doing a structured reverse-engineering PoC on a macOS crackme / license-check binary.
The goal is learning and interview preparation: understand the authorization gating model,
the call chain, architecture differences, and how to validate a minimal patch.

## Scope and intent (read first)

It is an educational tool for understanding how local license checks are structured and why offline gating is inherently
breakable. The whole point is that the *methodology* transfers.

## The core idea (the through-line of every step)

Offline full-functionality clients are structurally invitations to be cracked:
when the auth logic runs entirely on the attacker's machine, the attacker holds
the lock, the key, and the blueprint of the lock's internals at once. Every step
of this methodology ultimately demonstrates one conclusion: **the value is not
in that boolean.** Keep this lens active — it is what an interviewer is really
probing for, and it is what separates "I flipped a byte" from "I understood the
trust-boundary error."

`references/crackme-license-check-ctf.md` is the deep methodology reference:
the six-ring skeleton, the L1→L8 difficulty ladder, patch-me vs keygen-me, and
the modern Apple Silicon friction (PAC, hardened runtime, FairPlay). Read it
when you need depth on any ring. `examples/demo-poc.md` is the canonical worked
write-up — the gold standard for the final deliverable's shape and reasoning
quality.

## How to work: lab notebook, then full write-up

Reverse engineering is iterative discovery, not a linear checklist. Work the way
a skilled human does: keep a **lean running analysis** — a lab notebook — that
you update as each hypothesis is confirmed or killed. You are not writing the
final document up front; you are accreting evidence toward the **Aha moment**
(the PoC goal is reached: the gating model is understood and the flag /
unlock is demonstrably achievable). Only then do you expand the notebook into
the full detailed write-up.

This two-phase shape matters because it mirrors how confidence actually builds:
static analysis proposes, dynamic analysis confirms. Committing to a full
write-up before the Aha moment produces confident-sounding fiction. The notebook
keeps you honest about what is known versus assumed.

### Phase 1 — Running lab notebook

Maintain a short markdown scratch document as you analyze. Each entry is a
hypothesis and its status. Prefer this terse form:

```
## Notebook

- [confirmed] UI string "Trial expired" xrefs into -[LicenseManager isActivated]
- [assumed]   gating boolean lands in w0, then cbz w0 -> unauthorized branch
- [confirmed] LLDB: w0 == 0 at branch on unlicensed run; register write w0 1 unlocks UI
- [open]      x86_64 slice: is the same check present? not yet inspected
```

Update statuses as evidence arrives. An assumption is not a finding until
dynamic analysis (LLDB) or byte-level inspection confirms it. The notebook is
the artifact you reason from — show it to the user as you go.

### Phase 2 — Full write-up (after the Aha moment)

When the gating model is fully reconstructed and the unlock is demonstrated,
expand the notebook into the full write-up using the template below. Match the
depth and reasoning quality of `examples/demo-poc.md`.

## The six-ring analysis skeleton

Drive the analysis along this fixed skeleton. Each ring is both an analysis step
and a difficulty knob a CTF author can turn. Use it as the spine of both the
notebook and the final write-up.

```
state source -> call convention -> gating decision -> arch difference -> patch risk -> validation loop
   (source)        (flow)            (the linchpin)      (semantics)        (cost)         (proof)
```

1. **State source** — Work backward from strings. UI behavior is the visible
   projection of state; strings are anchors; xrefs are the rope back to the
   source. In IDA, `Shift+F12` for the Strings window; search `Trial`,
   `expired`, `register`, `activated`, `invalid license`, license file paths,
   `NSUserDefaults` keys, Keychain service names. Press `X` on a hit to follow
   xrefs to the reader. If strings are obfuscated (XOR / base64 / runtime
   concat), static search fails — pivot to dynamic breakpoints.

2. **Call convention** — Objective-C has no plain calls; everything dispatches
   through `objc_msgSend`. The real information is in registers. Recover the
   semantics of each message by finding who set the receiver and selector before
   the call:

   | role | arm64 | x86_64 |
   |---|---|---|
   | receiver (self) | `x0` | `rdi` |
   | selector (_cmd)  | `x1` | `rsi` |
   | first argument   | `x2` | `rdx` |
   | return value     | `x0` | `rax` |

   If IDA resolves `__objc_selrefs` / `__objc_methname`, selectors become
   readable method names — a free call map. Note whether symbols are stripped
   and whether selectors are built dynamically via `NSSelectorFromString`.

3. **Gating decision (the linchpin)** — The auth logic collapses to a boolean
   feeding a conditional branch. Watch the key instructions:

   | platform | instructions | meaning |
   |---|---|---|
   | arm64  | `cbz` / `cbnz` | branch on register zero |
   | arm64  | `tbz` / `tbnz` | test a bit, then branch |
   | arm64  | `cmp` + `b.eq` / `b.ne` | compare then conditional |
   | x86_64 | `test` / `cmp` + `je` / `jne` | compare then conditional |

   Typical shape: `if (isValid)` → return value in `w0` → `cbz w0,
   <unauthorized>`. Finding that branch is finding the linchpin. Watch for
   **multiple** gates (TOCTOU): a startup check plus a second check on a premium
   feature. NOPing only the startup check fails later.

4. **Architecture difference** — Universal (fat) binaries carry both arm64 and
   x86_64 slices. `lipo -info <binary>`; `lipo -thin arm64 <binary> -output
   <out>` to split. The same logic is **two independent instruction encodings**:
   patching arm64 ≠ patching x86_64. Apple Silicon runs arm64; Intel / Rosetta
   runs x86_64. A CTF author may make the slices intentionally inconsistent so a
   single-slice patch breaks under Rosetta.

5. **Patch risk** — Three basic moves, each with a corresponding risk that is
   itself an advanced exam point:

   | move | arm64 | x86_64 | note |
   |---|---|---|---|
   | NOP the check call | `nop` | `90` | check never happens |
   | flip / short the branch | `b.eq`→`b.ne` or force `b` | `je`→`jne` | invert direction |
   | force return value | `mov w0,#1; ret` | `mov eax,1; ret` (`B8 01 00 00 00 C3`) | cleanest; fixes at source |

   Risks: **code signing** (editing `__TEXT` changes CDHash → AMFI kills the
   process; re-sign ad-hoc with `codesign -f -s - <binary>`); **self-check /
   anti-tamper** (program hashes its own `__TEXT`); **PAC** on arm64e (signed
   pointers — affects tampering signed pointers, usually not boolean/compare
   edits); **server dependency** (patching the boolean yields an empty shell —
   the concrete embodiment of "the value isn't in the boolean").

6. **Validation loop** — Static proposes, dynamic confirms. The standard loop
   *is* patch validation:

   ```
   static locate -> dynamic confirm -> in-memory trial -> persist to disk -> re-sign and verify
   ```

   ```bash
   lldb <binary>
   br set -n "-[LicenseManager isValid]"   # break on the suspected method
   run
   register read x0                          # inspect self / return
   register write x0 1                       # force the return in memory
   continue                                  # does the UI actually unlock?
   ```

   Confirm the linchpin in memory before committing the change to the file and
   re-signing. Watch for anti-debug (`ptrace(PT_DENY_ATTACH)`, `sysctl`
   `P_TRACED`) that blocks LLDB attach.

## From one working build to a portable PoC

A fixed offset or one successful byte patch proves only one binary. When the
PoC becomes a reusable keygen or patcher, define a **compatibility profile** from
business semantics rather than treating one compiler layout as an API.

### Rank signature evidence by stability

| evidence | stability across builds | how to use it |
|---|---|---|
| absolute vmaddr, fat-slice offset, branch displacement | very low | output/debug evidence only; never an input contract |
| stack layout, register allocation, relocation immediates | low | mask or derive when they do not carry business meaning |
| obfuscated-string initializer bytes | low | expect regeneration; do not confuse ciphertext layout with plaintext semantics |
| unique caller argument setup and algorithm enum | high | use as the first semantic anchor |
| caller-to-helper control-flow edge | high | decode and follow it instead of scanning for an unrelated lookalike |
| ordered operations and repeated call-target relationships | high | validate data flow and call topology |
| original/patched function-entry states | high | make patching explicit and idempotent |

A long exact instruction sequence is not automatically a semantic signature.
If it pins fixed indices for relocation words, register choices, or generated
obfuscator setup, it is still a build fingerprint and will break on harmless
recompilation.

### Build a caller-linked semantic locator

For arm64, prefer this sequence:

1. Parse the correct thin/fat Mach-O slice and retain its file bounds.
2. Find a stable caller anchor that includes meaningful argument setup, such as
   an algorithm enum or schema discriminator.
3. Decode the caller's `bl` instruction. Sign-extend `imm26`, multiply it by
   four, and add it to the address of the branch instruction itself.
4. Require the target to be four-byte aligned and fully inside the selected
   slice before reading it.
5. Validate the helper by semantic phases: argument preservation, constructor /
   algorithm setup, ordered input additions, result extraction, truncation,
   cleanup, and return.
6. Compare call-target relationships. If the same logical operation appears
   three times, require all three `bl` instructions to resolve to the same
   target; also require distinct roles to remain distinct where proven.
7. Require exactly one valid caller/helper pair. Zero or multiple candidates are
   profile failures, never a reason to pick the first match.
8. Recognize both known entry states (`original` and `patched`) and make reruns
   idempotent. Any third state is an explicit error.

Use bounded variable regions only where evidence justifies them. For example, a
per-build string initializer may vary in length, but the stable decoder call and
post-decoder data flow can still anchor the suffix. Bound the search window and
require the complete suffix exactly once so a wildcard cannot swallow arbitrary
code.

### Write the compatibility contract before relaxing a matcher

State three separate sets:

- **Proven invariant:** algorithm enum, discriminator, call ordering, truncation,
  output format, or another behavior confirmed by static/dynamic evidence.
- **Tolerated build drift:** vmaddrs, slice offsets, `bl` immediates, relocations,
  stack-guard addresses, and the observed variable compiler/obfuscator region.
- **Unproven blind spot:** a value hidden behind an opaque decoder, VM, runtime
  service, or encrypted table whose plaintext has not been recovered.

Opaque values need an honest decision. Either reverse/emulate the decoder,
capture the value during natural execution and establish a known vector, or
publish the blind spot. Do not wildcard opaque bytes and then claim the matcher
will detect every algorithm change. Phrase future support as: compatible while
the recognizable profile remains intact; detectable drift fails closed.

### Drive portable matchers with behavior tests

Use TDD when turning analysis into automation:

1. Keep compact fixtures derived from at least one old compatible build and the
   newly drifting build. Fixtures should preserve the relevant control-flow edge,
   not merely place caller and helper bytes independently in one blob.
2. RED: prove the current matcher rejects the new semantically equivalent layout.
3. GREEN: make the smallest semantic relaxation that accepts both builds.
4. Add negative mutations that must still fail:
   - changed algorithm enum or discriminator;
   - missing or duplicate caller/helper pairs;
   - out-of-bounds or unaligned branch target;
   - changed ordered operation or repeated call-target topology;
   - unknown function-entry bytes.
5. Run real binaries as integration checks, while keeping unit tests offline and
   deterministic. Report discovered offsets as evidence, never fixtures consumed
   by the patcher.

Tests should describe user-visible compatibility and rejection behavior. A test
that only mirrors private matcher tables will preserve the overfitting instead of
preventing it.

### Validate mutation and code signing in the right order

Use a disposable copy and preserve the pristine/installed app as read-only:

```
read-only profile check on original
  -> copy to a temporary work bundle
  -> remove analysis companion files that would pollute signing
  -> patch without signing
  -> assert the exact changed byte range
  -> ad-hoc sign
  -> codesign verification
  -> rerun locator (must report patched/idempotent)
  -> launch and verify actual behavior/persistence
```

The byte-diff assertion belongs **before** `codesign`: replacing a Developer ID
signature with an ad-hoc signature legitimately changes the code-signature region,
so a post-sign whole-file diff cannot prove that only the intended instruction
bytes were patched. Never patch the installed/reference binary to save a copy.

### Protect generated artifacts from failed preflight checks

Shell redirection opens and truncates its target before the program validates
its inputs. A failed profile check can therefore erase the previous known-good
artifact. Run a read-only preflight first, or publish atomically:

```bash
tool --check /path/to/Demo.app
tool --app /path/to/Demo.app > output.txt.tmp && mv output.txt.tmp output.txt
```

Keep deterministic generation separate from host probing and app inspection so
unit tests can compare payload/envelope content without invoking a debugger or
mutating an application bundle.

## Two insights worth surfacing explicitly

These are the high-value observations an interviewer probes for. Reach for them
when the target exhibits them:

- **patch-me vs keygen-me.** Patch-me trains *location*; keygen-me trains
  *algorithm understanding*. A keygen-me's check can be entirely correct, signed,
  and self-check-clean — the only way through is to actually understand the
  algorithm. Good authors deliberately mine the patch path (multiple gates,
  self-check, PAC) to force "understand, don't tamper."

- **Runtime-random sentinel.** When the "good" value is computed at startup
  (`KeyWellformed = random()`...), you cannot hardcode a patched return value —
  the legal value changes every launch. The stable PoC reuses the program's own
  legal-value reader (e.g. tail-branch `ApplicationLicenseBits()` straight into
  `ApplicationLicenseBitsGoodly()`) rather than forging a constant. See
  `examples/demo-poc.md` §5–6 for the canonical treatment, including the
  function-entry discipline (the branch must overwrite the *first* instruction
  so the prologue never runs, or the stack desyncs).

## Full write-up template

Use this structure for the final deliverable. Adapt section count to the target,
but preserve the arc: background → gating model → arch handling → patch →
validation → interview answer.

```markdown
# PoC Write-up: <target> Authorization Gating Reverse-Engineering

## 1. Background
What the demo is, why it's being analyzed (learning / interview), scope note.

## 2. Analysis target
The binary (arch slices), the suspected gating question in one line
(e.g. `currentBits == goodBits`).

## 3. Initial location path
From UI strings / symbols to the consumption point. Note false-positive
keywords and how you disambiguated.

## 4. Authorization model reconstruction
The reconstructed call chain and the two-layer structure (business consumer
vs. license framework internals). Show the gating comparison.

## 5. Key findings
The non-obvious facts (e.g. runtime-random sentinel, multiple gates,
arch inconsistency) and why they constrain the patch.

## 6. Patch strategy
The chosen move and *why* it's the most stable, including function-entry
discipline.

## 7. Universal Mach-O handling
Per-slice work; why arm64 bytes != x86_64 bytes.

## 8. Code signing
Why the original signature breaks and how to re-sign for the experiment.

## 9. LLDB validation
The breakpoints and register checks that prove the control flow.

## 10. Technical summary
The reconstructed model as a flow, and the core conclusion.

## 11. Interview answer
One paragraph: the whole PoC in the voice of a candidate explaining it.
```

## Tool quick reference

| task | command / action |
|---|---|
| view arch slices | `lipo -info <binary>` |
| split one arch | `lipo -thin arm64 <binary> -output <out>` |
| IDA strings window | `Shift+F12` |
| IDA cross-references | select, press `X` |
| launch LLDB | `lldb <binary>` |
| break on symbol | `br set -n "-[Class method]"` |
| read register | `register read x0` |
| write register | `register write x0 1` |
| ad-hoc re-sign | `codesign -f -s - <binary>` |
| check encryption | inspect `LC_ENCRYPTION_INFO` `cryptid` |
