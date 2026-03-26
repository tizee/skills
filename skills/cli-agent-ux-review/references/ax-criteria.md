# AX Evaluation Criteria

These are the dimensions to evaluate when reviewing a CLI tool for agent-friendliness. Not all apply to every tool — use judgment.

## 1. Non-Interactive by Default

This is the most fundamental requirement. If a CLI drops into an interactive prompt mid-execution, an agent is stuck — it cannot press arrow keys, navigate menus, or type "y" at the right moment. Interactive mode is the number one reason agents fail at CLI tools.

### Every input must be passable as a flag
- If a command needs an environment, `--env staging` must work. Don't force a selection menu.
- If a command needs a file path, `--file input.json` must work. Don't open a file picker.
- Audit every interactive prompt in the codebase — each one is a potential agent deadlock.

```
# this blocks an agent — stuck on interactive prompt
$ mycli deploy
? Which environment? (use arrow keys)
❯ staging
  production

# this works — all inputs as flags
$ mycli deploy --env staging
```

### Interactive mode as fallback, not primary path
- When flags are missing, it's acceptable to fall back to interactive prompts for human users
- But the tool must be fully operable without any interaction when all required flags are provided
- Check: can every command in the tool be scripted end-to-end with flags alone?

### Watch for hidden interactivity
- Pagers (`less`, `more`) invoked automatically on long output — agents can't quit a pager
- Editors (`$EDITOR`) opened for input (e.g., commit messages) — pass `--message` instead
- Confirmation prompts buried deep in a command flow, not just at the top level
- Auto-spawned browser windows for OAuth — provide `--no-browser` with a device code flow

## 2. Output Format

This is the single most impactful dimension. Agents consume stdout. If the output is noisy, ambiguous, or unparseable, the agent fails.

### Default output should be human-readable markdown/plain text
- Agents and humans both read well-structured plain text
- Tables, headers, and lists are good — they convey structure without requiring a parser
- Avoid walls of unstructured log-style output as the default

### `--json` flag for machine-readable output
- Every command that produces data should support `--json`
- JSON output should be the complete data, not a subset of what the human-readable version shows
- JSON should have a consistent schema across commands (same field names, same nesting conventions)
- Error responses under `--json` should also be JSON, not a mix of JSON on success and plain text on failure
- Check: does `--json` output to stdout cleanly, or does it mix with log lines on stderr?

### Token efficiency
- This matters more than most tool authors realize. An agent calling your tool pays per token of output it reads. A `list` command that dumps 200 lines of decorative formatting when the agent needs 5 fields is burning money and context window.
- Compare the token count of your default output vs `--json` vs what an agent actually needs. The reference doc measured a 5-6x reduction from JSON to CLI-formatted output — think about whether your tool achieves similar efficiency.
- Pagination or `--limit` flags help agents avoid pulling entire datasets when they need a few records.

### Success output should include actionable data
- Even in human-readable mode, success output should return identifiers, URLs, and key metrics — not just "Done!"
- An agent that gets `Deployed successfully` with no deploy ID can't reference that deployment in subsequent commands
- Think of success output as structured data that happens to be formatted for humans

```
# bad — agent learns nothing useful
✓ Deployed successfully!

# good — agent can use these values in follow-up commands
deployed v1.2.3 to staging
url: https://staging.myapp.com
deploy_id: dep_abc123
duration: 34s
```

### Color and formatting
- ANSI escape codes are invisible to humans but show up as garbage in agent context (`\x1b[32m` etc.)
- The tool should respect `NO_COLOR` env var (https://no-color.org/) or `--no-color` flag
- Bonus: auto-detect non-TTY stdout and disable color automatically (most modern CLI frameworks do this)

## 3. Error Handling

Agents cannot squint at a screen, re-read an error, and intuit what went wrong. Error handling needs to be explicit and machine-actionable.

### Exit codes
- 0 for success, non-zero for failure — this is the minimum
- Distinct exit codes for different failure modes (auth failure vs not found vs validation error) let agents branch without parsing error text
- Document exit codes somewhere (README, man page, `--help`)

### Error messages
- Should go to stderr, not stdout (agents often capture stdout for data)
- Should be self-contained: include what failed, why, and what to do about it
- Bad: `Error: invalid input`
- Good: `Error: --format must be one of: json, csv, table. Got: xmll`
- Under `--json`, errors should be structured: `{"error": "not_found", "message": "...", "suggestion": "..."}`

### Include runnable correction commands in error messages
- The most agent-friendly errors include a command the agent can copy-paste and run directly
- This turns error recovery from "understand the problem and figure out the fix" into "run this command"
- Bonus: include a discovery command so the agent can find valid values itself

```
# bad — agent must guess what tags exist
Error: No image tag specified.

# good — agent can directly run the suggested commands
Error: No image tag specified.
  mycli deploy --env staging --tag <image-tag>
  Available tags: mycli build list --output tags
```

### Failure modes an agent will hit
- What happens when the network is down? Does it hang forever or timeout with a clear message?
- What happens with invalid arguments? Does it suggest the closest valid option?
- What happens when a required dependency is missing? Does it tell you which one?

## 4. Credential & Secret Handling

Agents operate in shared context windows. Any credential that touches stdout or needs to be interpolated into a command is a security risk.

### Credentials should never appear in stdout
- If the tool generates tokens/keys, it should store them internally, not print them for the agent to copy-paste into subsequent calls
- Agent context windows can be logged, cached, or leaked via prompt injection — treat them as public

### Built-in auth management
- Login/register commands that persist credentials to a config file (e.g., `~/.config/toolname/credentials`)
- Subsequent commands should use stored credentials automatically — the agent should never need to pass `--token` or `--api-key` on every call
- If auth involves token exchange (OAuth, short-lived tokens), the CLI should handle refresh transparently

### Environment variable support
- Support `TOOL_API_KEY` style env vars as an alternative to config files
- This lets agents operate in ephemeral environments (CI, containers) without interactive setup

## 5. Mutation Safety

Agents make mistakes. Unlike humans, they don't pause and re-read before hitting enter. The tool should make destructive operations recoverable.

### `--dry-run` for destructive operations
- Any command that creates, modifies, or deletes resources should support `--dry-run`
- Dry run output should show exactly what would happen, in the same format as the real operation
- This is the single most important safety feature for agent use. Without it, agents must either skip dangerous operations or risk irreversible damage.

### Confirmation prompts
- Interactive `y/n` prompts are hostile to agents (they hang waiting for input)
- Provide `--yes` or `--force` to skip confirmation, AND make sure the default (no flag) is safe
- Better: require `--confirm` for dangerous operations rather than prompting interactively

### Idempotency
- Commands that create resources should handle "already exists" gracefully (upsert or clear error, not crash)
- Agents retry. If running a command twice causes corruption, agents will cause corruption.

## 6. Discoverability & Self-Documentation

Agents read `--help`. It's their primary way to understand what a tool can do.

**Why this section matters more than you think:** AI agents are LLMs. LLMs learn new tools through in-context learning — they generalize from a few concrete examples (few-shot) far more reliably than from abstract descriptions. This has direct design implications: a CLI that provides 3 usage examples teaches the agent more than 30 lines of flag documentation. And a CLI with a consistent command structure gives the LLM a pattern to generalize from — once it sees `service list` and `config list`, it can infer `deploy list` without being told. You are designing for a learner that excels at pattern extrapolation but struggles with ambiguous, underspecified, or inconsistent interfaces. Lean into that.

### Layered help — don't dump everything at once
- Root `--help` should only list subcommands with one-line descriptions — agents pick the relevant one and drill deeper
- Subcommand `--help` should show flags, descriptions, and examples for that command only
- An agent that runs `mycli --help` and gets 200 lines of all flags for all subcommands wastes tokens on commands it will never use
- Let the agent discover incrementally: `mycli` → subcommands → `mycli deploy --help` → flags and examples

### Help text quality
- Every command and subcommand should have `--help`
- Help should list all flags with descriptions
- Group related flags logically

### Examples in `--help` are critical
- **Why:** LLMs perform few-shot learning — given 2-3 concrete input-output examples, they generalize to novel invocations with high accuracy. A flag description is an abstraction the model must interpret; an example is a pattern it can directly adapt. This is the same mechanism that makes few-shot prompting work — and `--help` examples are literally few-shot prompts for tool use.
- Every subcommand `--help` should include at least 2-3 examples covering common use cases
- Examples should be copy-pasteable (with realistic argument values, not `<placeholder>`)
- Vary the examples to show different flag combinations — this teaches the agent the tool's combinatorial surface, not just one happy path

```
# bad — no examples, agent must synthesize from flag descriptions
$ mycli deploy --help
Options:
  --env     Target environment
  --tag     Image tag
  --force   Skip confirmation

# good — agent can pattern-match directly
$ mycli deploy --help
Options:
  --env     Target environment (staging, production)
  --tag     Image tag (default: latest)
  --force   Skip confirmation

Examples:
  mycli deploy --env staging
  mycli deploy --env production --tag v1.2.3
  mycli deploy --env staging --force
```

### Command structure — guessability matters
- **Why:** LLMs generalize from patterns. A consistent command structure is, in effect, a one-shot lesson — the agent sees `mycli service list` once and infers `mycli deploy list`, `mycli config list` without reading help. An inconsistent structure (e.g., `service list` but `deploy show-all`) breaks the pattern and forces the agent to fall back to trial-and-error or help-reading, both of which cost tokens and retries.
- Consistent verb-noun or noun-verb pattern (`tool resource action` or `tool action resource`)
- Predictable flag names across commands (`--output`, `--format`, `--json` should mean the same thing everywhere)
- Avoid hidden or undocumented flags that are important for common workflows

### Version and capability reporting
- `--version` should exist
- Bonus: a `capabilities` or `info` command that reports what features are available (useful when agents need to adapt to different versions)

## 7. Streaming & Progress

### Long-running operations
- Progress bars and spinners are for humans. They produce garbage output for agents.
- For long operations, consider `--quiet` mode that only outputs the final result
- Or: structured progress events on stderr, final result on stdout

### Piping compatibility
- Output should work when piped (`tool list | other-tool process`)
- Don't break when stdout is not a TTY (no interactive prompts, no pager invocation)

## 8. Input Handling

### Stdin support
- Commands that accept data should support reading from stdin (`-` or pipe)
- This lets agents chain tools without temp files

### Argument vs stdin
- Accept input both as arguments and from stdin where it makes sense
- File arguments should accept `-` for stdin

### Batch operations
- If an agent needs to process 100 items, calling the tool 100 times is expensive
- Consider accepting multiple inputs in one invocation (e.g., `tool process file1 file2 file3` or `tool process --batch input.json`)
