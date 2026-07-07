---
name: tmux
description: "Remote control tmux sessions for interactive CLIs by sending keystrokes and scraping output."
license: WTFPL
---

# tmux Skill

Programmable terminal multiplexer for interactive work. Use tmux to remote control interactive CLIs (python, gdb, etc.) by sending keystrokes and scraping pane output.

## Config isolation (READ FIRST)

Start every server with an explicit config so keystroke injection and pane
scraping stay deterministic. tmux reads `-f` only on the command that *starts*
the server (the first `new` on a socket); later `tmux -S "$SOCKET"` calls
attach and inherit it.

- **Prefer `create-session.sh`.** It loads the bundled `tools/clean.conf`
  (status off, mouse off, no auto-rename, large scrollback) automatically, so a
  single command gives you a clean, isolated session with no extra flags.
- **For manual servers, pass `-f` on the first `new`** — `-f tools/clean.conf`
  for the deterministic config, or `-f /dev/null` for a bare server. This keeps
  the session self-contained and independent of the user's `~/.tmux.conf`.
- **Load the user's real config on request** with `create-session.sh -c user`,
  when the task genuinely needs their personal keybindings.

## Quickstart

**Always use `create-session.sh` to create sessions** - it handles socket management, config isolation (clean by default), prompt detection, and error handling automatically.

```bash
# Python REPL session (clean config is the default)
tools/create-session.sh -n python \
  -p 'PYTHON_BASIC_REPL=1 python3 -q' -w '^>>> '

# After creation, ALWAYS provide monitoring commands:
To monitor this session yourself:
  tmux -S "/tmp/agent-tmux-sockets/python.sock" attach -t python

Or to capture the output once:
  tmux -S "/tmp/agent-tmux-sockets/python.sock" capture-pane -p -J -t python:0.0 -S -200
```

This must ALWAYS be printed right after a session was started and once again at the end of the tool loop. But the earlier you send it, the happier the user will be.

### Manual Session Creation (Advanced)

If you need full control, you can create sessions manually. The critical part
is `-f` on the **first** command (the one that starts the server) so the user's
`~/.tmux.conf` is never sourced:

```bash
SOCKET_DIR=${AGENT_TMUX_SOCKET_DIR:-${TMPDIR:-/tmp}/agent-tmux-sockets}
mkdir -p "$SOCKET_DIR"
SOCKET="$SOCKET_DIR/agent.sock"
SESSION=agent-python
CLEAN_CONF="$(dirname "$0")/tools/clean.conf"   # or an absolute path to it

# -f on this first command loads the deterministic config and keeps the
# session isolated (use /dev/null if you cannot reference clean.conf).
tmux -S "$SOCKET" -f "$CLEAN_CONF" new -d -s "$SESSION" -n shell
tmux -S "$SOCKET" send-keys -t "$SESSION":0.0 -- 'PYTHON_BASIC_REPL=1 python3 -q' Enter
tmux -S "$SOCKET" capture-pane -p -J -t "$SESSION":0.0 -S -200
tmux -S "$SOCKET" kill-session -t "$SESSION"
```

## Socket convention

- Place tmux sockets under `AGENT_TMUX_SOCKET_DIR` (defaults to `${TMPDIR:-/tmp}/agent-tmux-sockets`) and use `tmux -S "$SOCKET"` so we can enumerate/clean them. Create the dir first: `mkdir -p "$AGENT_TMUX_SOCKET_DIR"`.
- Default socket path to use unless you must isolate further: `SOCKET="$AGENT_TMUX_SOCKET_DIR/agent.sock"`.
- **Keep every session on a per-socket path under this directory** so you can enumerate and clean them up reliably.

## Targeting panes and naming

- Target format: `{session}:{window}.{pane}`, defaults to `:0.0` if omitted. Keep names short (e.g., `agent-py`, `agent-gdb`).
- Use `-S "$SOCKET"` consistently to stay on the private socket path. The config comes from the `-f` on the server-starting command (see "Config isolation"): clean by default, `-c user` only when you explicitly need the user's keybindings.
- Inspect: `tmux -S "$SOCKET" list-sessions`, `tmux -S "$SOCKET" list-panes -a`.

## Finding sessions

**Always use the helper** to find created sockets:
- List sessions on your active socket: `tools/find-sessions.sh -S "$SOCKET"`
- Find all sockets: `tools/find-sessions.sh --all` (scans `AGENT_TMUX_SOCKET_DIR`)
- Filter by name: `tools/find-sessions.sh -S "$SOCKET" -q "pattern"`

## Sending input safely

- Prefer literal sends to avoid shell splitting: `tmux -S "$SOCKET" send-keys -t target -l -- "$cmd"`
- **Note**: When sending multiple lines with `-l` flag, include `\n` for newlines, then send Enter separately to execute
- When composing inline commands, use single quotes or ANSI C quoting to avoid expansion: `tmux -S "$SOCKET" send-keys -t target -- $'python3 -m http.server 8000'`.
- To send control keys: `tmux -S "$SOCKET" send-keys -t target C-c`, `C-d`, `C-z`, `Escape`, etc.
- Send Enter: `tmux -S "$SOCKET" send-keys -t target -- "cmd" Enter`

### Sending literal text with `-l`

The `-l` (literal) flag sends its argument as raw text. Send the text with
`-l`, then send `Enter` as a separate command to execute it:

```bash
# Send literal text, then execute
tmux -S "$SOCKET" send-keys -t python:0.0 -l 'print("hello world")'
tmux -S "$SOCKET" send-keys -t python:0.0 Enter
```

For plain text without special characters, a single command with `Enter` works:

```bash
tmux -S "$SOCKET" send-keys -t python:0.0 'print("hello world")' Enter
```

**Pick the approach by content:**
- Use `-l` plus a separate `Enter` when the text contains special shell
  characters (dollar signs, exclamation marks, backticks) — `-l` preserves them
  exactly.
- Use a single command with `Enter` for plain text.

### BEST PRACTICE: Sending Multi-line Code Blocks

**RECOMMENDED: Use `-l` to send large code blocks in one operation instead of line-by-line.**

This is much more efficient than sending commands one line at a time:

```bash
# EFFICIENT: Send entire code block at once with embedded newlines
tmux -S "$SOCKET" send-keys -t python:0.0 -l 'def hello(name):
    print(f"Hello, {name}!")
    return True

result = hello("world")'
tmux -S "$SOCKET" send-keys -t python:0.0 Enter
```

**Key advantages:**
- **Faster**: One operation instead of multiple send-keys calls
- **Safer**: Preserves exact formatting and indentation
- **More reliable**: Avoids timing issues between line sends
- **Handles special chars**: Dollar signs, quotes, backticks work correctly

**For very large code blocks, use heredoc or read from file:**
```bash
# Send multi-line code from heredoc
tmux -S "$SOCKET" send-keys -t python:0.0 -l "$(cat <<'EOF'
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, x):
        self.result += x
        return self.result

calc = Calculator()
calc.add(5)
EOF
)"
tmux -S "$SOCKET" send-keys -t python:0.0 Enter
```

**Remember**: Always send `Enter` as a separate command after using `-l` to execute the code.

## Watching output

- Capture recent history (joined lines to avoid wrapping artifacts): `tmux -S "$SOCKET" capture-pane -p -J -t target -S -200`.
- For continuous monitoring, poll with the helper script (below) instead of `tmux wait-for` (which does not watch pane output).
- You can also temporarily attach to observe: `tmux -S "$SOCKET" attach -t "$SESSION"`; detach with `Ctrl+b d`.
- When giving instructions to a user, **explicitly print a copy/paste monitor command** alongside the action so they always have it at hand.

## Spawning Processes

Some special rules for processes:

- When asked to debug, use lldb by default
- When starting a python interactive shell, always set the `PYTHON_BASIC_REPL=1` environment variable. This is very important as the non-basic console interferes with your send-keys.

## Synchronizing / waiting for prompts

- Use timed polling to avoid races with interactive tools. Example: wait for a Python prompt before sending code:
  ```bash
  tools/wait-for-text.sh -t "$SESSION":0.0 -p '^>>>' -T 15 -l 4000
  ```
- For long-running commands, poll for completion text (`"Type quit to exit"`, `"Program exited"`, etc.) before proceeding.

## Interactive tool recipes

- **Python REPL**: `tmux -S "$SOCKET" send-keys -- 'python3 -q' Enter`; wait for `^>>>`; send code with `-l`; interrupt with `C-c`. Always with `PYTHON_BASIC_REPL=1`.
- **GDB**: `tmux -S "$SOCKET" send-keys -- 'gdb --quiet ./a.out' Enter`; disable paging `tmux -S "$SOCKET" send-keys -- 'set pagination off' Enter`; break with `C-c`; issue `bt`, `info locals`, etc.; exit via `quit` then confirm `y`.
- **Other TTY apps** (ipdb, psql, mysql, node, bash): same pattern—start the program, poll for its prompt, then send literal text and Enter.

## Primary Tool: create-session.sh

**Always use `create-session.sh` instead of manual tmux commands** - it handles all the details automatically.

```bash
tools/create-session.sh -n NAME [-c clean|none|user|custom] [options]

Options:
  -n NAME        Session name
  -c LEVEL       clean (default, deterministic), none (-f /dev/null),
                 user (your keys/config), custom
  -p PROGRAM     Program to launch
  -w PATTERN     Wait for regex pattern
  -t TIMEOUT     Timeout (default 15)
  -s SOCKET_DIR  Socket directory
  -f CONFIG      Custom config file
  -h             Show help
```

**Recommended usage examples:**

```bash
# Python (always use PYTHON_BASIC_REPL=1); clean config is the default
tools/create-session.sh -n python \
  -p 'PYTHON_BASIC_REPL=1 python3 -q' -w '^>>> '

# GDB (clean by default; only use -c user if you need your own keybindings)
tools/create-session.sh -n gdb \
  -p 'gdb --quiet ./program' -w '^(gdb) '

# PostgreSQL
tools/create-session.sh -n db \
  -p 'psql -h localhost mydb' -w 'mydb=#'
```

## Helper: wait-for-text.sh

`tools/wait-for-text.sh` polls a pane for a regex (or fixed string) with a timeout. Works on Linux/macOS with bash + tmux + grep.

```bash
tools/wait-for-text.sh -t TARGET -p PATTERN [-s SOCKET] [options]
```

**Required:**
- `-t`, `--target` - tmux target (session:window.pane), required
- `-p`, `--pattern` - regex pattern to look for, required

**Optional:**
- `-s`, `--socket` - tmux socket path
- `-F`, `--fixed` - treat pattern as a fixed string (grep -F)
- `-T`, `--timeout` - seconds to wait (integer, default: 15)
- `-i`, `--interval` - poll interval in seconds (default: 0.5)
- `-l`, `--lines` - number of history lines to inspect (integer, default: 1000)
- `-h`, `--help` - show help

**Exit codes:**
- Exits 0 on first match, 1 on timeout. On failure prints the last captured text to stderr to aid debugging.

## Helper Scripts

### Find Sessions

```bash
tools/find-sessions.sh --all                  # All agent sockets
tools/find-sessions.sh -S SOCKET -q "pattern" # Filter by name
```

## Cleanup

**Always clean up after completing work.** Killing a session can leave its socket file behind, so confirm the file is removed as the final step.

### Track cleanup steps

When working with tmux sessions, track the cleanup steps in whatever task or
todo tracker your agent provides, so nothing is forgotten:

```
Cleanup checklist:
1. Create tmux session (in_progress)
2. Complete interactive work (pending)
3. Kill tmux session (pending)
4. Verify socket file removed (pending)
5. Remove socket file if still exists (pending)
```

Mark each cleanup step as completed after verification, so no orphaned socket files are left behind.

### Proper Cleanup Procedure

1. **Kill the session when done:**
   ```bash
   tmux -S "$SOCKET" kill-session -t "$SESSION"
   ```

2. **VERIFY socket file is removed (REQUIRED):**
   ```bash
   # Check if socket file still exists
   ls -la "$(dirname "$SOCKET")"
   ```

3. **Remove stale socket file if it exists (REQUIRED):**
   ```bash
   # If socket file remains after killing session/server
   rm -f "$SOCKET"
   ```

4. **Mark cleanup tasks completed in your task tracker** - after confirming the socket file is gone.

### Alternative Cleanup Methods

- **Kill all sessions on a socket:**
  ```bash
  tmux -S "$SOCKET" list-sessions -F '#{session_name}' | xargs -r -n1 tmux -S "$SOCKET" kill-session -t
  ```

- **Remove everything on the private socket (including all sessions):**
  ```bash
  tmux -S "$SOCKET" kill-server
  ```

**Finish cleanup by confirming the socket file is gone:**
1. `ls` the socket directory to confirm the file is removed
2. `rm -f "$SOCKET"` to clear any stale socket file
3. Mark your cleanup steps completed once the file is gone

## Troubleshooting

- **Timeout:** verify pattern, increase `-T`
- **Python:** check `PYTHON_BASIC_REPL=1`, verify `^>>> `
- **Cannot attach:** `tools/find-sessions.sh -S "$SOCKET"`
- **Session exists:** kill first
