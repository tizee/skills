---
name: obsidian-cli
description: Interact with Obsidian vaults using the Obsidian CLI to read, create, search, and manage notes, tasks, properties, and more. Also supports plugin and theme development with commands to reload plugins, run JavaScript, capture errors, take screenshots, and inspect the DOM. Use when the user asks to interact with their Obsidian vault, manage notes, search vault content, perform vault operations from the command line, or develop and debug Obsidian plugins and themes.
---

# Obsidian CLI

Use the `obsidian` CLI to interact with a running Obsidian instance. Requires Obsidian to be open.

## Command reference

Run `obsidian help` to see all available commands. This is always up to date. Full docs: https://help.obsidian.md/cli

## Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian create name="My Note" silent overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

## File targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension needed)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

## Vault targeting

Commands target the most recently focused vault by default. Use `vault=<name>` as the first parameter to target a specific vault:

```bash
obsidian vault="My Vault" search query="test"
```

## Creating notes

### File placement

`create name="My Note"` places files at the **vault root**. To create notes in a specific folder, always use `path=`:

```bash
obsidian create path="pages/My Note.md" template="tech-note-template" silent
```

Before creating, discover the vault's folder structure with `obsidian folders` to find the correct notes directory.

### Templates and content

When `template=` is provided, the CLI triggers Obsidian's template insertion (including Templater plugin variables like `<% tp.file.title %>`). Key behaviors:

- `template=` fully resolves Templater `<% tp.* %>` syntax — dates, titles, etc. are expanded
- `template:read resolve` only resolves core template variables (`{{title}}`, `{{date}}`), **not** Templater plugin syntax
- When both `template=` and `content=` are provided, **template wins and content is ignored**

**Correct workflow** to create a note from template then add content:

```bash
# 1. Create with template (resolves all Templater variables)
obsidian create path="pages/My Note.md" template="tech-note-template" silent

# 2. Append or overwrite to fill in body content
obsidian create path="pages/My Note.md" content="..." overwrite silent
```

To discover available templates: `obsidian templates`

### Properties (YAML frontmatter)

Note frontmatter is YAML. `property:set` must use the correct `type=` to produce valid YAML for each property. Omitting `type=` defaults to plain text, which breaks structured fields.

Supported types: `text`, `list`, `number`, `checkbox`, `date`, `datetime`

```bash
# list — produces YAML list (- item\n- item\n...)
obsidian property:set name="tags" type="list" value="git, hooks" file="My Note"
obsidian property:set name="aliases" type="list" value="alias1, alias2" file="My Note"

# text (default)
obsidian property:set name="status" value="draft" file="My Note"

# number
obsidian property:set name="priority" type="number" value="1" file="My Note"

# checkbox
obsidian property:set name="published" type="checkbox" value="true" file="My Note"

# date / datetime
obsidian property:set name="due" type="date" value="2026-03-11" file="My Note"
obsidian property:set name="created" type="datetime" value="2026-03-11T10:00" file="My Note"
```

**Common mistake:** omitting `type="list"` for tags/aliases writes a comma-separated string instead of a YAML list, which Obsidian marks as invalid frontmatter.

## Common patterns

```bash
obsidian read file="My Note"
obsidian create path="folder/New Note.md" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian property:set name="tags" type="list" value="tag1, tag2" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
obsidian folders
obsidian templates
```

Use `--copy` on any command to copy output to clipboard. Use `silent` to prevent files from opening. Use `total` on list commands to get a count.

## Agent workflows

### Workflow 1: Add a knowledge note to a vault

Use when the user or agent wants to capture a learning, solution, or discovery as a structured note.

**Steps:**

1. **Discover vault structure** — find the notes folder and available templates:
   ```bash
   obsidian vault="<vault>" folders
   obsidian vault="<vault>" templates
   ```

2. **Create note with template** — use `path=` to place in the correct folder; `silent` to avoid opening:
   ```bash
   obsidian vault="<vault>" create path="<notes-folder>/<Note Title>.md" template="<template-name>" silent
   ```

3. **Set frontmatter properties** — use correct `type=` for each property:
   ```bash
   obsidian vault="<vault>" property:set name="tags" type="list" value="tag1, tag2" file="<Note Title>"
   ```

4. **Verify template resolution** — read back to confirm Templater variables expanded:
   ```bash
   obsidian vault="<vault>" read file="<Note Title>"
   ```

5. **Write body content** — overwrite with full content (frontmatter + body) since template sections are now resolved:
   ```bash
   obsidian vault="<vault>" create path="<notes-folder>/<Note Title>.md" overwrite content="<full note content with frontmatter>" silent
   ```

6. **Final verification**:
   ```bash
   obsidian vault="<vault>" read file="<Note Title>"
   ```

**Example** — recording a dev solution:
```bash
# 1. Discover
obsidian vault="development" folders
obsidian vault="development" templates

# 2. Create from template
obsidian vault="development" create path="pages/Git - Hook chaining.md" template="tech-note-template" silent

# 3. Set tags
obsidian vault="development" property:set name="tags" type="list" value="git, hooks" file="Git - Hook chaining"

# 4. Read back (verify Templater resolved)
obsidian vault="development" read file="Git - Hook chaining"

# 5. Overwrite with full content (preserve resolved frontmatter, fill in body)
obsidian vault="development" create path="pages/Git - Hook chaining.md" overwrite content="---\ncreation date: 2026-03-11\ntags:\n  - git\n  - hooks\n---\n\n# Git - Hook chaining\n\n## What is it?\n\n..." silent

# 6. Verify
obsidian vault="development" read file="Git - Hook chaining"
```

### Workflow 2: Append to an existing note

Use when adding new content to an existing note (e.g. appending a log entry, adding a section).

```bash
# Append a new section
obsidian vault="<vault>" append file="<Note Title>" content="\n## New Section\n\nContent here."

# Append a task to daily note
obsidian vault="<vault>" daily:append content="- [ ] Review PR #42"
```

### Workflow 3: Search and read from a vault

Use when the agent needs to look up existing knowledge before creating new notes (avoid duplicates).

```bash
# 1. Search for existing notes on the topic
obsidian vault="<vault>" search query="hook chaining" limit=5

# 2. Read a matching note for context
obsidian vault="<vault>" read file="<matched note>"

# 3. If no match, proceed with Workflow 1 to create a new note
```

### Workflow 4: Update properties on existing notes

Use when bulk-updating metadata (e.g. adding tags, changing status).

```bash
# Read current properties
obsidian vault="<vault>" properties file="<Note Title>"

# Update
obsidian vault="<vault>" property:set name="status" value="published" file="<Note Title>"
obsidian vault="<vault>" property:set name="tags" type="list" value="git, hooks, new-tag" file="<Note Title>"
```

**Important:** `property:set` for list types **replaces** the entire list. To add a tag, read current tags first, then set the full list including the new one.

## Plugin development

### Develop/test cycle

After making code changes to a plugin or theme, follow this workflow:

1. **Reload** the plugin to pick up changes:
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **Check for errors** — if errors appear, fix and repeat from step 1:
   ```bash
   obsidian dev:errors
   ```
3. **Verify visually** with a screenshot or DOM inspection:
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **Check console output** for warnings or unexpected logs:
   ```bash
   obsidian dev:console level=error
   ```

### Additional developer commands

Run JavaScript in the app context:

```bash
obsidian eval code="app.vault.getFiles().length"
```

Inspect CSS values:

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

Toggle mobile emulation:

```bash
obsidian dev:mobile on
```

Run `obsidian help` to see additional developer commands including CDP and debugger controls.
