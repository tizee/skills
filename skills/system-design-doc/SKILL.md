---
name: system-design-doc
description: Analyze a software project's source code and write a grounded design/implementation document, author a new forward-looking design doc before writing code, or use the embedded principles as a guide for evaluating any design doc. Use this skill whenever the user wants to understand, learn, study, or document how a system/feature/subsystem is architected (e.g. "how does X work in this repo", "document the architecture of the Y subsystem", "reverse-engineer the Z system", "explain the design of feature W"), OR wants to plan and write a new design doc before implementation (e.g. "write a design doc for X", "draft a design for this feature", "I need a design doc to coordinate this work"), OR wants design-doc writing principles and a review checklist. Triggers on requests to analyze/learn from/document a system's internals, to plan a new system's design, or to review a design doc for completeness. Output follows a house format with ASCII/Unicode (or mermaid) flowcharts, a key-file index, behavioral contracts, and a BDD scenario table, validated against checklist.md.
---

# System Design Doc

Produce a single self-contained design/implementation document for a software system — either by reading existing source and capturing how it actually works, or by planning a new system before any code exists. The same house format, diagram discipline, and behavioral-contract rigor apply to both. The skill also doubles as a principles guide and review checklist for any design doc.

A good design doc saves development time: when *documenting* existing code it lets a reader learn the design without re-reading source; when *planning* new code it forces hard decisions to surface before they solidify into the wrong implementation. Either way the reader wants the *why* and the *what must be true*, the data flow as a picture, and a map of where things live.

## Two Modes

Pick the mode from the user's intent. If unclear, ask.

| | **Mode A — Document existing system** | **Mode B — Author new design** |
|---|---|---|
| Trigger | "how does X work", "document/reverse-engineer Y" | "write a design doc for X", "plan this feature" |
| Source of truth | the actual code you read | the problem, constraints, and decisions you reason through |
| Core risk | hallucinating how you *assume* it works | over-specifying (writing the implementation in the design phase) |
| Deliverable | grounded doc, every claim traceable to `path:symbol` | forward design doc, decisions weighted by cost-of-getting-wrong |

Both modes finish by validating the draft against **[`checklist.md`](checklist.md)** before writing the file.

## When to Use

- **Mode A** when the user wants to understand/capture the design of a feature inside a project (locally cloned repo, open-source or internal). If they have not named a feature, ask which subsystem to study — produce a *focused* doc about one mechanism, not the whole project.
- **Mode B** when the user wants to plan a system before building it. Investing in a design doc pays off when: multiple people coordinate the work, the project runs for years, goals are ambiguous, or there are catastrophic risks (security, legal) preventable at design time. For a trivial, easily-reversible decision, a design doc may not be worth writing at all — say so.
- **As a guide** when the user wants principles or a checklist to write/review a design doc themselves. Point them at the Principles section and `checklist.md`.

## Output Location

Write the doc to `./analysis/<name>.md` relative to the current working directory unless the user specifies another path. Create the `analysis/` directory if it does not exist. Use a short kebab-case `<name>` derived from the feature/system (e.g. `event-loop`, `auth-token-refresh`, `recency-bank`).

## Mode A Workflow — Document existing system

The order matters: ground yourself in evidence *before* writing prose. Writing first invites hallucination — you will fill gaps with how you *assume* the framework works rather than how *this* project works.

### A1. Scope the feature

Pin down exactly what to learn. One sentence: "How does `<feature>` work in this repo?" If ambiguous, ask. Note adjacent things explicitly out of scope so the doc stays focused.

### A2. Map the territory (read-led, not guess-led)

Find the real entry points and trace the flow. Bias toward retrieval over recall:

- `Glob` for candidate files by name/path; `Grep` for symbols, strings, config keys; structural search for definitions, call sites, implementations.
- Read the actual files. Follow the call chain across module boundaries until you can explain the flow end to end.
- Note the precise `path:symbol` for every important hop — you will cite these.
- Read any existing docs/README for *design intent*, but verify intent against code; docs drift.

You may delegate code-tracing (find usages, locate call sites) to subagents. Do the synthesis and writing yourself — the narrative is the value.

### A3. Distinguish contract from implementation

Before writing, separate what is **durable** from what is **incidental**. This is the single most important judgment in the doc.

| Durable (lead with this) | Incidental (mention, do not center) |
|--------------------------|--------------------------------------|
| Why the feature exists, the problem it solves | Exact field counts, struct layouts |
| Invariants that must hold | Specific function names as the structure |
| Decision/data flow shape | Parameter signatures |
| State transitions and their guarantees | Test counts, line numbers as facts |

You are documenting a project you do not control. Implementation-shaped claims ("a 14-field struct", "calls `doFooBar()`") rot the moment upstream refactors. Contract-shaped claims ("the buffer must be flushed before the lock releases") survive. Reference implementation details by pointing at the code, not by transcribing them as the contract.

**Cite symbols, not line ranges.** Anchor each claim to a durable locator: a file plus a function/type/symbol name (`dispatch()` in `rpc.lua`, `M.connect`), because names survive edits that line numbers do not. A doc full of `foo.lua:198–210` is wrong within one refactor. If a line number helps a reader jump, treat it as an approximate hint (`rpc.lua` around L200, in the socket read loop), never as the proof of a contract. The proof is the named symbol and the behavior.

### A4. Write the doc

Use the [reverse-engineering template](#mode-a-template) for section order. Fill every applicable section; drop one only if it genuinely does not apply.

### A5. Verify grounding

Re-read the draft against the source. For each flowchart node, file-index row, and contract: can you point at the code that proves it? Delete or fix anything you cannot ground, then run [`checklist.md`](checklist.md) and write the file.

## Mode B Workflow — Author a new design

Reason through decisions *before* writing them down, weighting each by the penalty for being wrong. The risk here is the opposite of Mode A: over-specification. If you pin down every detail you have written the implementation in the design phase, defeating the purpose.

### B1. Right-size the investment

Decide how much doc the project warrants (one-pager vs multi-team signoff). State the chosen depth. Skip sections that do not apply — most docs need only a subset.

### B2. Frame problem and scope

Write the **objective** (one sentence), **background** (why now, what problem, prior attempts), **goals** (in terms of user/team/company impact, never internal implementation like "add Kubernetes"), and **non-goals** (what readers might wrongly assume is in scope). Goals must connect logically to the background.

### B3. Make decisions, weighted by cost-of-wrong

For each design decision ask: **what's the penalty for being wrong?** Hard-to-reverse choices (language, storage backend, public interface, trust boundaries) deserve detailed reasoning and an *alternatives considered* note. Easily-reversible choices ("load more" vs pagination) do not belong in the doc — do not burn review cycles on them.

### B4. Specify the durable surfaces

Cover the sections whose cost-of-wrong is high: **scenarios** (concrete walk-throughs of the finished system), **interfaces** (API/CLI/file-format/UI sketches), **constraints**, **dependencies/infrastructure**, and where relevant **SLOs + monitoring**, **security**, **privacy**, **legal**, **logging**. Record unresolved tensions in **open issues**; move them to **resolved issues** (retaining the discussion) as you settle them.

### B5. Draw it and validate

Add the diagrams (B5 is not optional — see Diagrams in the checklist), write the BDD scenario table, then run [`checklist.md`](checklist.md) and write the file.

## Shared Foundations

These apply to both modes and are enforced by `checklist.md`.

### Diagrams are mandatory

The flowchart is what makes a design *click* — invest here. As the author you see the architecture in your head; the reader does not, so draw it. Cover at least: how data flows through the system, how components fit together, and how the system meets its dependencies and clients. See [Flowchart Conventions](#flowchart-conventions).

### BDD scenarios are mandatory

Every behavior-oriented doc ends with a BDD scenario table describing observable behavior in Given/When/Then. In Mode A they are derived from reading the code (and tests); in Mode B they specify intended behavior. They serve as both design spec and test acceptance criteria. Use the table form:

```
### BDD Scenarios

| # | Scenario | Given | When | Then |
|---|----------|-------|------|------|
| 1 | Short name | Pre-conditions | Action/trigger | Expected observable outcome |
```

Scenarios must be testable against the real system, not pseudocode. Where a test framework exists, each should map to a concrete test function name.

### Contracts over implementation

Lead with what must be true and why. Prefer durable claims over fragile ones:

- Fragile (avoid): field counts ("a 14-field struct"), variant/test counts, exhaustive name-to-name mapping tables, per-file source tables as the backbone, `file:line` references as proof.
- Durable (prefer): "a domain entity with visibility queries"; "the bridge is an exhaustive 1:1 mapping; see code for current pairs"; "the token reset zeroes accumulators while preserving cumulative totals".

Naming a central type as a landmark is fine; enumerating its shape is not.

## Document Templates

### Mode A template

```markdown
---
updated: YYYY-MM-DD
source: <repo name or URL>  @ <commit-ish or branch>
---

# <Feature Name>

<1-2 sentence behavioral summary: what this feature does and the problem it solves.
Lead with the contract, no preamble.>

## Source Files

| File | Role |
|------|------|
| `path/to/core.ext` | <one-line role> |

## Design Rationale

**Problem:** <what was broken / missing / hard before this design>
**Solution:** <the approach this project chose, and the key insight>
<Optional: alternatives the design implicitly rejects and why this one wins.>

## Architecture

<Prose orientation: name the main components and how they relate. 3-6 sentences.>

### Data / Control Flow

<Flowchart. This is the centerpiece — show the real path from trigger to effect.>

## Behavioral Contracts

<The invariants and guarantees that must hold. The durable heart of the doc.>

- <Invariant 1> (see `dispatch()` in `file.ext`)
- <Invariant 2>

## Key Mechanisms

### <Mechanism A>

<Explain *why* it works this way. Quote the project's real code where it clarifies;
do not paraphrase into pseudocode that hides the truth.>

## BDD Scenarios

| # | Scenario | Given | When | Then |
|---|----------|-------|------|------|
| 1 | <observable behavior> | <precondition> | <trigger> | <outcome> |

## Key Files

| File | Purpose |
|------|---------|
| `path/to/core.ext` | <purpose, optionally function/region> |

## Open Questions

<Things you could not resolve from source alone — unclear intent, dead code, TODOs,
behavior needing runtime confirmation. Honest gaps beat confident guesses.>
```

### Mode B template

Include the subset of sections whose cost-of-getting-wrong justifies them (see `checklist.md`). The common skeleton:

```markdown
---
title: <short, distinctive, evocative project name>
author: <name + email>
status: <draft | ready for review | approved>
created: YYYY-MM-DD
url: <authoritative link>
---

# <Project Name>

## Objective

<One sentence any stakeholder understands.>

## Background

<Why now, what problem, prior attempts.>

## Goals

<Impact on user/team/company. Never internal implementation details.>

## Non-goals

<What readers might wrongly assume is in scope, with a one-line reason each.>

## Scenarios

<Concrete walk-throughs of the finished system in the real world.>

## Diagrams

<Architecture + data-flow diagrams. See Flowchart Conventions.>

## Interfaces

<API/CLI semantics, file formats, or UI sketches.>

## Constraints

<Budget/client/infra/dependency constraints that shape the design.>

## Dependencies / Infrastructure

<Languages, hardware/services, persistence. Weight by cost-of-change.>

## Behavioral Contracts

<Invariants the implementation must satisfy.>

## BDD Scenarios

| # | Scenario | Given | When | Then |
|---|----------|-------|------|------|
| 1 | <name> | <precondition> | <trigger> | <outcome> |

<Optional, include when relevant: SLOs, Monitoring/Alerting, Security, Privacy,
Legal, Logging, Timeline, Glossary.>

## Alternatives Considered

<Strong alternatives and why they did not win. A few lines each, not an essay.>

## Open Issues

<Outstanding problems: the problem, options, and the immediate next step.>

## Resolved Issues

<Settled decisions with the original discussion retained for posterity.>
```

## Flowchart Conventions

Make diagrams readable in a monospace terminal. ASCII/Unicode box-drawing is the default; mermaid is acceptable where the renderer supports it (keep mermaid node labels on one line and quote any label containing `()`, `:`, or punctuation).

**Linear / layered flow** — vertical, arrows down:

```
User input
  |
  v
Dispatcher  --(no match)-->  Fallback handler
  |
  v
Handler.run()
  |
  +-- side effect: write to store
  |
  v
Result returned
```

**Branching / decision flow** — show the fork:

```
        Request arrives
              |
              v
      Cache has entry?
        /          \
      Yes           No
       |             |
       v             v
   Return cached   Fetch + populate cache
```

**Component / boxed architecture** — box-drawing for subsystem boundaries:

```
┌─────────────────────────────────────────────┐
│              Subsystem Name                   │
├─────────────────────────────────────────────┤
│  Producer ──► Queue ──► Consumer              │
│                 │                             │
│                 ▼                             │
│             Backpressure signal               │
└─────────────────────────────────────────────┘
```

Rules:
- Pick one style per diagram; do not mix box-drawing and ASCII arrows arbitrarily.
- Keep width under ~75 columns so it does not wrap in narrow terminals.
- Label edges when the branch condition matters (`--(timeout)-->`, `-->|timeout|`).
- The diagram must reflect the *real* path (Mode A) or the *intended* path (Mode B), not an idealized blur.
- **Prefer several small, single-purpose diagrams over one mega-diagram.** Each answers exactly one question ("how is a message routed?", "what happens on a cache miss?"). Split when a diagram exceeds ~12 rows or has crossing lines. Three legible pictures teach more than one exhaustive tangle.

## Principles

1. **Grounded or gone (Mode A).** Every structural claim maps to code you read. If you cannot cite it, do not assert it — put genuine uncertainty in Open Questions.
2. **Cost-of-wrong drives depth (Mode B).** Detail the decisions that are expensive to reverse; omit the trivially-reversible ones. Specifying everything is writing the implementation early.
3. **Contract over implementation.** Lead with what must be true and why. Reference function/field details by pointing at code, not by transcribing them as the backbone — code refactors and transcriptions rot.
4. **One system/feature, deep.** A focused doc that fully explains one mechanism beats a shallow survey of ten.
5. **Why before what before how.** Rationale first, then contracts/flow, then mechanism detail.
6. **Pictures and scenarios are not optional.** A design without a diagram and a BDD table is a draft, not a design doc.
7. **Honest gaps.** A clearly marked Open Question or Open Issue beats a confident fabrication.

Validate every doc against **[`checklist.md`](checklist.md)** before finalizing.
