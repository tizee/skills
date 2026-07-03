# Clean Architecture Review Checklist

## Table of Contents

- Requirement fidelity gate (see requirement-fidelity.md)
- Construction-level rules and anti-patterns (see code-construction-rules.md)
- Severity rubric (`P0`..`P3`)
- Layer boundary checks (clean architecture)
- Cross-layer business logic chaos patterns
- YAGNI misapplication: deferring layer violations
- SOLID review checks
- Module depth checks (deep vs shallow)
- Information hiding and leakage checks
- KISS / over-engineering checks (from `kiss`)
- DRY / PIE / SLAP checks
- Orthogonality and reversibility checks
- Action habits and risk laws
- Production robustness checks
- Code smells quick reference
- Testing best practices
- Reporting heuristics

## Requirement Fidelity Gate

See [requirement-fidelity.md](requirement-fidelity.md). Run it **before** any check in this file: locate the requirement source, map requirement items to code paths and tests, and classify mismatches as design-level defects vs behavior bugs. Architecture checks on a change that implements the wrong requirement produce a well-structured wrong product.

## Construction-Level Rules

See [code-construction-rules.md](code-construction-rules.md) for function/statement/variable-level checks (naming, variables, constants, control flow, comments, defensive programming, error handling, concurrency) and the anti-pattern catalog with worked examples. Apply them while walking the diff, after the architecture lenses in this file.

## Severity Rubric (`P0`..`P3`)

See [severity-rubric.md](severity-rubric.md) for full definitions and examples.

## Layer Boundary Checks (Clean Architecture)

Validate actual dependency direction and business logic placement.

### Expected Responsibility by Layer

#### Domain Layer

Own:
- Core business rules and invariants
- Domain entities/value objects/domain services
- Domain language and policies

Avoid:
- Framework types (HTTP requests/responses, ORM models, web context)
- SQL queries, network clients, filesystem calls
- Serialization formats and transport DTOs

#### Application / Use-Case Layer

Own:
- Orchestration of domain behavior
- Transaction boundaries (business-level)
- Coordination of ports/repositories/services
- Use-case-specific validation and workflow sequencing

Avoid:
- HTTP parsing/rendering details
- Raw infrastructure calls that bypass ports
- Business rules that belong inside domain objects/services

#### Interface / Adapter Layer

Own:
- Translate external inputs/outputs (HTTP, CLI, events) into application commands/results
- Map transport DTOs to use-case input and back

Avoid:
- Deep business decisions/invariants
- Persistence decisions

#### Infrastructure Layer

Own:
- Database, queue, cache, API clients, filesystem implementations
- Technical retries, serialization, connection management
- Implementing ports declared by inner layers

Avoid:
- Product/business decisions and branching rules
- Returning framework-specific models beyond the boundary

### Boundary Violation Red Flags

- Domain imports ORM/entity annotations tightly coupled to persistence behavior
- Domain or use-case code reads HTTP headers/cookies directly
- Controllers contain pricing, authorization policy, or state transition logic
- Repositories choose business status/outcome instead of data access concerns
- Infrastructure code silently applies business defaults/invariants
- DTOs leaking into domain method signatures
- Use cases depending on concrete adapters instead of ports/interfaces
- Circular dependencies between layers/modules

## Cross-Layer Business Logic Chaos Patterns

These are priority findings because they create hidden behavior and production inconsistency.

### Split Invariant Enforcement

Symptoms:
- Validation partly in controller, partly in service, partly in repository/DB
- Different entrypoints enforce different subsets of rules

Production risk:
- Inconsistent writes, bypassed checks, hard-to-debug incidents

### Hidden Business Decisions in Infrastructure

Symptoms:
- Retry policy changes business semantics (e.g., duplicate side effects)
- Repository auto-fills status/tenant/ownership rules
- Cache fallback changes authorization or pricing behavior

Production risk:
- Silent correctness bugs under failure modes

### Transport-Driven Domain Behavior

Symptoms:
- Domain logic branches on HTTP status, route names, request context
- Event payload schema details leak deep into core logic

Production risk:
- Fragile core model coupled to interface churn

### Persistence Model Equals Domain Model (without intent)

Symptoms:
- ORM model passed everywhere as domain object
- Lazy-loading/persistence semantics influence business rules

Production risk:
- Implicit I/O, transaction surprises, test unreliability

## YAGNI Misapplication: Deferring Layer Violations

YAGNI ("You Aren't Gonna Need It") is about not building features prematurely. It is **not** a license to defer fixing structural violations.

### The Anti-Pattern

A review finds code in the wrong layer (e.g., a parsing function that encodes domain contract semantics living in the CLI layer). The reviewer recommends: "wait until a second consumer exists before moving it." This sounds like YAGNI, but it is a misapplication.

### Why It's Wrong

| Concern | YAGNI applies? | Reasoning |
|---------|---------------|-----------|
| "Don't build feature X until you need it" | Yes | Feature may never be needed |
| "Don't add abstraction Y until variation is real" | Yes | Abstraction may be speculative |
| "Don't fix layer violation Z until a second consumer exists" | **No** | The violation is structural debt, not a feature. Its fix cost only grows over time. |

A layer violation is not a missing feature — it is a dependency direction error that exists **now**. Key differences:

- **A missing feature** costs nothing until someone needs it. Deferring is free.
- **A layer violation** imposes cost on every future consumer: they must either import across boundaries (violating dependency direction) or duplicate the logic (violating DRY). The "second consumer" will inherit the violation as a constraint.

### Detection Heuristic

When reviewing a finding that recommends deferral, ask:

1. **Does the code encode a contract owned by an inner layer?** (e.g., parsing semantics, validation rules, state machine transitions)
2. **Would a second consumer need to import from the wrong layer or rewrite the logic?**
3. **Is the fix trivial?** (move function + update imports)

If all three are yes, fix it now. The "wait for a second consumer" advice is rationalizing structural debt as YAGNI discipline.

### Example

```python
# BAD: CLI layer encodes the None/[]/[items] contract that filter_tools() depends on
# llms/app/cli/agent.py
def _parse_csv_flag(value: str | None) -> list[str] | None:
    if value is None:
        return None        # not provided -> no filtering
    if value == "":
        return []          # empty -> disable all tools
    return [s.strip() for s in value.split(",") if s.strip()]

# GOOD: Contract lives next to its consumer in the agent layer
# llms/agent/tools/filter.py
def parse_tool_names(value: str | None) -> list[str] | None:
    ...  # same logic, correct layer
```

### Severity

- If the misplaced code encodes a **domain invariant** (e.g., validation, state transition): P1-P2
- If the misplaced code encodes an **input contract** (e.g., parsing, normalization): P2
- If the misplaced code is pure utility with no semantic coupling: P3 (or ignore)

## SOLID Review Checks

Use SOLID as a change-risk lens, not a dogma checklist.

### S: Single Responsibility Principle

Flag when one class/function/module has multiple reasons to change:
- Business rules + persistence + transport mapping + logging all mixed
- "Manager"/"Service" objects doing orchestration and low-level I/O

Ask:
- Can one behavioral change force touching this unit for unrelated reasons?

### O: Open/Closed Principle

Flag when extension requires editing many existing branches:
- Type-code `if/else` scattered across modules
- Feature addition requires touching controller, service, repo, serializer in parallel due to missing boundary design

Nuance:
- Do not add plugin architectures prematurely. Prefer simple branching until variation is real.

### L: Liskov Substitution Principle

Flag when abstractions lie:
- Interface implementations violate expected invariants/error behavior
- "Repository" implementations return incompatible semantics (e.g., `None` vs exception vs partial object)

Production impact:
- Runtime surprises only under certain providers/environments

### I: Interface Segregation Principle

Flag bloated interfaces/ports:
- Consumers depend on methods they never use
- Shared interfaces force infra implementations to support irrelevant operations

KISS tie-in:
- Overly generic ports often indicate speculative abstraction.

### D: Dependency Inversion Principle

Flag dependency direction leaks:
- Use cases import concrete DB/SDK clients directly
- Domain depends on framework infrastructure utilities

Also flag fake DIP:
- Interface exists but concrete type is still constructed inside the use case, defeating inversion

## Module Depth Checks (Deep vs Shallow)

> Source: John Ousterhout, *A Philosophy of Software Design*

A module's value is the ratio of functionality it hides to the complexity of its interface. **Deep modules** have simple interfaces and rich implementations. **Shallow modules** have interfaces nearly as complex as their implementations — they add abstraction cost without reducing what callers must know.

### Shallow Module Red Flags

- **Pass-through methods**: method does nothing except forward arguments to another method with a similar signature. The abstraction layer adds no value.
- **Thin wrapper classes**: a class that wraps another class (or a library) and exposes the same interface with trivial additions. The wrapper is overhead, not simplification.
- **One-line interface implementations**: an interface/protocol with 5+ methods where every implementation is a trivial delegation. The interface exists for "testability" but adds no behavioral abstraction.
- **Classitis**: functionality split across many tiny classes/protocols where each does almost nothing. Callers must assemble and coordinate them, increasing cognitive load.

### Deep Module Indicators (Good Design)

- Interface exposes 2–5 operations; implementation handles edge cases, retries, caching, format negotiation internally
- Callers don't need to know about implementation details to use the module correctly
- The most common usage requires minimal parameters

### Review Questions

- Does this abstraction boundary **reduce** what the caller must know, or merely **relocate** it?
- Would inlining this module into its caller make the code simpler without losing encapsulation?
- Is the interface simpler than the implementation? If not, the module may be too shallow.

### Severity

- Shallow modules that cause **shotgun surgery** (changing one behavior requires touching many thin wrappers): P2
- Pass-through methods that obscure control flow in critical paths: P2
- Classitis that inflates codebase size without functional benefit: P3

## Information Hiding and Leakage Checks

> Source: John Ousterhout, *A Philosophy of Software Design* + David Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules*

Each module should encapsulate a **design decision** — data structures, algorithms, policies, formats — so that decision can change without rippling through the system. Information leakage occurs when the same design decision is reflected in multiple modules.

### Information Leakage Red Flags

- **Temporal decomposition**: modules split by execution order (read → parse → validate → write) instead of by the knowledge they encapsulate. Each step shares format/schema knowledge that should be in one place.
- **Shared format assumptions**: two modules both know the wire format, file layout, or serialization schema. If the format changes, both must change.
- **Back-channel coupling**: module A "knows" that module B stores data in a specific structure and reads it directly instead of going through B's interface.
- **Leaked implementation types**: a module returns or accepts types that expose internal choices (e.g., returning a `SQLAlchemy.Row` from a repository, or accepting an `HTTPRequest` in a domain service).
- **Config-driven behavior spread**: a configuration value is read in multiple modules that each interpret it independently, instead of one module interpreting it and exposing a semantic interface.

### Versus Cross-Layer Chaos

Cross-layer chaos (covered earlier) is about business logic escaping its proper layer. Information leakage is broader — it also occurs **within the same layer** when peer modules share knowledge they shouldn't. Both are dependency problems, but they require different detection strategies:

| Pattern | Detection | Example |
|---------|-----------|---------|
| Cross-layer chaos | Domain import in wrong layer | Controller validates business rules |
| Information leakage | Same knowledge in peer modules | Two services both parse the same CSV format |

### Review Questions

- If this internal data structure changed, how many modules would break?
- Are peer modules coupled by shared knowledge of a format, protocol, or schema?
- Could a new module be extracted that owns this knowledge exclusively?

### Severity

- Leakage of a **domain invariant** across modules (e.g., pricing formula duplicated in order service and invoice service): P1
- Leakage of **format/protocol knowledge** across modules: P2
- Leakage of **minor implementation details** with low change probability: P3

## KISS / Over-Engineering Checks (from `kiss`)

Apply the `kiss` skill philosophy: manage complexity first.

### KISS Review Questions

- Is there a simpler design that preserves correctness and production safety?
- Does an abstraction hide complexity, or merely relocate it?
- Is the interface simpler than the implementation behind it?
- Is this complexity justified by current change pressure, scale, or reliability needs?

### Over-Engineering Red Flags

- Generic framework around one workflow and one implementation
- Multiple layers of factories/builders/strategies for trivial branching
- "Future-proofing" abstractions without a known second use case
- Configurability that weakens invariants or makes runtime behavior hard to reason about

### Good Complexity (Do Not Penalize)

Do not flag complexity if it clearly supports:
- Transactional correctness
- Idempotency and deduplication
- Fault isolation and retries with bounded semantics
- Security boundaries and tenancy isolation
- Observability needed for production debugging

## DRY / PIE / SLAP Checks

These three principles target *readability and change-cost at the function and module level*. They are distinct from layer boundaries (structural) and from KISS (whole-design simplicity).

### DRY — Don't Repeat Yourself (Knowledge, Not Text)

DRY is about **duplicated knowledge**, not duplicated characters. A piece of knowledge is a single authoritative statement of a rule, format, or policy.

Flag when:

- The same business rule (tax formula, eligibility check, status transition) is implemented in two or more places, so a change must be made in lockstep.
- The same wire format / schema / magic constant is hardcoded in multiple modules.
- A validation that defines a contract is copy-pasted across entrypoints.

Do **not** flag when:

- Two blocks merely *look* similar but encode independent decisions that may diverge later. Coupling them creates a false abstraction.
- Removing the duplication would require a confusing parameterized helper that obscures both call sites (DRY losing to KISS).

Detection heuristic: *"If this rule changed, how many places must change together, and would a developer reliably find all of them?"* If the answer is "several, and easy to miss" — it is a DRY violation. If it's "two, but they may legitimately diverge" — leave it.

Severity:

- Duplicated **domain invariant** (pricing, auth, state transition): P1
- Duplicated **format/protocol/constant**: P2
- Duplicated boilerplate with low change probability: P3

### PIE — Program Intent Explicitly

Code should make *what* it does and *why* obvious without forcing the reader to reverse-engineer the body.

Flag when:

- Magic numbers/strings encode a rule with no name (`if status == 3` instead of `if status == OrderStatus.SHIPPED`).
- Boolean parameters force the caller to guess meaning (`create(true, false)`); prefer named enums/options.
- A clever one-liner compresses several decisions into an unreadable expression.
- Control flow relies on side effects whose purpose is undocumented and non-obvious.
- A comment explains *what* the code does (noise) instead of *why* a non-obvious choice was made (signal).

Fix direction: introduce named constants/enums, extract intention-revealing helper functions, replace boolean flags with named options, and reserve comments for rationale.

Severity: usually P3; escalate to P2 when the hidden intent governs a correctness-critical branch (auth, money, data writes).

### SLAP — Single Level of Abstraction per Function

Each function should operate at one level of abstraction. High-level policy and low-level mechanics should not be interleaved in the same body.

Flag when:

- A function mixes orchestration (`processOrder()`) with raw byte/SQL/string manipulation in the same scope.
- Reading top-to-bottom forces the reader to "zoom" between strategy and implementation detail repeatedly.
- A long method has clearly separable phases that each deserve a named sub-function.

Fix direction: extract lower-level steps into named helpers so the parent function reads as a sequence of intent-level steps. This is the "compose method" pattern.

SLAP vs Long Method: Long Method is about *size*; SLAP is about *mixed altitude*. A 12-line function can still violate SLAP if it jumps abstraction levels; a 25-line function can be fine if it stays at one level.

Severity: P2 when it obscures a critical path; P3 otherwise.

## Orthogonality and Reversibility Checks

> Source: Hunt & Thomas, *The Pragmatic Programmer*

### Orthogonality

Orthogonal components are independent: changing one does not affect the others. Orthogonality is the design property that makes high cohesion / low coupling *measurable*.

Flag when:

- A change to one feature unexpectedly breaks an unrelated feature (signals hidden coupling).
- Two modules must always be modified together despite serving different concerns.
- A "shared utility" accumulates unrelated responsibilities, becoming a coupling hub.
- Global/singleton mutable state forces implicit coordination between otherwise independent code.

Review question: *"If I change this component, what else do I have to touch or re-test?"* A long, surprising answer indicates low orthogonality.

Severity: P1 when a single change forces edits across unrelated modules (entangled blast radius); P2 for localized entanglement.

### Reversibility

Good architecture avoids "one-way door" decisions wherever the cost of being wrong is high. It keeps critical choices (database vendor, transport, third-party SDK) behind boundaries so they can be swapped.

Flag when:

- A vendor SDK or framework type is referenced directly throughout the codebase, making replacement a rewrite.
- A schema/format decision is baked into many call sites with no migration seam.
- Business logic assumes a specific deployment topology or storage engine.

Nuance (avoid over-engineering): Not every decision needs reversibility. Demand it where the decision is *expensive to reverse and reasonably likely to change*. Wrapping a stable standard-library call behind a swappable port is speculative — flag *that* as over-engineering instead.

Severity: P2 when an expensive, likely-to-change decision has no isolation seam; P3 for minor lock-in.

## Action Habits and Risk Laws

These are not per-line checks; they shape the *recommendations* a reviewer gives and the *narrative* of the Architecture Summary.

### Action Habits (recommend these in fix directions)

- **Boy Scout Rule**: Leave code cleaner than you found it. When a change touches a messy area, recommend a small, scoped cleanup — not a full rewrite. Use to justify low-cost P3 improvements adjacent to the change.
- **Egoless programming**: Critique the code, not the author. Phrase findings as design risks and failure modes, never as personal judgment. (Enforced by the Evidence Rules in SKILL.md.)
- **Small steps**: Prefer many small, verifiable changes over one large risky refactor. When recommending remediation, sequence it: smallest safe step first, strategic follow-up second.
- **Clarity before optimization**: Do not accept complexity justified only by speculative performance. Recommend the clear version first; demand a measured bottleneck before endorsing an optimization that sacrifices readability.
- **Automate and reuse**: Recommend automating repeated manual checks (lint rules, CI gates) when the same class of defect recurs.

### Risk Laws (use to explain *why* a finding matters and to calibrate severity)

- **Broken Windows**: Tolerated bad code invites more bad code. A small mess in a hot path tends to spread. Use this to escalate an otherwise-P3 smell when it sits in a high-traffic module others will copy.
- **Entropy (software rot)**: Without active maintenance, structure decays. Frame accumulating debt findings in terms of trajectory, not just current state.
- **Second-System Effect**: Rewrites and "v2" designs tend toward feature-bloat and over-engineering. When reviewing a redesign, watch for speculative generality and abstractions added "because we learned from v1."
- **Yak Shaving**: A fix that drifts far from the original problem is a smell. Flag PRs whose scope wanders into unrelated refactors; recommend splitting them. Keep remediation aligned to the actual problem.

### Organizational Context (NOT code findings)

These laws operate at the team/org level. Do **not** raise them as code-review findings — they cannot be fixed by editing the code under review. Mention them only as context in the Architecture Summary when a structural pattern clearly reflects an org cause.

- **Brooks's Law**: Adding people to a late project makes it later. Relevant only when discussing delivery risk, not code.
- **Conway's Law**: System structure mirrors the communication structure of the org that built it. Useful for *explaining* why module boundaries fell where they did (e.g., a boundary that follows team lines rather than domain lines), but the remediation is organizational, not a code edit. Note it as an observation, never as a P0-P3 finding.

## Production Robustness Checks

The goal is to decide whether the codebase can operate safely in real production conditions.

### Correctness and Data Safety

- Are business invariants enforced in one authoritative place?
- Can alternate entrypoints bypass core rules?
- Are state transitions explicit and validated?
- Are partial writes/side effects possible without compensation?

### Failure Handling

- Are retries/timeouts/circuit breaking placed in the right layer?
- Do retries change business semantics (duplicates, reordering)?
- Are failures surfaced loudly (fail fast) instead of silently defaulting?

### Operational Observability

- Can you trace a business flow across layers?
- Are errors/logs emitted at the right boundaries with enough context?
- Is critical behavior hidden in framework magic/ORM side effects?

### Change Safety

- Does changing a rule require touching many layers?
- Are interfaces stable and meaningful, or leaky and fragile?
- Can behavior be tested without full infrastructure boot?

## Testing Best Practices

### What to Test
- Requirement-based tests: each key requirement item maps to at least one test that fails if the requirement is violated (see [requirement-fidelity.md](requirement-fidelity.md))
- Boundary values, invalid/dirty input, and failure paths — not just the nominal path
- Unit tests for business logic
- Integration tests for data access
- Test names describe behavior (Given_When_Then)
- Tests are independent (no shared state)
- Fast execution (< 10ms per unit test)
- Meaningful assertions (not just coverage)

### Testing Rules
- **Never** mock value objects (they're cheap to create)
- **Never** test private methods directly (test through public API)
- **Never** share state between tests
- **Always** test behavior, not implementation

### Test Validity Heuristic

The **deletion test**: if you delete the core logic of the function under test, does the test still pass? If yes, the test is decoration, not verification.

Detection:
- Assertions only check `toBeDefined()` / `not.toBeNull()` / `.toHaveLength(n)` without verifying actual business values
- Test inputs are trivial (empty objects, zero values) that exercise no meaningful branch
- No negative test cases — nothing checks that wrong inputs produce errors or wrong outputs are rejected

Fix direction:
- Assert concrete business results: `expect(result.totalAmount).toBe(900)`, `expect(result.status).toBe('confirmed')`
- Include boundary cases and error paths
- After writing a test, **delete the implementation body** and confirm the test fails — if it doesn't, the test is worthless

### Bug Fix Testing Discipline (Red-Green)

When fixing a bug, follow this order:

1. **Write a reproducing test** that captures the buggy behavior
2. **Run it and confirm it fails** (red) — this proves the test actually catches the bug
3. **Fix the code**
4. **Run it and confirm it passes** (green) — this proves the fix works

The reverse order (fix first, add test after) is unreliable: you can never be sure the test would have caught the bug, because you never saw it fail. A test you've never seen fail is a test you can't trust.

### Debug Log Discipline

When debugging with inserted log/trace statements:
- **Do not remove debug logs as part of a bug fix commit.** Debug logs are removed by the human after confirming the fix is correct, not by the AI alongside the fix.
- Rationale: if the fix is wrong, the logs are gone too, and must be re-inserted for the next debugging round. Keep logs until the issue is confirmed resolved, then clean up in a separate pass.

## Reporting Heuristics

- Findings first, sorted by severity.
- Tie each finding to a concrete failure mode or change hazard.
- Prefer "move logic to X layer" over broad rewrite advice.
- If architecture is mostly sound, say so and highlight the strongest design choices.
- Distinguish immediate remediation from strategic refactor opportunities.

## AI Over-Engineering Code Smell Checklist

AI-generated code has characteristic failure modes distinct from human code smells. Use this checklist to catch patterns that LLM-authored code introduces systematically.

- **Duplication (重复代码类)**
  - Structural duplication (结构重复): near-identical blocks differing only by variable names — LLMs copy-paste across call sites instead of extracting
  - Boilerplate skeleton (骨架重复): scaffolding classes/interfaces generated "just in case" with no runtime path that exercises them

- **Noise Code (噪音代码类)**
  - Empty function body (空函数体): methods with `pass` / `{}` / `throw NotImplemented` that were never filled in
  - Commented-out code (注释掉的代码): entire blocks left as `// old approach` with no explanation
  - Dead branch (死分支): `if False:` / `if (false) {` guards or version flags that can never be true
  - Unreachable code (不可达代码): statements after unconditional `return`/`throw`
  - Trivial comment (废话注释): `// increment i by 1` — restates code without adding intent
  - Excessive comments (过度注释): every line annotated, obscuring signal with noise
  - Unused import (未使用导入): imports added speculatively and never referenced
  - Leftover boilerplate (残留样板): `TODO: implement`, `YOUR_API_KEY_HERE`, placeholder strings shipped to production

- **Excessive Defensiveness (过度防御类)**
  - Redundant type check (冗余类型检查): `if isinstance(x, str) and isinstance(x, str)` / double null-guards on the same value in the same scope
  - Unnecessary default (不必要默认值): silently substituting `""` / `0` / `{}` for missing required config instead of raising at init — masks misconfiguration

- **Error Handling (错误处理类)**
  - Swallowed error (吞没异常): `except Exception: pass` or `catch (e) {}` — failures disappear silently
  - Broad catch (过宽捕获): catching `Exception`/`Throwable`/`Error` at a low level, then continuing as if nothing happened — converts hard faults into subtle corruption

- **Test Fabrication (测试拟合类)**
  - Hardcoded lookup (硬编码拟合): AI doesn't understand the logic, so it hardcodes return values that match test inputs — tests pass, but logic is a lookup table, not an implementation. Example: `if (amount === 1000 && level === 'gold') return 100;` instead of `return amount * discountRate(level);`
  - Vacuous assertion (空洞断言): test only checks `toBeDefined()` / `not.toBeNull()` / `toHaveLength` without verifying business-meaningful values — test cannot distinguish correct behavior from any non-null garbage

- **Type System Escape (类型系统逃逸类)**
  - Any-type escape (滥用 Any): using `Any` / `object` / `unknown` when concrete types or interfaces exist — LLMs default to `Any` when unsure about types, silently defeating type safety at boundaries
  - Unsafe cast (强制类型断言): unconditional `as SomeType` / `(<T>value)` / `cast()` without verifying the actual runtime type, deferring type errors to runtime

- **Security Risk (安全风险类)**
  - Hardcoded credential (硬编码凭证): API keys, passwords, tokens embedded in source
  - Injection risk (注入风险): unsanitised user input concatenated into SQL/shell/eval
  - Unsafe deserialization (不安全反序列化): `pickle.loads(user_data)` / `YAML.load` without safe loader
  - Weak crypto (弱加密算法): MD5/SHA1 for integrity, ECB mode, custom RNG seeded from time
  - Sensitive data in logs (敏感数据日志泄露): passwords, tokens, PII written to structured logs or tracing spans

### Severity Mapping for AI Smells

| Category | Default Severity | Escalate to P0 when... |
|---|---|---|
| Duplication | P3 | duplication splits a business invariant across copies |
| Noise Code | P3 | leftover_boilerplate or dead_branch reaches production config/auth path |
| Type System Escape | P2 | unsafe_cast on data crossing a trust boundary (auth token, payment amount) |
| Excessive Defensiveness | P2 | unnecessary_default masks a required-but-missing secret |
| Error Handling | P1 | swallowed_error in a payment, auth, or data-write path |
| Test Fabrication | P1 | hardcoded_lookup on core business logic (pricing, auth, state transitions) |
| Security Risk | P0 | any hardcoded_credential, injection_risk, or unsafe_deserialization |

## Code Smells Quick Reference

### Bloaters (Code that's too big)

| Smell | Detection Rule | Quick Fix |
|-------|---------------|-----------|
| Long Method | > 20 lines | Extract Method |
| Large Class | > 200 lines or > 20 methods | Extract Class |
| Primitive Obsession | Related primitives used together | Introduce Value Object |
| Long Parameter List | > 4 parameters | Introduce Parameter Object |
| Data Clumps | Same data group in multiple places | Extract Class |

### Object-Orientation Abusers

| Smell | Detection Rule | Quick Fix |
|-------|---------------|-----------|
| Switch Statements | Complex switch/if-else on type | Replace with Polymorphism |
| Temporary Field | Fields null in most states | Extract Class |
| Refused Bequest | Subclass ignores inheritance | Replace with Delegation |

### Change Preventers

| Smell | Detection Rule | Quick Fix |
|-------|---------------|-----------|
| Divergent Change | Class changes for multiple reasons | Split Class (SRP) |
| Shotgun Surgery | One change touches many classes | Move methods/fields |

### Dispensables

| Smell | Detection Rule | Quick Fix |
|-------|---------------|-----------|
| Duplicate Code | Similar code in 2+ places | Extract Method/Class |
| Lazy Class | < 3 methods, < 50 lines | Inline or remove |
| Data Class | Only getters/setters | Add behavior, encapsulate |
| Dead Code | Unused methods/variables | Delete |
| Speculative Generality | Unused abstractions | Collapse hierarchy |

### Couplers

| Smell | Detection Rule | Quick Fix |
|-------|---------------|-----------|
| Feature Envy | Method uses other class more | Move Method |
| Inappropriate Intimacy | Classes access private details | Reduce coupling |
| Message Chains | a.b.c.d calls | Hide Delegate |
| Middle Man | Mostly delegates | Remove or inline |
