---
name: cli-agent-ux-review
description: Review a CLI tool's source code for AI agent friendliness and Agent Experience (AX) quality. Use this skill when working inside a CLI tool's repository and the user wants to evaluate how well the tool works when operated by AI agents rather than humans directly. Triggers on phrases like "agent-friendly", "AX review", "agent experience", "agent-ux", "cli review for agents", or any request to assess whether a CLI tool is easy for coding agents to use, parse, and operate reliably. Also use when someone asks about improving a CLI tool's output format, error handling, or automation story from an agent's perspective.
context: fork
agent: Explore
---

# CLI Agent-UX Review

You are reviewing a CLI tool's codebase to assess how well it serves AI agents as first-class users. Agents interact with CLI tools differently from humans — they read stdout programmatically, they cannot visually scan layouts, they struggle with ambiguous error messages, and they burn tokens on noisy output. A tool that is pleasant for humans may be hostile to agents.

The goal is a prose review that helps the tool's author understand what works, what doesn't, and what to change — written from the perspective of an agent that has to operate this tool day after day.

## How to conduct the review

### 1. Orient yourself in the repo

Read the README, top-level help output (`--help`), and skim the command structure. Understand what the tool does, who it's for, and what its main commands are. Identify the programming language and CLI framework in use (e.g., `clap`, `cobra`, `click`, `commander`, `argparse`).

### 2. Evaluate along the AX dimensions

Work through each dimension in [references/ax-criteria.md](references/ax-criteria.md). You don't need to cover every single point — focus on what's actually relevant to this tool. Skip criteria that don't apply (e.g., credential handling for a tool that doesn't authenticate).

For each dimension, look at the actual source code. Don't just check if `--json` exists as a flag — look at what it actually outputs, whether it's consistent across commands, whether error cases also produce structured output.

### 3. Write the review

Structure the review as follows:

```
# AX Review: <tool-name>

## Summary
Two to three sentences. What does this tool do, and what's the overall verdict
on agent-friendliness? Is it ready for agent use, needs work, or fundamentally
hostile?

## What works well
Things the tool already does right for agents. Be specific — cite commands,
flags, output examples. Agents and their operators need to know what they can
rely on.

## Key findings
The meat of the review. Organize by theme (output format, error handling,
credential safety, etc.) rather than by checklist item. Each finding should
explain:
- What the current behavior is (with file:line references)
- Why it's a problem for agents specifically
- What a better approach looks like

Lead with the findings that have the highest impact on agent task success rate.

## Quick wins
Concrete, low-effort changes that would meaningfully improve AX. Think of these
as a prioritized punch list the author could work through in a day.

## Closing notes
Any broader architectural observations. Is the tool's design fundamentally
agent-friendly and just needs polish, or does the output/interaction model
need rethinking?
```

### What to avoid

- **Scored rubrics.** They create false precision and invite gaming. Prose forces you to actually think about what matters.
- **Exhaustive checklists.** Not every dimension applies to every tool. A tool with no auth doesn't need a credential section.
- **Generic advice.** "Consider adding structured output" is useless. Show exactly which commands need it and what the JSON shape should look like.
- **Human UX concerns.** This review is about agents. A beautiful `--help` layout with ANSI colors is actually a negative if the tool doesn't offer a way to suppress them (agents parse ANSI escape codes as garbage tokens).

## Reference

| Topic | File |
| --- | --- |
| AX evaluation criteria | [references/ax-criteria.md](references/ax-criteria.md) |
| Why CLI beats API + curl for agents | [references/cli-vs-curl.md](references/cli-vs-curl.md) |
