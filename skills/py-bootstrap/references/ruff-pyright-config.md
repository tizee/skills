# Ruff + Pyright Configuration

Complete tool configuration for `pyproject.toml`. Copy the sections below and adapt version targets as needed.

## Table of Contents

- [Ruff — Base](#ruff--base)
- [Ruff — Lint Rules](#ruff--lint-rules)
- [Ruff — Rule Ignores](#ruff--rule-ignores)
- [Ruff — Pydocstyle](#ruff--pydocstyle)
- [Ruff — Isort](#ruff--isort)
- [Ruff — McCabe Complexity](#ruff--mccabe-complexity)
- [Ruff — Per-file Ignores](#ruff--per-file-ignores)
- [Ruff — Formatter](#ruff--formatter)
- [Pyright](#pyright)

---

## Ruff — Base

```toml
[tool.ruff]
target-version = "py314"
line-length = 100
extend-exclude = [
  ".venv",
  "dist",
  "build",
  "__pypackages__",
]
```

- `target-version` — tells ruff which Python syntax is available so `UP` (pyupgrade) can modernize code correctly. Match the project's `requires-python`.
- `line-length = 100` — wide enough to avoid noisy wrapping, narrow enough for side-by-side diffs. The formatter enforces this; the linter defers to the formatter for line length (see `E501` ignore below).

## Ruff — Lint Rules

```toml
[tool.ruff.lint]
select = [
  "F",    # Pyflakes — undefined names, unused imports, shadowed builtins
  "E",    # pycodestyle errors — basic style violations
  "I",    # isort — import ordering
  "D",    # pydocstyle — docstring presence and format
  "UP",   # pyupgrade — modernize syntax for target Python version
  "B",    # bugbear — common pitfalls (mutable defaults, assert in except, etc.)
  "C4",   # comprehensions — prefer list/dict/set comprehensions over manual loops
  "SIM",  # simplify — simplifiable if/else, context managers, boolean expressions
  "PIE",  # flake8-pie — misc. style (unnecessary pass, dict.get with None default)
  "PERF", # perflint — performance anti-patterns (unnecessary list() in iteration)
  "PGH",  # pygrep-hooks — blanket `type: ignore` without specific codes, eval() usage
  "T10",  # debugger — leftover breakpoint() and pdb imports
  "T20",  # print — catches stray print() in library code; use logging instead
]
```

**Rule selection rationale**: This set covers correctness (F, B), style consistency (E, I, D), modernization (UP), and performance (PERF, C4, SIM) — a sweet spot that catches real bugs without drowning in false positives. Projects like Pydantic use a similar core set.

**Note on `D` (pydocstyle)**: Enforces docstrings on public modules, classes, and functions. Valuable for libraries where API surface documentation matters. For internal tools or scripts where docstrings add noise, disable `D` via `per-file-ignores` for relevant paths rather than removing it globally.

**Note on `T20` (print)**: Library packages should use `logging`, not `print()`. For CLI entry-point modules where `print()` is intentional, add the module to `per-file-ignores`.

## Ruff — Rule Ignores

```toml
ignore = [
  "E501", # line too long — the formatter handles wrapping; linting line length just creates noise
  "D105", # missing docstring in magic method — __repr__, __eq__ etc. are self-documenting
  "D107", # missing docstring in __init__ — the class docstring covers construction semantics
]
```

## Ruff — Pydocstyle

```toml
[tool.ruff.lint.pydocstyle]
convention = "google"
```

Google style docstrings are the most readable for both humans and LLMs. Widely adopted (Pydantic, FastAPI ecosystem). Enforces `Args:`, `Returns:`, `Raises:` sections.

## Ruff — Isort

```toml
[tool.ruff.lint.isort]
combine-as-imports = true
length-sort = true
length-sort-straight = true
```

- `combine-as-imports` — merges `from x import a` and `from x import b` into a single line, reducing import block size.
- `length-sort` / `length-sort-straight` — sorts imports by length within each section, producing visually stable diffs (short imports first). Adopted by pyright-python and others.

## Ruff — McCabe Complexity

```toml
[tool.ruff.lint.mccabe]
max-complexity = 15
```

Cyclomatic complexity ceiling. Default is 10, which triggers too many false positives on real-world code with necessary branching. 15 is permissive enough to avoid forced refactors while still catching genuinely tangled functions.

## Ruff — Per-file Ignores

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "B"]
"docs/**" = ["D"]
```

- Tests don't need docstrings (`D`) and often use patterns bugbear flags (mutable defaults in fixtures, broad exceptions in assertions) — `B` is noise there.
- Documentation scripts/conf.py don't need docstrings.

Extend as needed:
- For CLI entry points: `"src/<package>/__main__.py" = ["T20"]` to allow `print()`.
- For scripts: `"scripts/**" = ["D", "T20"]`.

## Ruff — Formatter

```toml
[tool.ruff.format]
quote-style = "single"
docstring-code-format = true
```

- `single` quotes reduce visual noise and are consistent with Pydantic and pyright-python conventions. The formatter handles the conversion — no manual effort.
- `docstring-code-format` — formats code blocks inside docstrings, keeping examples consistent with the rest of the codebase.

## Pyright

```toml
[tool.pyright]
include = ["src", "tests"]
exclude = ["**/__pycache__", ".venv", "build", "dist"]

pythonVersion = "3.14"
typeCheckingMode = "strict"

reportImportCycles = false
reportPrivateUsage = false
```

- `strict` mode catches real type bugs that `standard` misses: missing return types, untyped function defs, implicit `Any`. Starting strict on a fresh project costs nothing; retrofitting it later costs everything.
- `reportImportCycles = false` — circular imports are a structural concern, not a type error. Address them architecturally when they cause problems, not as lint noise.
- `reportPrivateUsage = false` — accessing `_private` members across modules within the same package is common in Python. This rule triggers too many false positives in real codebases.
