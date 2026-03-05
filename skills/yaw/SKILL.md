---
name: yaw
description: >
  Manage scheduled workflows and cron jobs via the yaw (yet another workflow) CLI.
  Use when the user wants to list, create, inspect, run, enable, disable,
  or debug recurring scheduled tasks or multi-step workflows. Also use when
  the user asks about cron jobs, timed tasks, scheduled commands, periodic scripts,
  recurring agent tasks, or workflow orchestration. Triggers on "cron",
  "scheduled tasks", "cron jobs", "timed tasks", "periodic", "recurring",
  "yaw", "workflow", or any request to schedule, list, or manage recurring commands.
---

# yaw -- yet another workflow

Declarative workflow engine. Schedules any command (scripts, agent CLIs, pipelines) via system crontab with support for multi-step DAG workflows.

## Invocation

Always use `yaw` directly. It should be installed on PATH (via `uv` or pip).

```bash
yaw list
```

If `yaw` is not on PATH, run from the project directory:

```bash
uv run yaw list
```

Default output is human-readable tables. Add `--json` for machine-readable JSON output (on `list`, `show`, `status`).

## Configuration

- **Config dir**: `~/.yaw/` (created by `yaw init`)
- **Workflow definitions**: `~/.yaw/jobs/<name>.yaml`
- **Execution logs**: `~/.yaw/logs/<name>/`
- **Runtime state**: `~/.yaw/state/<name>.json`
- **Global config**: `~/.yaw/config.yaml`
- Override config dir: `--dir <path>`

## Commands

### init

Create `~/.yaw/` directory structure and default config.

```
yaw init
```

### list

List all registered workflows with schedule, enabled status, and last run result.

```
yaw list
yaw list --json
```

### status

Summary of all workflows: last run time, run/failure counts, current status.

```
yaw status
yaw status --json
```

### show

Show full workflow definition, state, and recent log paths for a specific workflow.

```
yaw show <workflow-name>
yaw show <workflow-name> --json
```

### run

Execute a workflow immediately (manual trigger, useful for testing).

```
yaw run <workflow-name>
```

### logs

View the latest execution log for a workflow.

```
yaw logs <workflow-name>
yaw logs <workflow-name> --tail 20
```

### add / remove

Register or remove a workflow. Automatically syncs crontab.

```
yaw add <file.yaml>
yaw remove <workflow-name>
```

### enable / disable

Toggle a workflow without removing its definition. Automatically syncs crontab.

```
yaw enable <workflow-name>
yaw disable <workflow-name>
```

### validate

Validate a workflow definition file without registering it.

```
yaw validate <file.yaml>
```

### install / uninstall

Sync all enabled workflows to system crontab, or remove all yaw entries from crontab.

```
yaw install
yaw uninstall
```

## Workflow Definition Format

Workflows are YAML files. A single `WorkflowDefinition` model handles all cases.

### Simple scheduled job (command shorthand)

```yaml
name: my-job
trigger:
  - cron: "0 9 * * *"
command: echo "hello world"
```

### Legacy schedule shorthand

The `schedule` field is accepted as shorthand for a single cron trigger:

```yaml
name: my-job
schedule: "0 9 * * *"
command: echo "hello world"
```

This desugars to `trigger: [{cron: "0 9 * * *"}]` internally. `schedule` and `trigger` are mutually exclusive.

### Multi-step DAG workflow

Use `steps` (a dict of name -> step) with optional `needs` and `condition`:

```yaml
name: ci-pipeline
trigger:
  - cron: "0 9 * * 1-5"
  - manual: true

steps:
  lint:
    command: ruff check src/
  test:
    command: pytest
  build:
    needs: [lint, test]
    command: python -m build
  deploy:
    needs: [build]
    command: ./scripts/deploy.sh
    condition: "${{ workflow.trigger == 'manual' }}"
```

### Validation rules

- `command` and `steps` are mutually exclusive
- `trigger` list must be non-empty
- Step names must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`
- `needs` must reference existing step names
- Step dependency graph must be acyclic (DAG)
- `condition` must use `${{ ... }}` syntax (validated at parse time)

For full schema and examples, read `references/examples.md`.

## Agent Workflows

### Creating a new workflow

1. Write a YAML workflow definition file to `/tmp/<name>.yaml`
2. Validate: `yaw validate /tmp/<name>.yaml`
3. Register: `yaw add /tmp/<name>.yaml`

### Diagnosing a failed workflow

1. Check status: `yaw status`
2. Find the failing workflow and read logs: `yaw logs <name> --tail 50`
3. Inspect definition: `yaw show <name>`
4. Fix the underlying issue, then test: `yaw run <name>`

### Scheduling a headless agent task

Write a workflow that invokes the agent CLI:

```yaml
name: daily-digest
trigger:
  - cron: "0 9 * * *"
command: >
  llms agent -p "Check RSS feeds and send digest to telegram"
  --tools "Bash,Read,WebFetch"
```

For complex agent invocations, use a script wrapper:

```yaml
name: daily-digest
trigger:
  - cron: "0 9 * * *"
command: ~/scripts/daily-digest.sh
```

### Self-healing with failure hooks

Workflows can run a notify command on failure:

```yaml
on_failure:
  notify: >
    llms agent -p "Job '${YAW_JOB_NAME}' failed (exit ${YAW_EXIT_CODE}).
    Diagnose from ${YAW_LOG_FILE}." --tools "Bash,Read,Glob,Grep"
```

Environment variables injected into the notify command: `YAW_JOB_NAME`, `YAW_EXIT_CODE`, `YAW_LOG_FILE`, `YAW_ATTEMPT`, `YAW_DURATION`.

## Setup

If `yaw` is not on PATH, ask the user to install it. Requires Python 3.12+ and uv.

```bash
cd /path/to/yaw && uv pip install -e .
```
