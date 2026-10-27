#!/usr/bin/env bash
# Install the eyeproof skill for the agents found on this machine.
#   Claude Code:  ~/.claude/skills/eyeproof  -> symlink to skills/eyeproof (updates with the repo)
#   Hermes Agent: ~/.hermes/skills/software-development/eyeproof  -> copy (Hermes rejects symlinks leaving its
#                 skill folder; run this again after updating the repo)
set -e
here="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$HOME/.claude" ]; then
  mkdir -p "$HOME/.claude/skills"
  ln -sfn "$here/eyeproof" "$HOME/.claude/skills/eyeproof"
  echo "Claude Code: ~/.claude/skills/eyeproof -> $here/eyeproof"
fi
if [ -d "$HOME/.hermes" ]; then
  dst="$HOME/.hermes/skills/software-development/eyeproof"
  mkdir -p "$dst" && cp "$here/eyeproof-hermes/SKILL.md" "$dst/SKILL.md"
  echo "Hermes Agent: copied to $dst"
fi
[ -f "$HOME/.config/eyeproof/LOCAL.md" ] && echo "local rules: ~/.config/eyeproof/LOCAL.md (read by the skill)" || true
