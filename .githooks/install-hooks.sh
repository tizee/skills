#!/usr/bin/env bash
#
# Install this repo's git hooks.
#
# Git does not merge core.hooksPath, so pointing this repo at a local .githooks
# would normally disable all global hooks. To avoid that, this script creates a
# forwarding stub (symlink -> _forward) for every hook present in the global
# hooksPath, plus pre-commit (which also runs skill-lint). Then it sets the
# repo-local core.hooksPath.
#
# Re-run this after adding a new global hook so it gets a forwarding stub here.
#
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hooks_dir="$repo_root/.githooks"

[ -f "$hooks_dir/_forward" ] || { echo "error: $hooks_dir/_forward missing" >&2; exit 1; }
chmod +x "$hooks_dir/_forward"

global_hooks="$(git config --global core.hooksPath || true)"
global_hooks="${global_hooks/#\~/$HOME}"

# pre-commit is always installed (carries skill-lint even without a global one).
names="pre-commit"
if [ -n "${global_hooks:-}" ] && [ -d "$global_hooks" ]; then
  for f in "$global_hooks"/*; do
    [ -f "$f" ] || continue
    names="$names $(basename "$f")"
  done
fi

# One relative symlink per hook name -> _forward.
for name in $(printf '%s\n' $names | sort -u); do
  ln -sf _forward "$hooks_dir/$name"
done

git config --local core.hooksPath .githooks

echo "Installed forwarding hooks in .githooks and set core.hooksPath=.githooks"
echo "Hooks: $(printf '%s\n' $names | sort -u | tr '\n' ' ')"
if [ -n "${global_hooks:-}" ]; then
  echo "Forwarding to global hooksPath: $global_hooks"
fi
