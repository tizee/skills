---
name: zhu-reinit
description: Review available recent Zhu-agent history and tool calls, then update the current repository's durable agent guidance with repeatedly needed facts and user-corrected conventions. Run only when the user explicitly invokes /zhu-reinit or names the zhu-reinit skill; never invoke automatically.
disable-model-invocation: true
user-invocable: true
---

# Zhu Reinit

Refresh the current repository's agent guidance from evidence in recent agent work. Preserve durable knowledge that will prevent repeated discovery or repeated user corrections. Do not turn temporary session state into permanent instructions.

## Workflow

1. Establish the repository root and scope all edits to that repository.
2. Read the recent conversation history available in the current session, emphasizing the preceding agent turns and their tool calls.
3. When the environment exposes session-history tools or local agent history through an established product interface, inspect the most recent relevant sessions. Use the reference path under "Local session-history location" as a starting point. Do not search unrelated home-directory data, credentials, caches, or other repositories merely to find more history.
4. Record candidate facts that the agent repeatedly had to discover, candidate conventions that affected its decisions, and corrections or preferences explicitly supplied by the user.
5. Read the applicable guidance files before proposing changes. Check `AGENTS.md`, `CLAUDE.md`, and their relevant ancestor or nested variants. Follow existing repository conventions for which file is canonical.
6. Verify factual candidates against the current repository using the cheapest authoritative source. Prefer manifests, configuration, existing documentation, and focused file inspection over repeating broad exploratory searches.
7. Apply the retention test below. Discard candidates that do not pass.
8. Update the canonical guidance file in place. Preserve existing content and structure, remove exact duplication, and make the smallest coherent edit.
9. Review the diff for accuracy, durability, scope, sensitive data, contradictions, and unnecessary verbosity.
10. Report which guidance file changed, what durable knowledge was added or corrected, and which tempting candidates were intentionally excluded. If nothing qualifies, make no edit and say so.

## Retention test

Add a fact or instruction only when all applicable conditions hold:

- It is relevant to future work in this repository.
- It is unlikely to change between ordinary tasks.
- It is not already stated in applicable guidance.
- It is specific enough to change or accelerate agent behavior.
- It is supported by current repository evidence or an explicit user preference.
- It either appeared repeatedly in recent discovery work, or represents a clear user correction or standing preference. One explicit correction is sufficient; incidental one-off behavior is not.

Good candidates commonly include:

- Authoritative build, test, lint, format, generation, and validation commands, including required ordering or working directories.
- Package-manager choice, workspace layout, important entry points, ownership boundaries, and non-obvious architectural relationships.
- Generated or vendored paths that should not be edited, and the source files or commands that regenerate them.
- Stable environment constraints, supported runtimes, or tool requirements that are pinned or enforced by repository configuration.
- Repository-specific coding, testing, naming, error-handling, compatibility, or review conventions that are not reliably inferable from nearby code.
- Standing user preferences that apply to future repository work, such as how to derive commit messages, what historical context to consult, or a consistently requested coding style.
- Recurring traps where the obvious command, directory, or implementation approach is wrong for this repository.

Exclude:

- Current branch, dirty files, uncommitted changes, open task state, temporary paths, timestamps, transient failures, and recent command output.
- Guesses based only on the agent checking something once.
- Facts that are cheap and obvious from the file currently being edited unless agents repeatedly need them to orient themselves.
- Exhaustive directory trees, dependency inventories, file-by-file descriptions, tutorials, or generic software-engineering advice.
- Versions that float frequently unless a manifest or policy pins them and the version materially changes the workflow.
- Secrets, credentials, tokens, private conversation content, personal data, or machine-specific configuration.
- Preferences that applied only to one deliverable or were not expressed as an ongoing convention.

## Guidance-file strategy

- Prefer an existing canonical guidance file over creating another one.
- When no guidance file exists, create `AGENTS.md` at the repository root for portable agent guidance.
- When only `CLAUDE.md` exists and it is clearly canonical, update it rather than creating duplicate guidance.
- When both exist, respect any delegation or import relationship between them. Put shared repository facts in `AGENTS.md` when appropriate and Claude-only behavior in `CLAUDE.md`; do not copy the same paragraphs into both.
- Keep nested guidance scoped to the subtree it governs. Do not promote subsystem-specific rules to the repository root.
- Preserve stronger existing instructions. If new evidence conflicts with them, verify the current repository and revise only when the old guidance is demonstrably stale or the user explicitly superseded it.

## Writing rules

- Write short, operational statements under existing headings when possible.
- State the command, path, constraint, or decision directly; omit the story of how it was discovered.
- Prefer a small number of high-value additions over documenting every observation.
- Use exact commands only after verifying them. Mark required working directories and prerequisites.
- Do not add a generated timestamp, session identifier, or `/zhu-reinit` bookkeeping section.
- Do not modify application code, configuration, or unrelated documentation during this workflow.

## Local session-history location

This path is a reference point only. Storage layout may change between Zhu versions, so verify the path exists before reading it and fall back to the visible conversation when it does not.

- `~/.llms/sessions/<YYYY>/<MM>/<DD>/llms-<timestamp>-<session-id>.jsonl`: one append-only JSONL transcript per session (first line is the `session_meta` record; later lines are `message`, `token_usage`, and switch/compact/branch markers). Child agents (subagents and teammates) nest under `~/.llms/sessions/agents/<parent-session-id>/` with the same `llms-<timestamp>-<child-id>.jsonl` naming. The metadata records the session's working directory; filter by it to keep to the current repository. Use the bundled `scripts/zhu_session_to_md.py` helper to render a transcript into a compact markdown handoff for review (see "Transcript rendering helper" below).

Transcripts can be large. Extract user messages, corrections, and repeated discovery work with targeted filters (grep, jq, or SQL) instead of reading whole files. Only read history belonging to the current repository, and never copy secrets or personal data from transcripts into guidance files.

### Transcript rendering helper

The bundled `scripts/zhu_session_to_md.py` renders a Zhu JSONL transcript into
a compact markdown handoff that keeps user turns, assistant reasoning, and tool
calls while collapsing all but the last few tool results — ideal for scanning
what the agent repeatedly discovered and where the user corrected it, without
loading megabytes of raw tool output.

```bash
# Render the most recent Zhu session for the current repo to markdown.
# Filter by cwd first so you only read this repository's history.
python3 "$(dirname "$0")/scripts/zhu_session_to_md.py" <path/to/llms-*.jsonl> -o /tmp/handoff.md

# Keep more tool results when detail matters (default keeps the last 5):
python3 scripts/zhu_session_to_md.py <path/to/session.jsonl> -n 10
```

The helper is a convenience, not a requirement: prefer the visible conversation
when it already contains the evidence, and fall back to grep/jq when you only
need a few lines. Never paste secrets or personal data from the rendered output
into guidance files.

## History limitations

Use only history actually exposed to the current agent. Never claim to have reviewed unavailable sessions or tool calls. If earlier history is unavailable, use the visible conversation and explicitly state the limitation. Do not compensate by treating Git history as agent-session history; Git history may verify a candidate, but it does not reveal which facts agents repeatedly rediscovered or which corrections users made.
