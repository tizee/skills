---
name: pdf2md-api
description: >-
  Convert PDFs to markdown, plain text, or JSON via the pdf2md HTTP API.
  Use this skill whenever you need to convert a PDF from a URL, an arxiv paper, or an uploaded file
  to readable text using the remote pdf2md-service, rather than a local CLI tool.
  Triggers on "convert this PDF URL", "fetch arxiv paper as markdown", "pdf2md api",
  "upload PDF to convert", or any task that involves calling the pdf2md worker endpoint for PDF conversion.
  Also use when the user wants to read a remote PDF and the local `pdf2md` CLI is not available.
---

# pdf2md API

Convert PDFs to markdown, plain text, or JSON via HTTP. Cloudflare Worker proxy -> Python backend.

**Base URL:** `https://pdf2md-worker.pobomp.workers.dev`

No authentication required.

## GET Endpoints (all environments)

These endpoints work in any environment -- CLI agents, web chat apps, mobile apps. Just construct the URL and fetch it.

### Convert arxiv paper

```
GET /arxiv/{paper_id}
```

Paper ID formats: `2301.12345`, `2301.12345v2`, `hep-th/9901001`

Extract the paper ID from arxiv URLs:
- `https://arxiv.org/abs/2301.12345` -> `2301.12345`
- `https://arxiv.org/pdf/2301.12345` -> `2301.12345`

Full URL to fetch:
```
https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031
```

### Convert PDF from URL

```
GET /url/{pdf-url}
```

The full PDF URL goes directly in the path (no encoding needed for simple URLs):

```
https://pdf2md-worker.pobomp.workers.dev/url/https://example.com/paper.pdf
```

### Output format

All GET endpoints default to markdown. Append `?format=` to change:

| Value | Content-Type | Description |
|-------|-------------|-------------|
| `markdown` | `text/markdown` | Default. Clean markdown with tables, headers, structure |
| `text` | `text/plain` | Plain text, tables as ASCII grids |
| `json` | `application/json` | Structured JSON with layout data |

```
https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031?format=text
https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031?format=json
```

### Health check

```
GET /health
```

Returns cache stats.

## Usage by Environment

### Web / Mobile Chat Apps (no shell access)

If you only have a built-in web fetch tool (e.g. `web_reader`, `browser`, `fetch`, `url_fetch`):

1. **Construct the GET URL** from the patterns above
2. **Fetch it** with whatever built-in tool your platform provides
3. The response is the converted content (markdown by default)

Example -- convert an arxiv paper:
```
Fetch: https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031
```

Example -- convert a PDF URL:
```
Fetch: https://pdf2md-worker.pobomp.workers.dev/url/https://example.com/doc.pdf
```

No curl, no shell, no POST -- just GET the URL.

### CLI Coding Agents (shell access)

With shell access you get more flexibility: pipe, save to files, upload local PDFs.

```bash
# Convert arxiv paper
curl -s "https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031"

# Convert PDF from URL, save locally
curl -s "https://pdf2md-worker.pobomp.workers.dev/url/https://example.com/paper.pdf" > /tmp/converted.md

# Upload a local PDF file (CLI-only)
curl -s -X POST \
  -H "Content-Type: application/pdf" \
  --data-binary @paper.pdf \
  "https://pdf2md-worker.pobomp.workers.dev/file"
```

Or use `WebFetch` / `mcp__web_reader__webReader` for the GET endpoints if available.

## POST Endpoint (CLI-only)

### Upload PDF file

```
POST /file
Content-Type: application/pdf
Body: raw PDF bytes
```

Max file size: 20MB (returns 413 if exceeded).

This endpoint requires sending a POST with binary body -- only usable from environments with shell access or HTTP client libraries. Not available in web/mobile chat apps.

## Error Responses

All errors return JSON `{"error": "<message>"}`:

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid paper ID, missing params) |
| 413 | File too large |
| 502 | Backend unavailable |
