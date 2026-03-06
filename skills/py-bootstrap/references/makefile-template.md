# Makefile Template

Standard Makefile for Python projects managed by uv. Copy and adapt as needed.

## Template

```makefile
.PHONY: install sync test dev clean help fmt lint typecheck

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: sync ## Full setup: sync deps
	@echo "Done. Run 'make test' to verify."

sync: ## Sync Python dependencies
	uv sync

test: ## Run tests
	uv run pytest tests/ -v

fmt: ## Format code with ruff
	uv run ruff format src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

typecheck: ## Type check with pyright
	uv run pyright

dev: install test ## Setup dev environment and run tests

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

## Extending the Template

**For CLI tools that need a global install**:

```makefile
install-tool: install ## Install as global uv tool
	uv tool install . --reinstall
```

**For projects with browser/system dependencies** (e.g., Playwright):

```makefile
STAMP := .playwright-installed

install: sync $(STAMP) ## Full setup: sync deps + install browsers

$(STAMP): uv.lock
	uv run playwright install chromium
	@touch $@
```

The stamp file pattern avoids reinstalling browsers on every `make install` — it only reruns when `uv.lock` changes (i.e., a dependency version bumped).

**For projects with documentation**:

```makefile
docs: ## Build documentation
	uv run sphinx-build docs/ docs/_build/

docs-serve: ## Serve docs locally
	uv run sphinx-autobuild docs/ docs/_build/ --port 8000
```

## Notes

- All commands use `uv run` to ensure they execute inside the project's virtualenv without requiring manual activation.
- The `help` target uses grep + awk to auto-generate help from `##` comments — add `## description` to any target to include it.
- `dev` is the one-command "clone and go" target: syncs deps and runs the test suite.
