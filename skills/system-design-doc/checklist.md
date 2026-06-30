# Design Doc Checklist

A review gate for any design doc produced or evaluated with the `system-design-doc` skill. Run it before finalizing. Each item is a pass/fail question — if you cannot answer "yes" (or "n/a with reason"), fix the doc first.

Items tagged **[A]** apply mainly to Mode A (documenting existing source), **[B]** to Mode B (authoring a new design), and **[both]** to every doc. Supplementary reading: ["How to Write an Effective Software Design Document"](https://refactoringenglish.com/excerpts/write-an-effective-design-doc/) (mtlynch).

## 0. Decide whether a doc is warranted [B]

A design doc is worth the effort when *any* of these hold; almost certainly worth it when *two or more* do:

- [ ] Multiple people coordinate work to implement the design.
- [ ] The project takes more than ~3 months of full-time dev work.
- [ ] The implementation will run in production for several years.
- [ ] The work spans teams.
- [ ] Goals and requirements are ambiguous.
- [ ] There are catastrophic risks preventable at design time (security, legal, data loss).

If none apply, say so — the right investment may be zero. Then right-size: one-pager vs multi-team signoff.

## 1. Framing and scope

- [ ] **Objective** is one sentence any stakeholder understands. [both]
- [ ] **Background / Design Rationale** explains *why now*, the problem, and prior attempts. [both]
- [ ] **Goals** are stated as user/team/company impact, never internal implementation ("minimize deploy outages", not "add Kubernetes"). [B]
- [ ] **Non-goals** list what a reader might wrongly assume is in scope, each with a one-line reason. [B]
- [ ] Scope is *focused* — one feature/mechanism deep, not a shallow survey of the whole project. [A]
- [ ] Adjacent out-of-scope concerns are named explicitly. [both]

## 2. Cost-of-getting-wrong filter [B]

For every decision in the doc, ask "what's the penalty for being wrong?"

- [ ] Hard-to-reverse choices (language, storage backend, public interface, trust boundaries, data model) are reasoned through and justified.
- [ ] Easily-reversible choices ("load more" vs pagination, copy, button placement) are **excluded** — they do not belong in a design doc and waste review cycles.
- [ ] The doc does not over-specify to the point of being the implementation written early.

## 3. Grounding and resilience [both, A-critical]

- [ ] Every structural claim maps to code actually read (Mode A) or a stated decision (Mode B). Nothing asserted that cannot be backed up.
- [ ] Claims are anchored to **durable locators** — file + function/type/symbol name — not `file:line` ranges presented as proof.
- [ ] **Contracts lead, implementation follows.** Invariants and guarantees ("the buffer must flush before the lock releases") come before incidental detail.
- [ ] No fragile transcriptions used as the backbone: field counts, struct layouts, variant/test counts, exhaustive name-to-name mapping tables, per-file source tables as structure.
- [ ] Durable phrasings preferred (e.g. "an exhaustive 1:1 mapping; see code for current pairs" rather than enumerating every pair).
- [ ] Naming a central type as a landmark is fine; its full shape is not enumerated.

## 4. Diagrams (mandatory)

- [ ] At least one diagram exists. A design with no picture is a draft, not a design doc. [both]
- [ ] Diagrams cover the questions that matter: how data flows, how components fit together, how the system meets dependencies and clients. [both]
- [ ] One style per diagram; box-drawing and ASCII arrows are not mixed arbitrarily. [both]
- [ ] Lines stay under ~75 columns (no wrapping in narrow terminals). [both]
- [ ] Branch/edge conditions are labeled where they matter (`--(timeout)-->`, `-->|timeout|`). [both]
- [ ] The diagram reflects the **real** traced path (Mode A) or the **intended** path (Mode B), not an idealized blur. [both]
- [ ] Several small single-purpose diagrams used instead of one mega-diagram; any diagram over ~12 rows or with crossing lines is split. [both]
- [ ] mermaid node labels (if used) stay on one line; labels containing `()`, `:`, or punctuation are quoted. [both]
- [ ] If using an editable diagram tool, the source (code/file) is linked so reviewers can reproduce it. [B]

## 5. Behavioral contracts and BDD scenarios (mandatory)

- [ ] A **Behavioral Contracts** section lists the invariants/guarantees that must hold for correctness. [both]
- [ ] A **BDD scenario table** is present at the end, in Given/When/Then form:

  ```
  | # | Scenario | Given | When | Then |
  |---|----------|-------|------|------|
  | 1 | Short name | Pre-conditions | Action/trigger | Expected observable outcome |
  ```

- [ ] Scenarios describe **observable behavior**, testable against the real system — not pseudocode. [both]
- [ ] Scenarios cover the happy path **and** edge cases. [both]
- [ ] Where a test framework exists, each scenario maps to a concrete test function name. [both]

## 6. Interfaces and surfaces [B, include when relevant]

- [ ] **Scenarios** paint concrete walk-throughs of the finished system in the real world.
- [ ] **Interfaces** specify API/CLI semantics, file formats, or UI sketches (sketches, not pixel-perfect mockups).
- [ ] **Constraints** explain budget/client/infra/dependency limits that shape the design.
- [ ] **Dependencies / infrastructure** name languages, hardware/services, and persistence, weighting attention by cost-of-change.

## 7. Operability and risk [B, include when relevant]

- [ ] **SLOs** stated as measurable, objective targets (uptime, latency percentiles, scale) — not vague ("performant").
- [ ] **Monitoring / alerting** describes how SLO breaches and other critical events are detected.
- [ ] **Security**: threats considered, attack surface, and trust boundaries documented (even "no threats because…" with rationale).
- [ ] **Privacy**: sensitive data handled, retention, access, and protection (encryption at rest/in transit).
- [ ] **Legal**: regulatory/contractual/open-source-license considerations addressed where applicable.
- [ ] **Logging**: critical events, levels, storage, retention, access, and excluded sensitive data.
- [ ] **Timeline / milestones** chosen to produce useful intermediate artifacts (if coordinating work).

## 8. Decisions and gaps

- [ ] **Alternatives considered** briefly note strong rejected options and why they lost (a few lines each, not an essay). [B]
- [ ] **Open Questions / Open Issues** honestly record what is unresolved — problem, options, immediate next step. [both]
- [ ] Resolved decisions are moved to **Resolved Issues** with the original discussion retained. [B]
- [ ] No confident fabrication papering over a genuine gap. [both]

## 9. Conventions and housekeeping [both]

- [ ] Doc starts with YAML frontmatter (Mode A: `updated`, `source @ commit/branch`; Mode B: `title`, `author`, `status`, `created`, `url`).
- [ ] **Title** is short, distinctive, and evocative (Mode B).
- [ ] A **glossary** defines internal/unfamiliar terms, or such terms are defined inline.
- [ ] An early **source/file index** (Mode A) and a closing **Key Files** map orient follow-up reading.
- [ ] Section order follows the house template; sections dropped only when genuinely n/a.
- [ ] Prose follows "why before what before how."
