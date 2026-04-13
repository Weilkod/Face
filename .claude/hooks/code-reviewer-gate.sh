#!/usr/bin/env bash
# Stop hook: block the turn once if code files changed but code-reviewer
# hasn't reviewed them yet. Loop prevention via hash-of-contents marker.
# CLAUDE.md §7 done criteria — automated instead of a text instruction.

set -u

FILES=$( {
  git diff --name-only HEAD 2>/dev/null | grep -E '\.(py|ts|tsx|js|jsx)$' || true
  git ls-files --others --exclude-standard 2>/dev/null | grep -E '\.(py|ts|tsx|js|jsx)$' || true
} | sort -u )

if [ -z "$FILES" ]; then
  exit 0
fi

HASH=$(echo "$FILES" | while IFS= read -r f; do sha256sum "$f" 2>/dev/null; done | sha256sum | cut -c1-16)

MARKER=".claude/.last-reviewed-hash"
LAST=$(cat "$MARKER" 2>/dev/null || true)

if [ "$HASH" = "$LAST" ]; then
  exit 0
fi

printf '%s' "$HASH" > "$MARKER"

cat <<'JSON'
{"decision":"block","reason":"CLAUDE.md §7 done gate: code files were changed this turn but the code-reviewer subagent has not reviewed them. Invoke the code-reviewer subagent now against the current git diff + untracked code files, report its findings, then stop."}
JSON
