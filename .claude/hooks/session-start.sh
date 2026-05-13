#!/bin/bash
# SessionStart hook for gdrive-mcp
# Mirrored from ThomasPepperz/utilities pattern (PR #48).

set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  echo '{}'
  exit 0
fi

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$REPO_DIR"
CONTEXT_FILE="$(mktemp)"

{
  echo "## Trust tier reminder (per utilities/CLAUDE.md)"
  echo ""
  echo "Default tier: **GREEN**. Always-pause: force-push, unmerged branch delete, prod env changes, external sends."
  echo "Destructive gdrive ops gated by GDRIVE_ALLOW_DESTRUCTIVE=true."
  echo ""

  echo "## CLAUDE.md"
  echo ""
  if [ -f "CLAUDE.md" ]; then
    head -50 CLAUDE.md
  fi
  echo ""

  echo "## Dependency install"
  echo ""
  if [ -f "requirements.txt" ]; then
    pip install --quiet -r requirements.txt 2>&1 | tail -3 || echo "  (pip install failed)"
  fi
  echo ""

  echo "## Open PRs"
  echo ""
  if command -v gh >/dev/null 2>&1 && [ -n "${GH_TOKEN:-}${GITHUB_TOKEN:-}" ]; then
    gh pr list --state open --limit 10 --json number,title,isDraft \
      --jq '.[] | "- #\(.number) [\(if .isDraft then "draft" else "ready" end)] \(.title)"' \
      2>/dev/null || true
  fi
  echo ""
} >> "$CONTEXT_FILE"

python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = f.read()
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': ctx,
    }
}))
"

rm -f "$CONTEXT_FILE"
