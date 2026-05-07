# gdrive-mcp

Google Drive MCP Server — Full CRUD extension for Claude integration.

## Tools

| Tool | Description |
|------|-------------|
| `rename_file` | Rename any file or folder |
| `move_file` | Move file between folders (auto-detects current parent) |
| `trash_file` | Soft delete (recoverable) |
| `untrash_file` | Restore from trash |
| `delete_file` | Permanent delete (requires `GDRIVE_ALLOW_DESTRUCTIVE=true`) |
| `create_folder` | Create new folder |
| `list_folder` | List folder contents |
| `batch_trash` | Trash up to 100 files in one call |
| `batch_move` | Move up to 100 files in one call |
| `empty_trash` | Empty entire trash (requires `GDRIVE_ALLOW_DESTRUCTIVE=true`) |

## Setup

1. Create Google Cloud project with Drive API enabled
2. Create OAuth2 credentials (Desktop app type)
3. Run initial auth flow to get refresh token
4. Deploy to Railway with env vars:

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
GDRIVE_ALLOW_DESTRUCTIVE=false
```

## Auth Flow (one-time)

```bash
pip install google-auth-oauthlib
python auth_flow.py  # generates token.json with refresh_token
```

## Deploy

```bash
railway up
```

## Safety

- `delete_file` and `empty_trash` are gated behind `GDRIVE_ALLOW_DESTRUCTIVE` env var
- Default is `false` — flip to `true` only during cleanup windows, then flip back
- `batch_trash` is recoverable (files go to trash, not permanently deleted)
