---
name: tgbot
description: >
  Operate the tgbot CLI to send Telegram messages, files, and images from the terminal or from
  automated agent workflows. Use this skill whenever the user wants to send a Telegram message,
  notify a Telegram chat or channel, broadcast announcements, send files or images via Telegram,
  pipe command output to Telegram, or troubleshoot tgbot errors. Also use when the user mentions
  "tgbot", "telegram bot", "telegram notification", "send to telegram", "telegram alert",
  or any request involving Telegram messaging from the command line -- even if they don't
  explicitly name the tool.
---

# tgbot CLI Skill

tgbot is an agent-first Telegram Bot CLI already installed in PATH. It sends messages, files,
and images to Telegram chats/users with allowlist security and markdown rendering by default.

## Common Workflow

When the user asks to send a Telegram message, follow these steps:

### Step 1: Discover available bots and targets

```bash
tgbot list
```

This prints all configured bots, their targets (aliases + chat IDs), and default targets.
Pick the bot and target that match the user's intent. If the user names a specific bot or
target alias, use that. Otherwise, use the first bot with a suitable target or default.

If `tgbot list` shows no bots, tell the user tgbot is not configured yet and they need to
set up a bot first (see Setup section below).

### Step 2: Send the message

```bash
# Text message to a named target
tgbot send <bot> <target> '<text>'

# Text to the bot's default target (omit target)
tgbot send <bot> '<text>'

# Pipe content from stdin
echo '<text>' | tgbot send <bot> <target> -
cat report.txt | tgbot send <bot> <target> -

# File or image
tgbot send <bot> <target> --file ./path/to/file
tgbot send <bot> <target> --image ./path/to/image --caption 'Description'

# Broadcast to multiple targets
tgbot send <bot> --chats target1 --chats target2 '<text>'
```

Markdown is processed automatically. Use `--no-md` to send raw text.

### Step 3: Verify the result

On success, tgbot prints where it sent and the message ID:
```
Sent to devteam (group -1001234567890) via mybot
message_id: 42
```

On failure, it prints an error with a `hint` telling you what to do:
```
error: target: alias 'ops' not found in bot 'mybot'
hint: available aliases: devteam, alice.
```

For broadcast, each target result is printed, followed by a summary:
```
Sent to devteam (group -1001234567890) via mybot -- message_id: 42
Sent to alice (user 123456789) via mybot -- message_id: 43
error: target: alias 'ops' not found in bot 'mybot'
2 sent, 1 failed
```

---

## Few-Shot Examples

### Example 1: "Send a message to the dev team"

First, discover what's available:
```bash
tgbot list
```
Output:
```
notifier (CI bot)
  key: notifier
  default: devteam
  targets:
    devteam          group    -1001234567890
    alice            user     123456789
```
The bot `notifier` has a target `devteam`. Send:
```bash
tgbot send notifier devteam 'Build succeeded on main branch'
```

### Example 2: "Broadcast the release notes to all channels"

```bash
tgbot list
```
Output shows bot `releasebot` with targets `devteam`, `announcements`, `stakeholders`. Use
`--chats` for each:
```bash
tgbot send releasebot --chats devteam --chats announcements --chats stakeholders 'v2.1.0 released -- see changelog for details'
```
Partial failures are reported per-target; exit code is non-zero if any failed.

### Example 3: "Send this log file to alice"

```bash
tgbot list
```
Output shows bot `notifier` with user target `alice`. Send the file:
```bash
tgbot send notifier alice --file ./build.log --caption 'Build log from CI run #42'
```

### Example 4: "Pipe test results to telegram"

```bash
tgbot list
```
Output shows bot `cibot` with default target `devteam`. Pipe stdout:
```bash
pytest --tb=short 2>&1 | tgbot send cibot devteam -
```
The `-` argument reads from stdin.

### Example 5: "Send a screenshot to the dev group, no markdown"

```bash
tgbot list
```
Output shows bot `notifier` with target `devteam`. Send image with `--no-md` on caption:
```bash
tgbot send notifier devteam --image ./screenshot.png --caption 'UI regression on login page' --no-md
```

### Example 6: "Notify me when the build finishes"

After the build command completes, send the result:
```bash
tgbot list
```
Output shows bot `notifier` with user target `me`. Chain with the build:
```bash
make build 2>&1 | tail -n 20 > /tmp/build_output.txt && \
  tgbot send notifier me "Build passed" || \
  tgbot send notifier me "Build FAILED -- check logs"
```

---

## Error Categories and Exit Codes

| Category | Exit Code | Typical Cause |
|----------|-----------|---------------|
| config | 1 | Missing/invalid config files, key not found, bot not found |
| target | 2 | Alias not in allowlist, no default target set |
| file | 3 | File path doesn't exist |
| network | 4 | Connection timeout, DNS failure |
| api | 5 | Telegram API rejected the request (bad token, chat not found, rate limit) |
| markdown | 6 | Markdown conversion failure |

Every error includes a `hint` with actionable guidance. Common fixes:

| Error message pattern | Fix |
|-----------------------|-----|
| "key 'X' not found" | `tgbot key list` to check, then `tgbot key add` |
| "bot 'X' not found" | `tgbot list` to see configured bots |
| "alias 'X' not found" | `tgbot bot targets <bot>` to see allowed targets, or use `--force` |
| "no default target" | Provide target explicitly, or `tgbot bot set-default <bot> <alias>` |
| API 401 | Token is wrong/revoked; get new one from @BotFather |
| API 403 | Bot was kicked from chat or lacks permissions |
| API 429 | Rate limited; wait and retry (tgbot does not auto-retry) |

---

## JSON Output

Use `--json` only for debugging errors or piping into other tools (e.g. `jq`). Do not use
it for normal interactive sends.

```bash
# Debug a failing send
tgbot send mybot devteam 'test' --json

# Pipe into jq to extract message_id
tgbot send mybot devteam 'hello' --json | jq '.targets[0].message_id'

# Check bot config programmatically
tgbot list --json | jq '.bots[].name'
```

Response shapes:
- Success: `{"ok": true, "targets": [{"alias": "...", "message_id": ...}]}`
- Error: `{"error": "...", "category": "...", "hint": "...", "exit_code": N}`

---

## Setup (only when no bots are configured)

If `tgbot list` shows nothing, guide the user through setup. They need a bot token from
Telegram's @BotFather.

```bash
# 1. Store the API token
tgbot key add mybot '<token-from-botfather>'

# 2. Create a bot config referencing the key
tgbot bot add mybot --key mybot --description 'My bot'

# 3. Verify the token works
tgbot whoami mybot
```

### Adding groups/channels (recommended: use poll)

**NEVER run `tgbot bot poll` from an agent -- it blocks forever until Ctrl+C.**
Tell the user to run it themselves in their terminal.

The easiest way to add groups and channels is polling. Instruct the user to:

1. Add the bot as admin to the target group/channel on Telegram
2. Run `tgbot bot poll mybot` in their terminal
3. @mention the bot in each group/channel they want to add
4. Press Ctrl+C when done

The command auto-discovers groups/channels and saves them to the allowlist:
```
Polling as @mybot -- mention the bot in a group/channel.
Press Ctrl+C to stop.

Added 'dev-team' (group -1001234567890) to bot 'mybot'.
Added 'announcements' (channel -1009876543210) to bot 'mybot'.
```

Aliases are auto-generated from the chat title (lowercased, hyphenated, CJK preserved).
Chats already in the allowlist are silently skipped.

### Adding groups/channels (manual)

If you already know the chat ID, add directly:

```bash
tgbot bot allow mybot --chat devteam:group:-1001234567890
tgbot bot allow mybot --chat announcements:channel:-1009876543210
```

### Adding users (always manual)

Users must always be added manually with their numeric ID:

```bash
tgbot bot allow mybot --user alice:123456789
```

### Set a default target

```bash
tgbot bot set-default mybot devteam
```

---

## Reference

### Global flags

| Flag | Purpose |
|------|---------|
| `--config-dir PATH` | Override config dir (default: `~/.config/tgbot/`, env: `TGBOT_CONFIG_DIR`) |
| `--force` | Bypass allowlist checks |
| `--json` | JSON output mode |
| `--verbose` | Debug logging |

### Send options

| Option | Purpose |
|--------|---------|
| `--file PATH` | Send a document |
| `--image PATH` | Send a photo |
| `--caption TEXT` | Caption for file/image |
| `--no-md` | Disable markdown processing |
| `--chats TARGET` | Broadcast target (repeatable) |

### Key management

```
tgbot key add <name> <token>
tgbot key remove <name>
tgbot key update <name> <token>
tgbot key list
```

### Bot management

```
tgbot bot add <name> --key <key_name> [--description "..."]
tgbot bot remove <name>
tgbot bot show <name>
tgbot bot targets <name>
tgbot bot allow <name> --chat alias:type:id
tgbot bot allow <name> --user alias:id
tgbot bot deny <name> --chat <alias>
tgbot bot deny <name> --user <alias>
tgbot bot set-default <name> <alias>
tgbot bot clear-default <name>
```
