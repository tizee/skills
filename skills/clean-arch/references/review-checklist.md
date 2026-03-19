# Clean Architecture Review Checklist

## Table of Contents

- Severity rubric (`P0`..`P3`)
- Layer boundary checks (clean architecture)
- Cross-layer business logic chaos patterns
- YAGNI misapplication: deferring layer violations
- SOLID review checks
- Module depth checks (deep vs shallow)
- Information hiding and leakage checks
- KISS / over-engineering checks (from `kiss`)
- Production robustness checks
- Code smells quick reference
- Testing best practices
- Reporting heuristics

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
