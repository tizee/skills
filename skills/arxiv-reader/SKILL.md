---
name: arxiv-reader
description: Read, summarize, or explain any arxiv paper. Supports arxiv.org URLs (abs, pdf, html), paper IDs, and alphaxiv.org URLs. Use when user shares an arxiv link, mentions a paper ID, or asks about a research paper.
---

# Arxiv Reader

Read, summarize, or explain any arxiv paper. Default approach fetches the arxiv HTML page directly via WebFetch, with alphaxiv.org as a supplementary source for structured overviews.

## When to Use

- User shares any arxiv URL (e.g. `arxiv.org/abs/2401.12345`, `arxiv.org/pdf/2401.12345`, `arxiv.org/html/2603.02473v1`)
- User mentions a paper ID (e.g. `2401.12345`, `2603.02473v1`)
- User asks you to read, explain, summarize, or analyze an arxiv research paper
- User shares an alphaxiv URL (e.g. `alphaxiv.org/overview/2401.12345`)
- User pastes a link to a paper and wants to understand it

## Workflow

### Step 1: Extract the paper ID

Parse the paper ID from whatever the user provides:

| Input                                      | Paper ID       |
| ------------------------------------------ | -------------- |
| `https://arxiv.org/abs/2401.12345`         | `2401.12345`   |
| `https://arxiv.org/pdf/2401.12345`         | `2401.12345`   |
| `https://arxiv.org/html/2603.02473v1`      | `2603.02473v1` |
| `https://alphaxiv.org/overview/2401.12345` | `2401.12345`   |
| `2401.12345v2`                             | `2401.12345v2` |
| `2401.12345`                               | `2401.12345`   |

### Step 2: Fetch the paper via arxiv HTML (primary)

Use WebFetch to get the arxiv HTML page directly. This works for all papers including newly published ones:

```
WebFetch(url="https://arxiv.org/html/{PAPER_ID}", selector="article", no_js=true)
```

- `selector="article"` extracts the main paper content, skipping navigation and boilerplate.
- `no_js=true` since arxiv HTML pages are static — no JavaScript rendering needed.
- This is the **default and preferred** method. It always has the latest papers.

If the HTML version is not available (some older papers only have PDF), proceed to Step 3.

### Step 3: Fetch alphaxiv overview (supplementary)

alphaxiv.org provides AI-generated structured overviews, but may not have new papers yet.

```bash
curl -s "https://alphaxiv.org/overview/{PAPER_ID}.md"
```

Returns a structured, detailed analysis optimized for LLM consumption. One call, plain markdown, no JSON parsing.

If this also returns 404, try the full text extraction:

```bash
curl -s "https://alphaxiv.org/abs/{PAPER_ID}.md"
```

### Step 4: Last resort — PDF

If both HTML and alphaxiv are unavailable, direct the user to the PDF:

```
https://arxiv.org/pdf/{PAPER_ID}
```

## Error Handling

- **arxiv HTML unavailable**: Some older papers lack HTML versions. Fall through to alphaxiv.
- **alphaxiv 404**: Paper not yet processed by alphaxiv. Expected for very new papers.
- **Both unavailable**: Point user to the PDF URL.

## Notes

- No authentication required — all endpoints are public.
- Prefer arxiv HTML over alphaxiv because arxiv has zero latency for new papers.
- Use alphaxiv when you want its AI-generated structured overview as a supplement, not as the primary source.
