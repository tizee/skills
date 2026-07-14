# zhu-reinit

A user-only skill for the **Zhu** coding agent that refreshes the current
repository's durable agent guidance (`AGENTS.md` / `CLAUDE.md`) from evidence in
recent agent work — preserving facts the agent repeatedly rediscovered and
conventions the user explicitly corrected, while filtering out transient session
state.

## Usage

Invoke explicitly from the current repository:

```
/zhu-reinit
```

It never runs automatically (`disable-model-invocation: true`); only the user
triggers it via the slash command. On invocation it reviews the visible
conversation and, when available, recent Zhu session transcripts, then applies a
retention test and makes the smallest coherent edit to the canonical guidance
file. See [`SKILL.md`](./SKILL.md) for the full workflow and retention rules.

## Layout

```
zhu-reinit/
├── SKILL.md                    # skill definition (workflow, retention test, writing rules)
├── README.md                   # this file
└── scripts/
    └── zhu_session_to_md.py    # render a Zhu JSONL transcript to a compact markdown handoff
```

The helper script is Zhu-specific: it parses Zhu's append-only session log
record shapes (`session_meta` / `message` / `token_usage`) at
`~/.llms/sessions/<YYYY>/<MM>/<DD>/llms-<timestamp>-<session-id>.jsonl`.

## Credit

Adapted from the upstream **reinit** skill by [aisk](https://github.com/aisk):
<https://github.com/aisk/reinit> (see its
[`SKILL.md`](https://github.com/aisk/reinit/blob/master/SKILL.md)).

Changes in this Zhu port:

- Rewritten the local-history reference to Zhu's session-log location and
  format; removed the other-agent transcript locations to avoid confusion.
- Added the Zhu-only `scripts/zhu_session_to_md.py` transcript renderer.
- Renamed the skill to `zhu-reinit` (slash command `/zhu-reinit`).
