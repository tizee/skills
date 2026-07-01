#!/usr/bin/env python3
"""Lint Agent Skill SKILL.md files.

Validates one skill, one SKILL.md, or scans a directory of skills.

Two severities are reported:

- ERROR: the skill would FAIL to load in Zhu (the Rust agent). Its loader
  (crates/skills/src/loader.rs) silently drops such skills with only a
  tracing::warn!, so these are the failures that make a skill "vanish".
- WARN:  the skill still loads in Zhu, but is risky or non-portable (e.g.
  exceeds the agentskills.io spec limits that stricter tools enforce, or
  Zhu will truncate the description).

Exit code is 0 only when no ERROR was found (WARNs do not fail the run).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "error: PyYAML is required. Install it with `pip install pyyaml` "
        "or run this script via `uv run --with pyyaml`.\n"
    )
    raise SystemExit(2)

# --- Limits ---------------------------------------------------------------
# Kept in sync with crates/skills/src/loader.rs and the agentskills.io spec.
NAME_MAX = 64
DESC_SPEC_MAX = 1024  # agentskills.io hard cap; stricter tools reject above.
DESC_ZHU_TRUNCATE = 1224  # Zhu truncates (still loads) above this.

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# Frontmatter keys Zhu's loader understands. Unknown keys are ignored by Zhu
# (not fatal), so they are reported only as INFO-level WARNs for hygiene.
ZHU_KNOWN_KEYS = {
    "name",
    "description",
    "argument-hint",
    "context",
    "agent",
    "model",
    "approval-policy",
    "disable-model-invocation",
    "user-invocable",
    "fork-context",
    "metadata",
    # widely-used spec keys Zhu tolerates
    "license",
    "allowed-tools",
    "compatibility",
}


class Report:
    def __init__(self, skill_id: str):
        self.skill_id = skill_id
        self.errors: list[str] = []
        self.warns: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


def _first_paragraph(body: str) -> str:
    """Zhu's fallback description when frontmatter has none: first paragraph."""
    for block in body.strip().split("\n\n"):
        text = block.strip()
        if text and not text.startswith("#"):
            return " ".join(text.split())
    return ""


def validate_skill_md(skill_md: Path) -> Report:
    rep = Report(skill_md.parent.name)

    raw = skill_md.read_text(encoding="utf-8")

    frontmatter: dict = {}
    body = raw
    has_frontmatter = raw.startswith("---")

    if has_frontmatter:
        m = FRONTMATTER_RE.match(raw)
        if not m:
            rep.error(
                "frontmatter opens with '---' but has no closing '---' delimiter"
            )
            return rep
        fm_text = m.group(1)
        body = raw[m.end():]
        try:
            parsed = yaml.safe_load(fm_text)
        except yaml.YAMLError as e:
            # This is the exact class of failure that silently drops a skill
            # in Zhu (e.g. an unquoted description containing a colon-space
            # like "house format: prose" parsed as a nested mapping).
            detail = str(e).replace("\n", "\n    ")
            rep.error(f"invalid YAML in frontmatter: {detail}")
            return rep
        if parsed is None:
            frontmatter = {}
        elif isinstance(parsed, dict):
            frontmatter = parsed
        else:
            rep.error(
                f"frontmatter must be a YAML mapping, got {type(parsed).__name__}"
            )
            return rep
    else:
        rep.warn(
            "no YAML frontmatter; name falls back to directory name and "
            "description to the first body paragraph"
        )

    # --- name ---
    name = frontmatter.get("name")
    if name is None:
        name = skill_md.parent.name  # Zhu's default_name fallback
    elif not isinstance(name, str):
        rep.error(f"'name' must be a string, got {type(name).__name__}")
        name = ""
    name = name.strip()
    if not name:
        rep.error("effective name is empty")
    elif len(name) > NAME_MAX:
        rep.error(f"name is {len(name)} chars; max is {NAME_MAX}")
    elif "--" in name:
        rep.error(f"name '{name}' contains consecutive hyphens")
    elif not NAME_RE.match(name):
        rep.error(
            f"name '{name}' must be lowercase alphanumeric + hyphens, "
            "no leading/trailing hyphen"
        )

    # --- description ---
    desc = frontmatter.get("description")
    from_fallback = False
    if desc is None:
        desc = _first_paragraph(body)
        from_fallback = True
    elif not isinstance(desc, str):
        rep.error(f"'description' must be a string, got {type(desc).__name__}")
        desc = ""
    desc = desc.strip()

    if not desc:
        rep.error(
            "description is empty"
            + (" (no frontmatter description and no body paragraph)"
               if from_fallback else "")
        )
    else:
        n = len(desc)
        if n > DESC_ZHU_TRUNCATE:
            rep.warn(
                f"description is {n} chars; Zhu will truncate it to "
                f"{DESC_ZHU_TRUNCATE} (still loads, but tail is lost)"
            )
        elif n > DESC_SPEC_MAX:
            rep.warn(
                f"description is {n} chars; exceeds the agentskills.io spec "
                f"limit of {DESC_SPEC_MAX} (stricter tools may reject it)"
            )
        if "<" in desc or ">" in desc:
            rep.warn(
                "description contains angle brackets; Zhu escapes them, but "
                "the agentskills.io spec forbids them (non-portable)"
            )

    # --- unknown keys (hygiene only) ---
    if isinstance(frontmatter, dict):
        unknown = sorted(set(frontmatter) - ZHU_KNOWN_KEYS)
        if unknown:
            rep.warn(
                "unknown frontmatter key(s) ignored by Zhu: "
                + ", ".join(unknown)
            )

    return rep


def _find_skill_mds(target: Path) -> list[Path]:
    if target.is_file() and target.name == "SKILL.md":
        return [target]
    if (target / "SKILL.md").is_file():
        return [target / "SKILL.md"]
    # directory scan: <dir>/<skill-name>/SKILL.md
    found = sorted(target.glob("*/SKILL.md"))
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(
            "usage: validate.py <skill-dir | SKILL.md | skills-root-dir>\n"
        )
        return 2

    target = Path(argv[1]).expanduser()
    if not target.exists():
        sys.stderr.write(f"error: path does not exist: {target}\n")
        return 2

    skill_mds = _find_skill_mds(target)
    if not skill_mds:
        sys.stderr.write(f"error: no SKILL.md found under {target}\n")
        return 2

    total_errors = 0
    total_warns = 0
    failed = 0

    for skill_md in skill_mds:
        rep = validate_skill_md(skill_md)
        total_errors += len(rep.errors)
        total_warns += len(rep.warns)
        if not rep.ok:
            failed += 1

        if rep.ok and not rep.warns:
            print(f"OK    {rep.skill_id}")
            continue

        status = "FAIL" if rep.errors else "WARN"
        print(f"{status}  {rep.skill_id}")
        for e in rep.errors:
            print(f"        ERROR: {e}")
        for w in rep.warns:
            print(f"        WARN:  {w}")

    print(
        f"\n{len(skill_mds)} skill(s): {failed} failed, "
        f"{total_errors} error(s), {total_warns} warning(s)"
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
