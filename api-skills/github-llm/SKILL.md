---
name: github-llm
description: >-
  Browse GitHub repository contents from the command line using a Cloudflare Worker HTTP mirror.
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

A Cloudflare Worker that mirrors GitHub repository paths under its own origin. Use it to browse repo contents and fetch files via simple HTTP requests -- no cloning, no CLI, no `gh` auth setup.

**Worker origin:** `https://github-llm.pobomp.workers.dev`

## How It Works

Take any GitHub URL and replace `https://github.com` with the worker origin. Keep the path unchanged.

| GitHub URL | Worker URL |
|---|---|
| `https://github.com/owner/repo` | `https://github-llm.pobomp.workers.dev/owner/repo` |
| `https://github.com/owner/repo/tree/main/src` | `https://github-llm.pobomp.workers.dev/owner/repo/tree/main/src` |
| `https://github.com/owner/repo/blob/main/README.md` | `https://github-llm.pobomp.workers.dev/owner/repo/blob/main/README.md` |

## URL Pattern

```
https://github-llm.pobomp.workers.dev/{owner}/{repo}/tree/{ref}/{path...}  -> directory listing (HTML)
https://github-llm.pobomp.workers.dev/{owner}/{repo}/blob/{ref}/{path...}  -> raw file contents
https://github-llm.pobomp.workers.dev/{owner}/{repo}                       -> repo root listing (HTML)
```

The conversion rule is straightforward -- this is all an LLM needs:

```
worker_url = github_url.replace("https://github.com", "https://github-llm.pobomp.workers.dev")
```

## When to Use This vs gh-llm CLI

| Aspect | This Worker | gh-llm CLI |
|---|---|---|
| Access method | HTTP fetch (curl, fetch, web_reader) | Shell commands |
| Best for | Remote/sandboxed environments, any tool that speaks HTTP | Local terminals with shell access |
| Output format | HTML directory listings, raw file bytes | Formatted tables, raw stdout |

If you have shell access and `gh-llm` is installed, the CLI may be more convenient. If you're in a sandboxed environment, working over HTTP, or the CLI isn't available, use this worker.

## Workflow

### 1. List repository contents

Fetch the repo root or a subdirectory to see what's there. Directory requests return HTML with a `<pre>` block containing links.

```bash
# Repo root (uses default branch)
curl -s https://github-llm.pobomp.workers.dev/owner/repo

# Specific branch/directory
curl -s https://github-llm.pobomp.workers.dev/owner/repo/tree/main/src
```

Or use `mcp__web_reader__webReader` / `WebFetch` to fetch and parse the HTML directory listing.

### 2. Read a file

Blob paths return raw file content, same as `raw.githubusercontent.com`.

```bash
curl -s https://github-llm.pobomp.workers.dev/owner/repo/blob/main/README.md
```

### 3. Explore incrementally

Start from the root, identify directories of interest from the listing, then drill in. Follow links from the HTML listing or construct URLs by hand.

## Tips

- Branch and tag names containing `/` are supported -- the worker resolves the ref vs path boundary automatically.
- `GET` and `HEAD` methods only. Other methods return 405.
- Public repos work without authentication (rate limited to 60 req/hr). The worker owner can configure a `GITHUB_TOKEN` for higher limits and private repo access.
- The worker uses the GitHub Contents API for metadata and `raw.githubusercontent.com` for file bytes. It does not scrape GitHub HTML pages.
- When fetching directory listings, the HTML output is minimal -- a `<pre>` block with links. Parse it accordingly; don't expect a full HTML page with semantic markup.
- For large files or binary content, the worker proxies directly from GitHub's CDN, so transfer is efficient.
