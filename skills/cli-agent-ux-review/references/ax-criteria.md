# AX Evaluation Criteria

These are the dimensions to evaluate when reviewing a CLI tool for agent-friendliness. Not all apply to every tool — use judgment.

## 1. Output Format

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

### Color and formatting
- ANSI escape codes are invisible to humans but show up as garbage in agent context (`\x1b[32m` etc.)
- The tool should respect `NO_COLOR` env var (https://no-color.org/) or `--no-color` flag
- Bonus: auto-detect non-TTY stdout and disable color automatically (most modern CLI frameworks do this)

## 2. Error Handling

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

### Failure modes an agent will hit
- What happens when the network is down? Does it hang forever or timeout with a clear message?
- What happens with invalid arguments? Does it suggest the closest valid option?
- What happens when a required dependency is missing? Does it tell you which one?

## 3. Credential & Secret Handling

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

## 4. Mutation Safety

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

## 5. Discoverability & Self-Documentation

Agents read `--help`. It's their primary way to understand what a tool can do.

### Help text quality
- Every command and subcommand should have `--help`
- Help should list all flags with descriptions
- Include examples in help text — agents use examples as templates more than they use flag descriptions
- Group related flags logically

### Command structure
- Consistent verb-noun pattern (`tool resource action` or `tool action resource`)
- Predictable flag names across commands (`--output`, `--format`, `--json` should mean the same thing everywhere)
- Avoid hidden or undocumented flags that are important for common workflows

### Version and capability reporting
- `--version` should exist
- Bonus: a `capabilities` or `info` command that reports what features are available (useful when agents need to adapt to different versions)

## 6. Streaming & Progress

### Long-running operations
- Progress bars and spinners are for humans. They produce garbage output for agents.
- For long operations, consider `--quiet` mode that only outputs the final result
- Or: structured progress events on stderr, final result on stdout

### Piping compatibility
- Output should work when piped (`tool list | other-tool process`)
- Don't break when stdout is not a TTY (no interactive prompts, no pager invocation)

## 7. Input Handling

### Stdin support
- Commands that accept data should support reading from stdin (`-` or pipe)
- This lets agents chain tools without temp files

### Argument vs stdin
- Accept input both as arguments and from stdin where it makes sense
- File arguments should accept `-` for stdin

### Batch operations
- If an agent needs to process 100 items, calling the tool 100 times is expensive
- Consider accepting multiple inputs in one invocation (e.g., `tool process file1 file2 file3` or `tool process --batch input.json`)
