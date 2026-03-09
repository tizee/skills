# AGENTS.md Template

Default `AGENTS.md` for Python projects bootstrapped with this skill. Copy to the project root and fill in placeholders.

## Template

```markdown
# AGENTS.md

Instructions for AI coding agents working in this repository.

## Project Overview

- **Name**: <project-name>
- **Type**: <library|cli-tool|application>
- **Python**: >=3.14
- **Package Manager**: uv

## Commands

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `make test` or `uv run pytest tests/ -v` |
| Lint | `make lint` or `uv run ruff check src/ tests/` |
| Format | `make fmt` or `uv run ruff format src/ tests/` |
| Type check | `make typecheck` or `uv run pyright` |

## Code Style

- **Formatter/Linter**: ruff (configured in pyproject.toml)
- **Type checker**: pyright in strict mode
- **Docstrings**: Google style
- **Quotes**: Single quotes (enforced by ruff formatter)
- **Line length**: 100 characters
- **Layout**: src-layout (`src/<package>/`)

## Rules

- Use `uv` for all package operations — never `pip install` directly
- Run `uv run ruff check` on any new or modified files before committing
- Run `uv run pyright` on edited files — fix errors, avoid `# type: ignore` unless necessary
- No `print()` in library code — use `logging`; `print()` is allowed in CLI entry points
- All package code lives under `src/<package>/`
- Tests go in `tests/` using pytest
```

## Adapting the Template

- Fill in `<project-name>` and `<package>` from user input.
- Set project type to `library` (for `--lib`) or `cli-tool` (for `--app`).
- For CLI tools, add a note that `T20` (print rule) is relaxed in entry-point modules.
- Add project-specific rules if the user mentions any (e.g., async framework, database, API conventions).
