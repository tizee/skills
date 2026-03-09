---
name: hackernews
description: Fetch and explore Hacker News content via the official API. Use when the user wants to browse top/best/new/ask/show/job stories, get story details with comments, look up user profiles, search by keyword, or filter stories by time window (e.g. past 24h). Triggers on "hacker news", "HN stories", "HN front page", "trending on HN", "show hn", "ask hn", or any request to fetch or summarize Hacker News content.
---

# Hacker News

Fetch stories, comments, and user profiles from the Hacker News API.

## Invocation

Always use `hn` directly. It is already installed on PATH.

```bash
hn stories --type top --limit 10
```

Only if `hn` is not found (command not found error), fall back to api requests.

Default output is readable markdown. Add `--json` before the subcommand for structured JSON (for piping to `jq` or other tools).

## Commands

### stories

Fetch ranked story lists.

```
hn stories --type <type> --limit <N> [--since <duration>] [--keyword <query>]
```

| `--type` | Content |
|----------|---------|
| `top` | Front page (default, includes jobs) |
| `new` | Newest stories |
| `best` | Highest-rated |
| `ask` | Ask HN |
| `show` | Show HN |
| `job` | Job listings (Firebase only, no --since support) |

`--limit` defaults to 10. API max: 500 for top/new/best, 200 for ask/show/job.

#### Time-based search (--since)

Filter stories by time window using the Algolia Search API. Accepts duration strings:

| Duration | Meaning |
|----------|---------|
| `30m` | Past 30 minutes |
| `1h` | Past hour |
| `6h` | Past 6 hours |
| `24h` | Past 24 hours |
| `3d` | Past 3 days |
| `7d` | Past week |
| `2w` | Past 2 weeks |

When `--since` is used, the command switches from the Firebase API to the Algolia HN Search API. Results for `--type new` are sorted by date (newest first); all other types are sorted by relevance/points.

**Note:** `--type job` does not work with `--since` (Algolia does not index job posts separately).

#### Keyword search (--keyword)

Search stories by keyword. Can be combined with `--since` for time-bounded keyword search. Uses Algolia Search API.

#### Examples

```bash
# Top stories from the past 24 hours
hn stories --since 24h

# AI-related stories from the past week
hn stories --since 7d --keyword AI

# Newest Ask HN posts from the past 3 days
hn stories --type ask --since 3d

# Show HN posts about Rust from the past day, as JSON
hn --json stories --type show --since 24h --keyword rust

# Default: top stories from Firebase (no time filter)
hn stories --type top --limit 20
```

Output: numbered list with title, link, score, author, time, and comment count with HN discussion link.

### item

Fetch a single item (story, comment, job, poll).

```
hn item <id> [--with-comments] [--comment-depth N]
```

- `--with-comments`: recursively fetch the comment tree
- `--comment-depth N`: max recursion depth (default: 2). Keep low to avoid large fetches.

Without `--with-comments`, returns the item with comment count hint.

### user

Fetch a user profile.

```
hn user <username>
```

Returns karma, about, creation date, and the 20 most recent submission IDs.

### updates

Fetch recently changed items and profiles.

```
hn updates
```

## Installation

The `hn` tool is a Python package in the `hackernews-reader/` directory.

```bash
cd hackernews-reader
uv sync                  # install dependencies
uv tool install .        # install globally as `hn`
```

## Direct API Access

For queries the tool does not cover, use curl or `WebFetch` against the HN Firebase API or Algolia Search API directly.

Firebase API (see `references/api.md`):
```bash
curl -s https://hacker-news.firebaseio.com/v0/maxitem.json
curl -s https://hacker-news.firebaseio.com/v0/item/8863.json
```

Algolia Search API:
```bash
# Stories matching "rust" from past 24h
curl -s "http://hn.algolia.com/api/v1/search?tags=story&query=rust&numericFilters=created_at_i>$(date -v-24H +%s)"
```

## Tips

- Comment trees can be large. Start with `--comment-depth 1` and increase if needed.
- Firebase API has no rate limit, but batch fetching many items creates many HTTP requests. Keep `--limit` reasonable.
- Algolia API is rate-limited to 10,000 requests/hour per IP.
- Markdown output converts HTML to readable text (links preserved, tags stripped). Use `--json` for raw HTML fields.
- User `submitted` lists can contain thousands of IDs; the tool returns only the 20 most recent.
- When `--since` and `--keyword` are both omitted, the tool uses the Firebase API (identical to the original behavior).
