# skills.tizee

Personal agent skill set shared across different AI agent products. Each skill is a self-contained directory with a `SKILL.md` defining its name, description, and workflow.

## Skills

### Code Quality & Review

| Skill | Description |
|---|---|
| `clean-architecture-review` | Review a codebase, PR, or module for clean architecture quality. Detects cross-layer business logic mixing, dependency direction leaks, SOLID principle problems, and over-engineering. Reports findings with SRE-style severity levels (P0–P3). |
| `kiss` | Review code as a senior engineer. Identifies over-complicated designs and lists simplification opportunities. Runs as an `Explore` agent (forked context). |
| `code-formatting` | Best practices for code formatting and granular edit operations. Emphasizes external formatters (`prettier`, `black`, `jq`) and atomic sequential edits. |
| `tdd` | Test-driven development workflow. Enforces behavior-over-implementation testing, fail-fast discipline, and living documentation principles. |
| `script-bugfix` | Debug complex, side-effect-heavy scripts by isolating logic, validating in a no-side-effect environment, then reintegrating with minimal changes. |

### Python

| Skill | Description |
|---|---|
| `piglet` | Python craftsmanship guidance based on *One Python Craftsman*. Covers naming, branching, data structures, exceptions, loops, decorators, imports, and modern syntax choices. |
| `friendly-python` | Practical guidance for writing Pythonic, readable, and maintainable Python. Focuses on clarity, public API design, and style. Pairs with `piglet`. |
| `python-ty` | Fast Python type checking with `ty` (by Astral). Use for running type checks in CI or debugging type errors. |
| `uv-script` | Create standalone executable Python scripts using `uv` with inline TOML dependency metadata and shebang support. No virtualenv management required. |

### Frontend & Design

| Skill | Description |
|---|---|
| `frontend-design` | Create distinctive, production-grade frontend interfaces with high design quality. Avoids generic AI aesthetics; commits to a bold conceptual direction before coding. |
| `taste-skill` (`design-taste-frontend`) | Senior UI/UX engineering skill. Enforces metric-based design variance, motion intensity, and visual density. Uses React/Next.js with strict component architecture and CSS hardware acceleration. |
| `visual-explainer` | Generate self-contained HTML pages for diagrams, architecture overviews, diff reviews, comparison tables, and any structured visual explanation. Auto-activates for tables with 4+ rows or 3+ columns. |

### Planning & Architecture

| Skill | Description |
|---|---|
| `brainstorming` | Collaborative design ideation. Explores user intent, requirements, and design before implementation. Enforces presenting a design and getting user approval before any code is written. |
| `plan-with-files` | Manus-style file-based planning for complex tasks. Creates `.plans/<feature-name>-yymmdd/` with `task_plan.md`, `findings.md`, and `progress.md`. Use for tasks requiring more than 5 tool calls. |
| `git-repo-analysis` | Analyze git repositories and generate comprehensive markdown documentation. Performs top-down analysis: overview → architecture → modules → docs. Runs in forked context. |

### Web & Content

| Skill | Description |
|---|---|
| `fetchmd` | Convert web pages to markdown using the `r.jina.ai` API via the `fetchmd` CLI. Requires a Jina API key in `~/.config/fetchmd/config.json`. |
| `local-webfetch` | Fetch web content using `playwrightmd` for JavaScript-rendered pages. Provides flexible token-aware retrieval strategies for AI agents. |
| `hackernews` | Fetch and explore Hacker News content via the official API using the `hn` CLI. Browse top/best/new/ask/show/job stories, comments, and user profiles. |
| `rss-reader` | Manage RSS/Atom subscriptions in OPML format and fetch feed content as markdown or JSON using the `rss` CLI. Supports list, add/remove, search, and daily digest. |

### Developer Tooling

| Skill | Description |
|---|---|
| `ast-grep` | Structural code pattern search and refactoring using `ast-grep` (`sg`). Syntax-aware, language-agnostic alternative to regex search. Supports JS, TS, Python, Ruby, Go, Rust, and more. |
| `changelog` | Generate and update `CHANGELOG.md` by analyzing git commit history. Handles new changelogs and release appends using conventional commit format. |
| `commit-postmortem-generator` | Analyze fix commits in git history and generate concise postmortem reports. Groups related commits and stores reports in `./.postmortem/`. |
| `tmux` | Remote control tmux sessions for interactive CLIs (Python REPL, GDB, etc.) by sending keystrokes and scraping pane output. Uses `create-session.sh` for session management. |
| `tgbot` | Operate the `tgbot` CLI to send Telegram messages, files, and images from the terminal or from automated agent workflows. Supports allowlist security and markdown rendering. |

### AI Agent Utilities

| Skill | Description |
|---|---|
| `ask-codex` | Delegate hard problems to Codex using a file-based input/output pattern. Use for subtle bugs, deep algorithm analysis, obscure protocols, or when stuck after multiple attempts. |
| `codex-skill` | Guide for creating effective Codex skills. Defines skill folder structure, SKILL.md schema, agent configs, and best practices for extending agent capabilities. |
| `cli-agent-ux-review` | Review a CLI tool's source code for AI agent friendliness and Agent Experience (AX) quality. Evaluates how well a tool works when operated by AI agents rather than humans directly. Runs as an Explore agent (forked context). |
| `osay` | AI-powered text-to-speech CLI (`osay`). Converts text to speech for pronunciation queries, reading aloud, audio file generation, or language practice. |

## Structure

```
skills/
  <skill-name>/
    SKILL.md          # Required: name, description, workflow
    agents/           # Optional: sub-agent configs
    scripts/          # Optional: helper scripts
    templates/        # Optional: output templates
    references/       # Optional: reference material
    examples/         # Optional: usage examples
```

## Usage

Skills are loaded on demand by referencing the skill name. Each `SKILL.md` contains a YAML frontmatter block with `name` and `description` fields used for routing, plus the full workflow instructions for the agent.

Skills marked with `context: fork` run in an isolated subagent context — pass relevant file paths or change descriptions via `arguments` so the subagent has the context it needs.
