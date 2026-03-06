---
name: py-bootstrap
description: Bootstrap new Python projects with a production-grade dev toolchain using uv, ruff, pyright, pytest, and hatchling. Use this skill whenever the user wants to create a new Python project, initialize a Python package, scaffold a Python CLI tool, set up a Python library, or start any Python codebase from scratch. Also use when the user says "new project", "init project", "bootstrap", "scaffold", "create a python package", or asks about setting up Python dev tooling (linting, formatting, type checking) for a fresh project.
---

# py-bootstrap

Bootstrap production-grade Python projects with a standardized dev toolchain.

## Toolchain

| Tool | Role | Invocation |
|------|------|------------|
| **uv** | Package manager, virtualenv, lockfile | `uv init`, `uv add`, `uv sync` |
| **hatchling** | Build backend (src-layout) | `build-system` in pyproject.toml |
| **ruff** | Linter + formatter (replaces black, isort, flake8) | `uv run ruff check`, `uv run ruff format` |
| **pyright** | Static type checker | `uv run pyright` |
| **pytest** | Test runner + coverage | `uv run pytest` |
| **make** | Task runner for common dev commands | `make test`, `make lint`, etc. |

## Workflow

### 1. Scaffold with uv

```bash
uv init <project-name> --lib --python ">=3.14"
cd <project-name>
```

`--lib` creates a src-layout package. For CLI tools or applications, use `uv init <name> --app --python ">=3.14"` instead and adjust the layout accordingly.

### 2. Add dev dependencies

```bash
uv add --dev ruff pyright pytest pytest-cov hatchling
```

Add project-specific runtime dependencies separately:

```bash
uv add <dep1> <dep2>
```

### 3. Configure pyproject.toml

After `uv init`, the generated `pyproject.toml` needs tool configuration. Use hatchling as the build backend with src-layout, and add ruff + pyright config.

The complete pyproject.toml structure:

```toml
[project]
name = "<project-name>"
version = "0.1.0"
description = "<one-line description>"
readme = "README.md"
license = "<license>"  # user's choice — ask if not specified
requires-python = ">=3.14"
dependencies = []

[project.urls]
Homepage = "<url>"
Repository = "<url>"

# Only for CLI tools — omit for libraries:
# [project.scripts]
# <cmd> = "<package>:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/<package>"]

[dependency-groups]
dev = [
    "hatchling>=1.28.0",
    "pyright>=1.1.408",
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    "ruff>=0.15.4",
]
```

For the `[tool.ruff]`, `[tool.pyright]`, and related sections, read `references/ruff-pyright-config.md` and apply the full configuration. The reference file contains the complete config with rationale — adapt `target-version` and `pythonVersion` if the project uses a different Python version.

### 4. Create pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    --strict-markers
    --strict-config
    -v

[coverage:run]
source = <package>
omit =
    */__main__.py
    */setup.py

[coverage:report]
show_missing = true
skip_covered = false
sort = Cover
```

### 5. Create Makefile

Read `references/makefile-template.md` for the complete Makefile template. Adapt targets if the project has special needs (e.g., no browser install step, custom build commands).

### 6. Create directory structure

```
<project-name>/
├── src/<package>/
│   ├── __init__.py
│   └── py.typed          # PEP 561 marker for typed packages
├── tests/
│   ├── __init__.py
│   └── test_<package>.py
├── pyproject.toml
├── pytest.ini
├── Makefile
├── README.md
└── .gitignore
```

Create `py.typed` as an empty file — it signals to type checkers that the package ships inline types.

Create a minimal `.gitignore`:

```gitignore
__pycache__/
*.pyc
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
```

### 7. Verify setup

```bash
uv sync
make lint
make typecheck
make test
```

All three should pass on the initial skeleton before writing any real code.

## Conventions

- **src-layout**: All package code lives under `src/<package>/`. This prevents accidental imports from the working directory and is the modern Python packaging standard.
- **Single `pyproject.toml`**: All tool config lives here — no separate `.ruff.toml`, `pyrightconfig.json`, or `setup.cfg`.
- **Strict types from day one**: Starting with `typeCheckingMode = "strict"` is far easier than retrofitting it later. Suppress individual false positives with `# type: ignore[rule]` comments rather than weakening the global mode.
- **No `print()` in library code**: The `T20` ruff rule catches stray prints. Use `logging` for libraries. For CLI tools, `T20` can be disabled in the entry-point module via `per-file-ignores`.
- **Docstrings (google style)**: The `D` rules enforce docstrings. For scripts/tools where docstrings add noise, disable `D` in `per-file-ignores` for relevant paths.

## References

- `references/ruff-pyright-config.md` — Complete ruff + pyright configuration with rule-by-rule rationale. Read this when generating `pyproject.toml`.
- `references/makefile-template.md` — Makefile template with all standard targets. Read this when generating the Makefile.
