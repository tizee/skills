---
name: pdf2md-api
description: Convert PDFs to markdown, plain text, or JSON via the pdf2md HTTP API. Use this skill whenever you need to convert a PDF from a URL, an arxiv paper, or an uploaded file to readable text using the remote pdf2md-service, rather than a local CLI tool. Triggers on "convert this PDF URL", "fetch arxiv paper as markdown", "pdf2md api", "upload PDF to convert", or any task that involves calling the pdf2md worker endpoint for PDF conversion. Also use when the user wants to read a remote PDF and the local `pdf2md` CLI is not available or not appropriate.
---

# pdf2md API

Convert PDFs to markdown, plain text, or JSON via the pdf2md-service HTTP API (Cloudflare Worker proxy -> Python backend).

Base URL: `https://pdf2md-worker.pobomp.workers.dev`

No authentication required.

## Endpoints

### Convert arxiv paper

```
GET /arxiv/{paper_id}
```

Paper ID formats: `2301.12345`, `2301.12345v2`, `hep-th/9901001`

```bash
curl -s "https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031"
```

### Convert PDF from URL

```
GET /url/{pdf-url}
```

The full PDF URL goes directly in the path (no encoding needed for simple URLs):

```bash
curl -s "https://pdf2md-worker.pobomp.workers.dev/url/https://example.com/paper.pdf"
```

### Upload PDF file

```
POST /file
```

```bash
curl -s -X POST \
  -H "Content-Type: application/pdf" \
  --data-binary @paper.pdf \
  "https://pdf2md-worker.pobomp.workers.dev/file"
```

Max file size: 20MB (returns 413 if exceeded).

### Health check

```
GET /health
```

Returns cache stats:

```bash
curl -s "https://pdf2md-worker.pobomp.workers.dev/health"
```

## Output Formats

All conversion endpoints default to markdown. Use `?format=` to change:

| Value | Content-Type | Description |
|-------|-------------|-------------|
| `markdown` | `text/markdown` | Default. Clean markdown with tables, headers, structure |
| `text` | `text/plain` | Plain text, tables as ASCII grids |
| `json` | `application/json` | Structured JSON with layout data |

```bash
# Plain text
curl -s "https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031?format=text"

# JSON
curl -s "https://pdf2md-worker.pobomp.workers.dev/arxiv/2603.15031?format=json"
```

## Error Responses

All errors return JSON `{"error": "<message>"}`:

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid paper ID, missing params) |
| 413 | File too large |
| 502 | Backend unavailable |

## Agent Workflow

When converting a remote PDF or arxiv paper:

1. Call the appropriate endpoint with `curl`
2. Pipe output to a temp file if large: `curl ... > /tmp/converted.md`
3. Read the temp file with the Read tool to answer the user's question

When the user provides an arxiv ID or link:
- Extract the paper ID from the URL if needed (e.g. `https://arxiv.org/abs/2301.12345` -> `2301.12345`)
- Use the `/arxiv/` endpoint

When the user provides a PDF URL:
- Use the `/url/` endpoint with the URL in the path

When the user has a local PDF file:
- Use the `/file` endpoint with `--data-binary @<filepath>`
