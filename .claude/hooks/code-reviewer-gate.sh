#!/usr/bin/env bash
# Stop hook: block the turn once if code files changed but code-reviewer
# hasn't reviewed them yet. Loop prevention via hash-of-contents marker.
# CLAUDE.md §7 done criteria — automated instead of a text instruction.
#
# H1 (session 10): also diff against origin/main so post-commit stops
# still detect committed-but-unreviewed changes. Previously the hook only
# looked at `git diff HEAD` which is empty immediately after `git commit`,
# causing a silent pass on every commit (session 5/6 incident — see
# PROGRESS.md §"Stop hook 보강"). The fix UNIONs three sources:
#   1. uncommitted working-tree diff (`git diff HEAD`)
#   2. untracked source files
#   3. branch diff vs origin/main (`git diff origin/main...HEAD`)
# with graceful fallbacks if origin/main is unreachable.

set -u

FILTER='\.(py|ts|tsx|js|jsx)$'

# Source 3: branch-level diff vs origin/main (H1).
# Fallback chain: origin/main → HEAD~1..HEAD → empty (sources 1+2 still cover).
branch_diff() {
  if git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
    git diff --name-only origin/main...HEAD 2>/dev/null
    return
  fi
  if git rev-parse --verify --quiet HEAD~1 >/dev/null 2>&1; then
    git diff --name-only HEAD~1 HEAD 2>/dev/null
    return
  fi
  # No upstream and no parent commit (fresh repo): nothing to add.
  return
}

FILES=$( {
  git diff --name-only HEAD 2>/dev/null | grep -E "$FILTER" || true
  git ls-files --others --exclude-standard 2>/dev/null | grep -E "$FILTER" || true
  branch_diff | grep -E "$FILTER" || true
} | sort -u )

if [ -z "$FILES" ]; then
  exit 0
fi

# Hash file contents for files that still exist on disk; for files that
# only exist in a past commit (deleted on branch), fall back to hashing
# the path itself so the marker still changes. This keeps loop-prevention
# stable across post-commit stops.
HASH=$(echo "$FILES" | while IFS= read -r f; do
  if [ -f "$f" ]; then
    sha256sum "$f" 2>/dev/null
  else
    printf '%s\n' "deleted:$f"
  fi
done | sha256sum | cut -c1-16)

# Include the short HEAD hash in the marker so a future session doing
# post-hoc review can pin down exactly which commits were pending.
SHORT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "nohead")
MARKER_VALUE="$HASH@$SHORT_SHA"

MARKER=".claude/.last-reviewed-hash"
LAST=$(cat "$MARKER" 2>/dev/null || true)

if [ "$MARKER_VALUE" = "$LAST" ]; then
  exit 0
fi

printf '%s' "$MARKER_VALUE" > "$MARKER"

cat <<JSON
{"decision":"block","reason":"CLAUDE.md §7 done gate: code files were changed this turn (HEAD=$SHORT_SHA, including branch diff vs origin/main) but the code-reviewer subagent has not reviewed them. Invoke the code-reviewer subagent now against the current branch diff + uncommitted + untracked code files, report its findings, then stop."}
JSON
