---
name: repo-feature-design-doc
description: Reverse-engineer a feature, subsystem, or characteristic from an unfamiliar codebase (open-source or internal) and produce a grounded design/implementation document. Use this skill whenever the user wants to understand, learn, study, or document how some feature is architected and implemented in a project they did not write — e.g. "how does X work in this repo", "document the architecture of the Y subsystem", "reverse-engineer the Z system", "explain the design of feature W", "make a design doc for how this project does X", or any request to study a foreign codebase's internals and capture them as a structured design doc. Triggers on requests to analyze, learn from, or document a specific feature/mechanism inside someone else's source code, even when the user does not say the word "document". Output follows a strict house format with ASCII/Unicode flowcharts, a key-file index table, behavioral contracts, and BDD scenario tables.
context: fork
---

# Repo Feature Design Doc

Read an unfamiliar codebase, trace how one feature or subsystem actually works, and write a single self-contained design/implementation document that lets a reader understand and learn the design without re-reading the source.

The reader is someone studying the project to learn from it. They want the *why* and the *what must be true*, the data flow as a picture, and a map of where to look in the source. Every claim you write must be traceable to a real file and line in the target repo — an ungrounded design doc is worse than no doc.

## When to Use

Use this when the user wants to understand and capture the design of a feature inside a project they did not author — typically a locally cloned git repo (open-source or an internal codebase). The deliverable is a Markdown design doc, not a code change.

If the user has not named a feature, ask which feature/subsystem to study before investigating. Do not document the whole project — this skill produces a *focused* doc about one mechanism.

## Output Location

Write the doc to `./analysis/<feature-name>.md` relative to the current working directory unless the user specifies another path. Create the `analysis/` directory if it does not exist. Use a short kebab-case `<feature-name>` derived from the feature (e.g. `event-loop`, `auth-token-refresh`, `compaction`).

## Workflow

The order matters: ground yourself in evidence *before* writing prose. Writing first invites hallucination — you will fill gaps with how you *assume* the framework works rather than how *this* project works.

### 1. Scope the feature

Pin down exactly what the user wants to learn. One sentence: "How does <feature> work in this repo?" If ambiguous, ask. Note adjacent things explicitly out of scope so the doc stays focused.

### 2. Map the territory (read-led, not guess-led)

Find the real entry points and trace the flow. Bias toward retrieval over recall:

- `Glob` for candidate files by name/path; `Grep` for symbols, strings, config keys; `CodeGrep` for structural matches (definitions, call sites, implementations).
- Read the actual files. Follow the call chain across module boundaries until you can explain the flow end to end.
- Note the precise `path:line` for every important hop — you will cite these in the doc.
- Read any existing docs/README in the repo for *design intent*, but verify intent against code; docs drift.

You may delegate code-tracing (find usages, locate call sites) to subagents. Do the synthesis and writing yourself — the narrative is the value.

### 3. Distinguish contract from implementation

Before writing, separate what is **durable** from what is **incidental**. This is the single most important judgment in the doc.

| Durable (lead with this) | Incidental (mention, do not center) |
|--------------------------|--------------------------------------|
| Why the feature exists, the problem it solves | Exact field counts, struct layouts |
| Invariants that must hold | Specific function names as the structure |
| Decision/data flow shape | Parameter signatures |
| State transitions and their guarantees | Test counts, line numbers as facts |

Reason: you are documenting a project you do not control. Implementation-shaped claims ("a 14-field struct", "calls `doFooBar()`") rot the moment upstream refactors. Contract-shaped claims ("the buffer must be flushed before the lock releases") survive. Reference implementation details by pointing at the code, not by transcribing them as if they were the contract.

**Citation granularity — cite symbols, not line ranges.** When grounding a claim, anchor it to a durable locator: a file plus a function/type/symbol name (`dispatch()` in `rpc.lua`, `M.connect`), because names survive edits that line numbers do not. Exact line numbers drift on every insertion above them, so a doc full of `foo.lua:198–210` is wrong within one refactor. If a line number genuinely helps a reader jump to a spot, treat it as an approximate hint (`rpc.lua` around L200, in the socket read loop) and never as the proof of a contract. The proof is the named symbol and the behavior, not the line.

### 4. Write the doc

Use the house template below verbatim for section order. Fill every applicable section; drop a section only if it genuinely does not apply (e.g. no UI). Quality of the flowcharts and prose depends on your own judgment and care — there is no template that substitutes for actually understanding the flow.

### 5. Verify grounding

Re-read your draft against the source. For each flowchart node, file-index row, and contract: can you point at the code that proves it? Delete or fix anything you cannot ground. Then write the file.

## Document Template

Reproduce this structure. It mirrors a durable-design-doc house style: behavioral summary first, source map early, pictures for flow, contracts over implementation, BDD scenarios as executable spec, key-file index last.

```markdown
---
updated: YYYY-MM-DD
source: <repo name or URL>  @ <commit-ish or branch>
---

# <Feature Name>

<1-2 sentence behavioral summary: what this feature does and the problem it solves.
No preamble, lead with the contract.>

## Source Files

<Early orientation table — where the reader should look. Keep it to the files that
actually carry the feature, not every file touched.>

| File | Role |
|------|------|
| `path/to/core.ext` | <one-line role> |
| `path/to/other.ext` | <one-line role> |

## Design Rationale

**Problem:** <what was broken / missing / hard before this design>

**Solution:** <the approach this project chose, and why — the key insight>

<Optional: alternatives the design implicitly rejects and why this one wins.>

## Architecture

<Prose orientation: name the main components and how they relate. 3-6 sentences.>

### Data / Control Flow

<ASCII or Unicode box-drawing flowchart. See "Flowchart Conventions" below.
This is the centerpiece — invest here. Show the real path from trigger to effect.>

## Behavioral Contracts

<The invariants and guarantees that must hold for the feature to be correct.
These are the durable heart of the doc. Bullet list of "X must be true" statements,
each grounded in code.>

- <Invariant 1> (see `file.ext:NN`)
- <Invariant 2>

## Key Mechanisms

<One subsection per non-obvious mechanism. Explain *why* it works this way.
Include small, illustrative code excerpts only where they clarify — quote the
project's real code, do not paraphrase into pseudocode that hides the truth.>

### <Mechanism A>

<Explanation + grounded reference. Optional decision-flow diagram for branching logic.>

## BDD Scenarios

<Describe observed behavior as Given/When/Then. These read as a spec of what the
feature does, derived from reading the code (and tests, if present). They let a
reader confirm their mental model. Use Gherkin.>

```gherkin
Feature: <feature behavior>

  Scenario: <observable behavior 1>
    Given <precondition>
    When <trigger>
    Then <observable outcome>

  Scenario: <edge case>
    Given <precondition>
    When <trigger>
    Then <observable outcome>
```

## Key Files

<Closing index: the authoritative map for follow-up reading. May overlap with
Source Files but can be more granular (specific functions/regions).>

| File | Purpose |
|------|---------|
| `path/to/core.ext` | <purpose, optionally :line or function> |

## Open Questions

<Things you could not resolve from the source alone — unclear intent, dead code,
TODOs in the repo, behavior that needs runtime confirmation. Honest gaps beat
confident guesses.>
```

## Flowchart Conventions

The flowchart is what makes the design *click* for a reader, so make it readable in a monospace terminal.

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
│                                               │
│  Producer ──► Queue ──► Consumer              │
│                 │                             │
│                 ▼                             │
│             Backpressure signal               │
│                                               │
└─────────────────────────────────────────────┘
```

Rules:
- Pick one style per diagram; do not mix box-drawing and ASCII arrows arbitrarily.
- Keep width under ~75 columns so it does not wrap in narrow terminals.
- Label edges when the branch condition matters (`--(timeout)-->`).
- The diagram must reflect the *real* path you traced, not an idealized one.
- **Prefer several small, single-purpose diagrams over one mega-diagram.** A box that nests a full decision tree inside a transport-routing layout becomes an unreadable tangle of crossing lines. If a diagram needs more than ~12 rows or has lines that cross, split it: one diagram for the top-level data flow, a separate one for the decision logic, another for a key sub-mechanism. Each diagram should answer exactly one question ("how does a message get routed?", "what happens on a cache miss?"). Clarity beats completeness — a reader learns more from three legible pictures than one exhaustive one.

## Principles

1. **Grounded or gone.** Every structural claim maps to code you read. If you cannot cite it, do not assert it. Put genuine uncertainty in Open Questions.
2. **Contract over implementation.** Lead with what must be true and why. Reference function/field details by pointing at code, not by transcribing them as the doc's backbone — foreign code refactors and your transcription rots.
3. **One feature, deep.** A focused doc that fully explains one mechanism beats a shallow survey of ten.
4. **Why before what before how.** Rationale first, then contracts/flow, then mechanism detail. The reader is here to learn the design thinking, not just the code shape.
5. **Honest gaps.** A clearly marked Open Question is more useful than a confident fabrication.
