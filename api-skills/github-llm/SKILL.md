---
name: github-llm
description: >-
  Browse GitHub repository contents via a Cloudflare Worker HTTP mirror.
  Use this skill whenever the user wants to list files in a GitHub repo, read file contents from GitHub,
  explore a repository's directory structure, or fetch a specific file from GitHub -- all without cloning.
  Also use when the user mentions "github-llm", "github mirror", or provides GitHub URLs they want to inspect.
  This is the HTTP-based complement to the `gh-llm` CLI skill -- use this one when HTTP access is preferred
  or when the CLI tool is not available.
  Triggers on requests like "show me the files in this GitHub repo", "read README from owner/repo",
  "list the contents of https://github.com/owner/repo", "what's in this repo", "cat this file from GitHub",
  "fetch file from GitHub", or any task involving browsing GitHub repository trees and files without cloning.
---

# GitHub LLM Worker

A Cloudflare Worker that mirrors GitHub repository paths. Browse repo contents and fetch files via simple GET requests -- no cloning, no CLI, no auth.

**Base URL:** `https://github-llm.pobomp.workers.dev`

## URL Pattern

All requests are GET. Replace `https://github.com` with the base URL -- keep the path unchanged.

```
{base}/owner/repo                         -> repo root listing (HTML)
{base}/owner/repo/tree/{ref}/{path...}    -> directory listing (HTML)
{base}/owner/repo/blob/{ref}/{path...}    -> raw file contents
```

The conversion rule:

```
worker_url = github_url.replace("https://github.com", "https://github-llm.pobomp.workers.dev")
```

| GitHub URL | Worker URL |
|---|---|
| `https://github.com/owner/repo` | `https://github-llm.pobomp.workers.dev/owner/repo` |
| `https://github.com/owner/repo/tree/main/src` | `https://github-llm.pobomp.workers.dev/owner/repo/tree/main/src` |
| `https://github.com/owner/repo/blob/main/README.md` | `https://github-llm.pobomp.workers.dev/owner/repo/blob/main/README.md` |

## Usage by Environment

### Web / Mobile Chat Apps (no shell access)

If you only have a built-in web fetch tool (e.g. `web_reader`, `browser`, `fetch`, `url_fetch`):

1. **Construct the GET URL** using the pattern above
2. **Fetch it** with whatever built-in tool your platform provides
3. Directory listings return minimal HTML (`<pre>` with links) -- parse or read as-is
4. File (blob) paths return raw content directly

Example -- read a file:
```
Fetch: https://github-llm.pobomp.workers.dev/anthropics/anthropic-cookbook/blob/main/README.md
```

Example -- list a directory:
```
Fetch: https://github-llm.pobomp.workers.dev/anthropics/anthropic-cookbook/tree/main/misc
```

No curl, no shell, no POST -- just GET the URL.

### CLI Coding Agents (shell access)

With shell access you get more flexibility: pipe, save to files, chain commands.

```bash
# List repo root
curl -s https://github-llm.pobomp.workers.dev/owner/repo

# Read a file
curl -s https://github-llm.pobomp.workers.dev/owner/repo/blob/main/README.md

# Save large file locally
curl -s https://github-llm.pobomp.workers.dev/owner/repo/blob/main/src/main.rs > /tmp/main.rs
```

Or use `WebFetch` / `mcp__web_reader__webReader` if available in your agent toolkit.

## Workflow: Incremental Exploration

1. Start from the repo root URL to get the top-level listing
2. Identify directories of interest from the listing
3. Append `/tree/{ref}/{dir}` to drill into subdirectories
4. Switch to `/blob/{ref}/{file}` to read specific files

## Notes

- **GET and HEAD only.** Other methods return 405.
- Branch/tag names containing `/` are supported -- the worker resolves ref vs path automatically.
- Public repos work without auth (rate limited to 60 req/hr). The worker owner can configure a `GITHUB_TOKEN` for higher limits and private repo access.
- Directory listings are minimal HTML (`<pre>` block with links), not full pages.
- File content is proxied from GitHub's CDN -- efficient for large/binary files.
