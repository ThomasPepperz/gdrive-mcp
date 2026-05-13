# CLAUDE.md — gdrive-mcp

User-global rules live in **`ThomasPepperz/utilities/CLAUDE.md`** (mirrored
from `~/.claude/CLAUDE.md` on the workstation). That file is the single
source of truth for cross-repo conventions:

- Pushing files via the GitHub MCP — size discipline
- Workflow-cascade pattern + anti-recursion gotcha
- Decision-tracking convention
- Trust tier system
- GitHub ↔ Teamwork linking
- Task lifecycle & successor-task discipline
- Recommendation-tracking discipline + capture-first refinement
- PM discipline & critical-path analysis
- Workflow & tooling gotchas

## gdrive-mcp-specific notes

- This repo is a **FastMCP server** for Google Drive CRUD (rename, move, trash, batch ops, folder create).
- **Deployment**: Railway via `railway up` CLI. No `railway.toml`; service configured in Railway dashboard.
- **Auth**: Google OAuth2. Env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GDRIVE_ALLOW_DESTRUCTIVE`.
- Destructive ops (`delete_file`, `empty_trash`) gated by `GDRIVE_ALLOW_DESTRUCTIVE=true`.
- **Refactor candidate**: single-commit scaffold from 2026-05-07; untouched since. Confirm production status before significant changes. Tracked as tw#39854906.
- Transferred from `DataDisciples/gdrive-mcp` on 2026-05-13 (see `utilities/docs/decisions/2026-05-13-datadisciples-migration-COMPLETED.md`).

> **CI mirror:** this file is read by `claude-code-action` running in GitHub Actions on this repo. The agent's session also loads `utilities/CLAUDE.md` for the canonical global rules.
