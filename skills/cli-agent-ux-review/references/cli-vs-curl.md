# Why CLI is Better Than API + curl for Agents

This document explains why wrapping an API behind a CLI produces better Agent Experience (AX) than having agents call the API directly via curl. The end result is functionally identical — the same data flows, the same operations happen — but the ergonomics for agents are radically different, like hand-tightening a screw versus using a power drill.

## The three problems with API + curl

### 1. Credentials leak into agent context

When an agent uses curl, it must interpolate credentials directly into the command:

```bash
curl -H "Authorization: Bearer sk-abc123..." https://api.example.com/data
```

This is dangerous for three reasons:

- **The token is now in the agent's context window.** Context windows can be logged, cached, or exfiltrated via prompt injection. Treat anything in context as potentially public.
- **Credentials get lost.** If the agent generates a token during registration, it appears in stdout once. If the conversation ends or the context compacts, the token is gone. No recovery path.
- **Complex auth flows break agents.** If the API requires OAuth-style token exchange (client ID + secret to get a short-lived access token), the agent must execute a multi-step auth dance before every API call. This is fragile — agents frequently get stuck in the auth step and never reach the actual task.

A CLI solves all three by handling credentials internally:

```bash
# One-time setup — credentials stored in ~/.config/tool/
tool register --name "MyAgent"

# All subsequent calls — no credentials in context
tool search --q "pdf editor"
```

The agent never sees, stores, or transmits the credential. The CLI manages token refresh, persistence, and recovery transparently.

### 2. API responses waste tokens and confuse agents

API responses are designed for application frontends — they contain pagination metadata, HATEOAS links, nested relationship objects, null fields, and envelope wrappers that an agent doesn't need. A typical API response:

```json
{
  "data": [
    {
      "id": "skill-123",
      "type": "skill",
      "attributes": {
        "name": "PDF Editor",
        "description": "Edit PDFs",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-06-15T12:00:00Z",
        "author_id": "user-456",
        "download_count": 1523,
        "rating": 4.2,
        "tags": ["pdf", "editor"],
        "metadata": { "version": "2.1.0", "license": "MIT" }
      },
      "relationships": {
        "author": { "data": { "id": "user-456", "type": "user" } },
        "category": { "data": { "id": "cat-7", "type": "category" } }
      }
    }
  ],
  "meta": { "total": 47, "page": 1, "per_page": 20 },
  "links": {
    "self": "https://api.example.com/skills?q=pdf+editor&page=1",
    "next": "https://api.example.com/skills?q=pdf+editor&page=2"
  }
}
```

A CLI can reduce this to what the agent actually needs:

```
PDF Editor (skill-123)
  Edit PDFs
  v2.1.0 | MIT | 1523 downloads
```

Real-world measurements show CLI output consuming **10-20% of the tokens** that the equivalent JSON API response uses. That is a 5-10x reduction in cost and context window pressure per tool invocation. When an agent calls a tool dozens of times in a session, this compounds.

### 3. curl has no monitoring or identity story

When an agent calls an API via curl, the request looks identical to any other HTTP client. The server sees a generic User-Agent (`curl/8.x` or `node-fetch`), with no way to distinguish:

- Agent traffic from human traffic
- One agent from another
- Legitimate use from abuse

A CLI can embed its own User-Agent header, version, and client ID automatically. The tool author gets visibility into how agents use the tool, which commands are popular, where agents fail — all essential for improving the AX.

This also matters for rate limiting and abuse prevention. With curl, the only option is IP-based throttling. With a CLI, you can do per-client rate limiting, usage tracking, and graduated access — all transparently.

## The deeper principle: From UX to AX

The shift from API + curl to CLI reflects a broader shift in tool design thinking. Traditional tools optimize for **User Experience (UX)** — the human at the keyboard. Agent-friendly tools optimize for **Agent Experience (AX)** — the AI model reading stdout.

These often overlap (clear output is good for both), but diverge in key areas:

| Aspect | UX priority | AX priority |
| --- | --- | --- |
| Output | Visual layout, colors, alignment | Parseable structure, low token count |
| Auth | Interactive login flow | Silent credential management |
| Errors | Friendly message with emoji | Structured error with exit code |
| Progress | Spinner, progress bar | Quiet mode, result only |
| Confirmation | Interactive y/n prompt | `--yes` flag, `--dry-run` preview |

The CLI is the best interface layer between APIs and agents because it can optimize for AX while keeping the underlying API intact for applications that need it. It is a translation layer — from machine-to-machine protocol (HTTP/JSON) to agent-to-tool protocol (stdin/stdout/stderr with conventions).
