#!/usr/bin/env python3
"""Convert a Zhu session JSONL transcript into a handoff markdown document.

Parses Zhu's append-only session log record shapes: `session_meta`, `message`
(payload.role of assistant/user/tool), and `token_usage`. Zhu logs live at
`~/.llms/sessions/<YYYY>/<MM>/<DD>/llms-<timestamp>-<session-id>.jsonl`.

Usage:
    python3 zhu_session_to_md.py <path/to/session.jsonl>          # output to same dir
    python3 zhu_session_to_md.py <path/to/session.jsonl> -o out.md
    python3 zhu_session_to_md.py <path/to/session.jsonl> -n 10    # keep last 10 tool results
"""

import argparse
import json
import os
import sys


def parse_args():
    p = argparse.ArgumentParser(
        description="Convert Zhu JSONL session transcript to markdown handoff doc"
    )
    p.add_argument("input", help="Path to session .jsonl file")
    p.add_argument(
        "-o", "--output",
        help="Output .md path (default: <input_stem>.md in same directory)",
    )
    p.add_argument(
        "-n", "--keep-tool-results",
        type=int,
        default=5,
        help="Number of last tool results to preserve (default: 5)",
    )
    return p.parse_args()


def extract_session_id(filepath: str) -> str:
    basename = os.path.splitext(os.path.basename(filepath))[0]
    # llms-2026-07-12T11-30-19-35e23b58-2473-4e7a-bc7c-7a19764d22d9
    parts = basename.rsplit("-", 5)
    if len(parts) == 6:
        return "-".join(parts[1:])  # drop "llms-" prefix
    return basename


def format_tool_call_args(args_str: str) -> str:
    """Turn JSON tool-call args into a short readable label."""
    try:
        obj = json.loads(args_str)
    except (json.JSONDecodeError, TypeError):
        return "?"

    if "file_path" in obj:
        return f"`{obj['file_path']}`"
    if "command" in obj:
        cmd = obj["command"]
        return f"`{cmd[:80]}{'...' if len(cmd) > 80 else ''}`"
    if "name" in obj:
        return f"skill `{obj['name']}`"
    return ""


def main():
    args = parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # ── first pass: index tool-result lines ──────────────────────────
    tool_result_indices: list[int] = []
    all_lines: list[tuple[int, dict]] = []

    with open(args.input, "r") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            all_lines.append((i, obj))
            if obj.get("type") == "message":
                if obj.get("payload", {}).get("role") == "tool":
                    tool_result_indices.append(i)

    total_tool = len(tool_result_indices)
    keep_n = min(args.keep_tool_results, total_tool)
    keep_set = set(tool_result_indices[-keep_n:]) if keep_n > 0 else set()

    # ── second pass: render markdown ─────────────────────────────────
    session_id = extract_session_id(args.input)
    out: list[str] = []

    out.append(f"# Session Handoff: {session_id}\n\n")
    out.append(
        f"> Extracted from `{os.path.basename(args.input)}`\n"
    )
    out.append(
        f"> Tool results: {keep_n} preserved (last {keep_n}), "
        f"{total_tool - keep_n} replaced with placeholder\n\n"
    )
    out.append("---\n\n")

    placeholder_count = 0

    for _line_idx, obj in all_lines:
        t = obj.get("type")

        if t == "token_usage":
            continue

        if t == "session_meta":
            meta = obj.get("payload", {})
            out.append(
                f"**Session:** `{meta.get('id','?')}` | "
                f"**Model:** `{meta.get('model','?')}` | "
                f"**CWD:** `{meta.get('cwd','?')}`\n\n"
            )
            continue

        if t != "message":
            continue

        p = obj.get("payload", {})
        role = p.get("role", "?")
        content = p.get("content", "")

        # ── Assistant ────────────────────────────────────────────
        if role == "assistant":
            text = content.strip() if content else ""
            reasoning = p.get("reasoning_content", "").strip()
            tool_calls = p.get("tool_calls", [])

            if not (text or tool_calls or reasoning):
                continue

            out.append("### Assistant\n\n")

            if reasoning:
                out.append(f" Thinking:\n{reasoning}\n\n---\n\n")

            if text:
                out.append(f"{text}\n\n")

            if tool_calls:
                calls_str = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "?")
                    label = format_tool_call_args(fn.get("arguments", "{}"))
                    calls_str.append(f"`{name}` → {label}" if label else f"`{name}`")
                out.append(f"*Tool calls:* {', '.join(calls_str)}\n\n")

        # ── User ─────────────────────────────────────────────────
        elif role == "user":
            if content.strip():
                out.append("### 👤 User\n\n")
                out.append(f"{content.strip()}\n\n")

        # ── Tool result ──────────────────────────────────────────
        elif role == "tool":
            tool_name = p.get("tool_name", "?")
            if _line_idx in keep_set:
                out.append("#### Tool Result (preserved)\n\n")
                out.append(f"**Tool:** `{tool_name}`\n\n")
                c = content
                if len(c) > 5000:
                    c = c[:5000] + "\n\n[...truncated...]"
                out.append(f"```\n{c}\n```\n\n")
            else:
                placeholder_count += 1
                if placeholder_count <= 3:
                    out.append(
                        f"#### Tool Result (placeholder #{placeholder_count})\n\n"
                    )
                    out.append(f"**Tool:** `{tool_name}` — *result omitted for brevity*\n\n")
                elif placeholder_count == 4:
                    omitted = total_tool - keep_n - 3
                    out.append(
                        f"#### Tool Results "
                        f"(placeholders #{placeholder_count}–{total_tool - keep_n})\n\n"
                    )
                    out.append(f"*{omitted} more tool results omitted for brevity*\n\n")

    out.append("---\n\n")
    out.append(
        f"*Generated from session `{session_id}` — "
        f"{total_tool} tool results total, last {keep_n} preserved.*\n"
    )

    # ── write output ────────────────────────────────────────────────
    out_path = args.output or os.path.splitext(args.input)[0] + ".md"
    with open(out_path, "w") as f:
        f.write("".join(out))

    size_kb = len("".join(out)) / 1024
    print(f"Wrote {out_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
