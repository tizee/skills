---
name: autoresearch
description: Set up and run an autonomous experiment loop for any optimization target. Gathers what to optimize, then starts the loop. Use when asked to "run autoresearch", "optimize X in a loop", "set up autoresearch for X", or "start experiments".
argument-hint: "<optimization goal>"
---

# Autoresearch

Autonomous experiment loop: try ideas, keep what works, discard what doesn't, never stop.

Use $ARGUMENTS to understand what the user wants to optimize.

## Tools

- **`InitExperiment`** — configure session (name, metric, unit, direction). Call again to re-initialize when the optimization target changes.
- **`RunExperiment`** — runs command, times it, captures output, parses `METRIC name=value` lines.
- **`LogExperiment`** — records result. `keep` auto-commits. `discard`/`crash` auto-reverts code changes (autoresearch files preserved).

## Setup

1. Ask (or infer): **Goal**, **Command**, **Metric** (+ direction), **Files in scope**, **Constraints**.
2. `git checkout -b autoresearch/<goal>-<date>`
3. Read the source files. Understand the workload deeply before writing anything.
4. Write `autoresearch.md` and `autoresearch.sh` (see below). Commit both.
5. `InitExperiment` → run baseline → `LogExperiment` → start looping immediately.

### `autoresearch.md`

This is the heart of the session. A fresh agent with no context should be able to read this file and run the loop effectively. Invest time making it excellent.

```markdown
# Autoresearch: <goal>

## Objective
<Specific description of what we're optimizing and the workload.>

## Metrics
- **Primary**: <name> (<unit>, lower/higher is better)
- **Secondary**: <name>, <name>, ...

## How to Run
`bash autoresearch.sh` — outputs `METRIC name=number` lines.

## Files in Scope
<Every file the agent may modify, with a brief note on what it does.>

## Off Limits
<What must NOT be touched.>

## Constraints
<Hard rules: tests must pass, no new deps, etc.>

## What's Been Tried
<Update this section as experiments accumulate. Note key wins, dead ends,
and architectural insights so the agent doesn't repeat failed approaches.>
```

Update `autoresearch.md` periodically — especially the "What's Been Tried" section — so resuming agents have full context.

### `autoresearch.sh`

Bash script (`set -euo pipefail`) that: pre-checks fast (syntax errors in <1s), runs the benchmark, outputs `METRIC name=value` lines to stdout. These lines are automatically parsed by `RunExperiment` — the primary metric (matching `InitExperiment`'s `metric_name`) and any secondary metrics are extracted and suggested as exact values for `LogExperiment`. Keep the script fast — every second is multiplied by hundreds of runs.

Example:

```bash
#!/bin/bash
set -euo pipefail

# Pre-check: fast syntax validation
python -m py_compile main.py

# Run benchmark
python benchmark.py 2>/dev/null

# Output is expected to contain lines like:
# METRIC total_ms=152
# METRIC memory_mb=34.5
```

**For fast, noisy benchmarks** (< 5s), run the workload multiple times inside the script and report the median. Slow workloads (ML training, large builds) don't need this.

## Loop Rules

**LOOP FOREVER.** Never ask "should I continue?" — the user expects autonomous work.

- **Primary metric is king.** Improved -> `keep`. Worse/equal -> `discard`. Secondary metrics rarely affect this.
- **Simpler is better.** Removing code for equal perf = keep. Ugly complexity for tiny gain = probably discard.
- **Don't thrash.** Repeatedly reverting the same idea? Try something structurally different.
- **Crashes:** fix if trivial, otherwise log and move on. Don't over-invest.
- **Think longer when stuck.** Re-read source files, study the profiling data, reason about what the system is actually doing. The best ideas come from deep understanding, not from trying random variations.
- **Resuming:** if `autoresearch.md` exists, read it + git log, continue looping.

**NEVER STOP.** The user may be away for hours. Keep going until interrupted.

## Ideas Backlog

When you discover complex but promising optimizations that you won't pursue right now, **append them as bullets to `autoresearch.ideas.md`**. Don't let good ideas get lost.

On resume (context limit, crash), check `autoresearch.ideas.md` — prune stale/tried entries, experiment with the rest.

## User Messages During Experiments

If the user sends a message while an experiment is running, finish the current `RunExperiment` + `LogExperiment` cycle first, then incorporate their feedback in the next iteration. Don't abandon a running experiment.

## Context Conservation

- Redirect verbose command output: `command > /tmp/output.log 2>&1` when not using `RunExperiment`.
- Use `RunExperiment` for all benchmark runs — it handles output truncation automatically.
- Keep `autoresearch.md` concise but complete — it's your lifeline on resume.
- Do NOT read large files unnecessarily between experiments.
