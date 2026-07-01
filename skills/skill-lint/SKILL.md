---
name: skill-lint
description: >-
  Validate and lint Agent Skill SKILL.md files and diagnose why a skill fails
  to load. Use whenever the user wants to check if a skill's frontmatter is
  valid, find out why a skill "vanished" or is not discovered, lint a single
  skill, or scan an entire skills directory before committing. Triggers on
  requests like "validate my skill", "why isn't my skill loading", "check the
  SKILL.md format", "lint my skills", "diagnose this frontmatter", or any
  request to verify skill name and description rules. Make sure to use this
  skill whenever a skill is unexpectedly missing from the available-skills
  list, since the usual cause is a silent frontmatter parse error rather than a
  discovery problem.
---

# Skill Lint

Diagnose and validate Agent Skill `SKILL.md` files. This exists because the
most common failure mode is silent: a malformed frontmatter causes the loader
to drop the skill with only a log warning, so it simply never appears in the
available-skills list. This skill turns that invisible failure into a clear,
actionable report.

## When to use

- A skill you wrote does not show up / cannot be invoked.
- Before committing a new or edited skill, to catch format errors early.
- To audit a whole skills directory in one pass.

## Usage

Run the bundled validator. It accepts a single skill directory, a single
`SKILL.md`, or a directory that contains many skills (scan mode).

```bash
# Lint one skill
python3 scripts/validate.py /path/to/skills/my-skill

# Lint a single SKILL.md
python3 scripts/validate.py /path/to/skills/my-skill/SKILL.md

# Scan every skill under a root directory
python3 scripts/validate.py ~/.config/llms/skills
```

Requires PyYAML. If it is not installed, run via uv instead:

```bash
uv run --with pyyaml scripts/validate.py <path>
```

Exit code is `0` only when no ERROR is found; WARN-only runs still exit `0`.

## Reading the output

Each skill prints one of `OK`, `WARN`, or `FAIL`, followed by any findings.
The two severities mean different things:

- **ERROR** — the skill would fail to load in Zhu. These are the failures that
  make a skill silently disappear. Fix all of them.
- **WARN** — the skill still loads in Zhu, but is risky or non-portable (for
  example it exceeds the agentskills.io spec length limit that stricter tools
  enforce, or Zhu would truncate an overlong description). Fix when you care
  about portability or want the full description preserved.

**Example:**

Input: a skill whose unquoted description contains a colon-space, e.g.
`Output follows a house format: prose + ASCII`.

Output:
```
FAIL  system-design-doc
        ERROR: invalid YAML in frontmatter: mapping values are not allowed here
```

## What it checks

- Frontmatter parses as YAML and is a mapping. A colon-space inside an
  unquoted scalar (`format: prose`) is the classic trap — it is read as a
  nested mapping and rejected. Fix by quoting the value or using a folded
  block scalar (`>-`).
- `name` is present (or falls back to the directory name), 1-64 chars,
  lowercase alphanumeric plus single hyphens, no leading/trailing/consecutive
  hyphens.
- `description` is present and non-empty (Zhu falls back to the first body
  paragraph when frontmatter has none). Reports when it exceeds the spec limit
  (1024) or Zhu's truncation cap (1224), and flags angle brackets.
- Unknown frontmatter keys (ignored by Zhu) are surfaced as hygiene warnings.

## Fixing the common frontmatter YAML error

When a description needs to contain a colon, quotes, or apostrophes, prefer a
YAML folded block scalar so nothing needs escaping:

```yaml
description: >-
  Write a grounded design doc. Output follows a house format: prose + ASCII
  flowcharts, a key-file index, and a BDD table.
```
