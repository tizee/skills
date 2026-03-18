---
name: pdf2md
description: Convert PDF files to clean markdown, plain text, or JSON using pymupdf4llm. Use this skill whenever the user wants to read a PDF as text, convert PDF to markdown/JSON, extract tables or equations from PDFs, OCR scanned PDFs, or process any PDF for LLM-readable output. Also use when the user mentions "pdf2md", asks to "read this PDF", "convert to markdown", "extract tables from PDF", "what does this PDF say", or needs high-quality PDF text extraction that preserves structure, tables, math, and formatting. If the user mentions a .pdf file and wants to read or understand its contents, use this skill.
---

# PDF to Markdown with pdf2md

Convert PDF files to clean, LLM-readable markdown using `pdf2md` -- a CLI tool built on [pymupdf4llm](https://github.com/pymupdf/pymupdf4llm). No GPU, no ML models, minimal memory. Handles tables, headers, multi-column layouts, images, code blocks, and form fields.

## Prerequisites

`pdf2md` must be installed as a uv tool. Before first use, check availability:

```bash
which pdf2md
```

If not found, tell the user to install it first:

```bash
git clone --depth 1 git@github.com/tizee/pdf2md.git
cd pdf2md && uv tool install .
```

## CLI Usage

```bash
pdf2md INPUT_FILE [OPTIONS]
```

Output goes to stdout by default. Use `-o` to write to a file.

### Key options

| Option | Description |
|--------|-------------|
| `-o, --output FILE` | Write to file instead of stdout |
| `-f, --format [markdown\|text\|json]` | Output format (default: markdown) |
| `-p, --pages "0-4"` | Pages to extract, 0-based. Ranges: `"0-4"`, lists: `"0,2,5"`, mixed: `"0-2,7"` |
| `--images / --no-images` | Extract images to disk |
| `--embed-images` | Embed images as base64 in output |
| `--image-dir DIR` | Directory for extracted images |
| `--dpi N` | Image resolution (default: 150) |
| `--page-chunks` | Output per-page chunks as JSON array |
| `--no-header` | Exclude page headers |
| `--no-footer` | Exclude page footers |
| `--page-separators` | Insert `--- end of page=n ---` between pages |
| `--table-strategy STR` | Table detection: `lines_strict` (default) or `lines` |
| `--form-fields` | Extract form field key-value pairs (Form PDFs). Outputs JSON |
| `--show-progress` | Show progress bar |

### Common recipes

```bash
# Read PDF to stdout (pipe to less, grep, etc.)
pdf2md document.pdf

# Save as markdown file
pdf2md document.pdf -o output.md

# First 3 pages only
pdf2md document.pdf -p "0-2" -o output.md

# Plain text (tables as ASCII grids)
pdf2md document.pdf -f text

# Structured JSON output
pdf2md document.pdf -f json -o output.json

# Extract with images
pdf2md document.pdf --images --image-dir /tmp/imgs -o output.md

# Skip repetitive headers/footers
pdf2md document.pdf --no-header --no-footer -o clean.md

# Per-page chunks for RAG
pdf2md document.pdf --page-chunks -o chunks.json

# Extract form fields
pdf2md form.pdf --form-fields
```

## Agent workflow

**Step 0 (first use only):** Run `which pdf2md` to check if the CLI is installed. If not found, notify the user to install it by cloning `git@github.com/tizee/pdf2md.git` and running `uv tool install .` in the cloned directory.

When the user asks to read or understand a PDF:

1. Run `pdf2md <file> -o /tmp/pdf_output.md` via Bash
2. Read `/tmp/pdf_output.md` with the Read tool
3. Answer the user's question based on the extracted content

When the user asks to convert a PDF:

1. Run `pdf2md` with the desired options and `-o` pointing to the user's preferred location
2. Tell the user where the output was saved

For large PDFs:

- Use `-p` to limit pages
- Use `--page-separators` to see page boundaries
- Read the output in chunks with the Read tool's `offset`/`limit` parameters

## Python API (for scripting)

When building scripts that need programmatic access, use pymupdf4llm directly:

```python
import pymupdf4llm

# Full document to markdown
md = pymupdf4llm.to_markdown("doc.pdf")

# Specific pages
md = pymupdf4llm.to_markdown("doc.pdf", pages=[0, 1, 2])

# Per-page chunks with metadata
chunks = pymupdf4llm.to_markdown("doc.pdf", page_chunks=True)
for chunk in chunks:
    print(chunk["metadata"]["page_number"], chunk["text"][:100])

# With images
md = pymupdf4llm.to_markdown("doc.pdf", write_images=True, image_path="/tmp/imgs/")

# Plain text
txt = pymupdf4llm.to_text("doc.pdf")

# JSON with layout boxes
data = pymupdf4llm.to_json("doc.pdf")

# Form fields
fields = pymupdf4llm.get_key_values("form.pdf")
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Garbled text from scanned PDF | Use `force_ocr=True` with an `ocr_function` in Python API |
| Missing tables | Try `--table-strategy lines` instead of default `lines_strict` |
| Too much noise from headers/footers | Use `--no-header --no-footer` |
| Images not in output | Use `--images --image-dir /tmp/imgs` |
| Import error / version mismatch | `pip install -U pymupdf4llm` (requires matching pymupdf version) |
