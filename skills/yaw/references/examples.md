# yaw Workflow Definition Examples

Reference examples for creating yaw workflow definitions. Each workflow is a standalone YAML file.

## Minimal Workflow (Trigger + Command)

Simple scheduled job — three required fields: `name`, `trigger`, `command`.

```yaml
name: hello
trigger:
  - cron: "*/5 * * * *"
command: echo "hello from yaw"
```

## Legacy Schedule Shorthand

The `schedule` field is accepted as shorthand for a single cron trigger. Equivalent to the above:

```yaml
name: hello
schedule: "*/5 * * * *"
command: echo "hello from yaw"
```

`schedule` and `trigger` are mutually exclusive.

## Full Workflow with All Optional Fields

```yaml
name: daily-rss-digest
trigger:
  - cron: "0 9 * * *"
description: "Daily RSS digest via headless agent"
enabled: true

command: >
  llms agent -p "
  1. Load the rss-reader skill and check today's RSS feed updates
  2. If there are new articles, summarize them as a digest
  3. Load the telegram skill and send the digest to channel @my-daily
  " --tools "Bash,Read,Glob,Grep,WebFetch" --output-format text

timeout: 300
cwd: ~/projects/my-workspace

env:
  TELEGRAM_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN}"
  RSS_OPML_PATH: "~/.config/rss/feeds.opml"

on_failure:
  retry: 1
  retry_delay: 30
  notify: >
    llms agent -p "Job '${YAW_JOB_NAME}' failed (exit ${YAW_EXIT_CODE}).
    Check ${YAW_LOG_FILE}." --tools "Bash,Read"
```

## Agent Headless Task (Inline Command)

```yaml
name: daily-digest
trigger:
  - cron: "0 9 * * *"
command: >
  llms agent -p "Check RSS feeds, summarize new articles,
  send digest to telegram" --tools "Bash,Read,WebFetch"
timeout: 300
```

## Script Wrapper Pattern

Point `command` at a script for complex invocations.

```yaml
name: weekly-report
trigger:
  - cron: "0 10 * * 1"
command: ~/scripts/weekly-report.sh
timeout: 600
```

Where `weekly-report.sh`:

```bash
#!/bin/bash
llms agent -p "Generate weekly summary report" \
  -s "You are a technical writer. Be concise." \
  --tools "Bash,Read,Glob,Grep,WebFetch" \
  --continue
```

## Stateful Agent with Session Resume

```yaml
name: pr-tracker
trigger:
  - cron: "0 10 * * 1-5"
command: >
  llms agent -p "Check open PRs, compare with yesterday"
  --resume pr-tracker-session
timeout: 180
```

## Role-Based Agent with System Prompt

```yaml
name: sre-monitor
trigger:
  - cron: "*/30 * * * *"
command: >
  llms agent -p "Check service health, report anomalies"
  -s "You are an SRE. Be terse. Use severity levels."
  --tools "Bash,Read,Glob,Grep,WebFetch"
timeout: 120
```

## Self-Healing Failure Hook

The notify command receives workflow context via environment variables.

```yaml
name: critical-backup
trigger:
  - cron: "0 3 * * *"
command: ~/scripts/backup-prod.sh
timeout: 900

on_failure:
  retry: 2
  retry_delay: 60
  notify: >
    llms agent -p "Job '${YAW_JOB_NAME}' failed with exit code
    ${YAW_EXIT_CODE} after ${YAW_ATTEMPT} attempts (${YAW_DURATION}s).
    Check logs at ${YAW_LOG_FILE} and attempt to diagnose."
    --tools "Bash,Read,Glob,Grep"
```

Notify environment variables:

| Variable | Description |
|----------|-------------|
| `YAW_JOB_NAME` | Workflow name |
| `YAW_EXIT_CODE` | Exit code of the failed command |
| `YAW_LOG_FILE` | Path to the current run's log file |
| `YAW_ATTEMPT` | Total attempts made (1 + retries) |
| `YAW_DURATION` | Execution duration in seconds |

## Database Backup

```yaml
name: daily-backup
trigger:
  - cron: "0 2 * * *"
command: pg_dump mydb | gzip > /backups/mydb-$(date +%F).sql.gz
timeout: 300
```

## Static Site Deploy

```yaml
name: blog-deploy
trigger:
  - cron: "0 6 * * *"
command: cd ~/blog && hugo && rsync -a public/ server:/var/www/
timeout: 120
```

## Environment File

Keep secrets out of YAML by referencing a `.env` file.

```yaml
name: api-checker
trigger:
  - cron: "0 */6 * * *"
command: ~/scripts/check-api.sh
env_file: ~/.config/yaw/envs/api-checker.env
env:
  EXTRA_FLAG: "verbose"
```

`env_file` is loaded first; inline `env` entries override file values.

## Multi-Step DAG Pipeline

Use `steps` for multi-step workflows with dependencies (mutually exclusive with `command`).

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
  typecheck:
    command: pyright src/
  build:
    needs: [lint, test, typecheck]
    command: python -m build
  deploy:
    needs: [build]
    command: ./scripts/deploy.sh
    condition: "${{ workflow.trigger == 'manual' }}"
```

## ETL Pipeline

```yaml
name: etl-pipeline
trigger:
  - cron: "0 4 * * *"
steps:
  extract:
    command: python scripts/extract.py
  transform:
    needs: [extract]
    command: python scripts/transform.py
  load:
    needs: [transform]
    command: python scripts/load.py
timeout: 1800
```

## Disabled Workflow

Set `enabled: false` to keep the definition without scheduling.

```yaml
name: deprecated-task
trigger:
  - cron: "0 0 * * *"
command: echo "this is disabled"
enabled: false
```
