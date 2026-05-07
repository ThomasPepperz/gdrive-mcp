"""
Google Drive MCP Server — CRUD Extension
Extends existing read-only connector with write operations.
Stack: FastMCP + google-api-python-client + Railway

Env vars required:
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
  GDRIVE_ALLOW_DESTRUCTIVE=false (set true for permanent deletes)
"""

import os
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Config ──────────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/drive"]
ALLOW_DESTRUCTIVE = os.environ.get("GDRIVE_ALLOW_DESTRUCTIVE", "false").lower() == "true"

mcp = FastMCP(
    "Google Drive MCP",
    description="Full CRUD operations for Google Drive — rename, move, trash, delete, folder management",
)

# ── Auth ────────────────────────────────────────────────────────────────────

def get_drive_service():
    """Build authenticated Drive v3 service from env var credentials."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


# ── Helper ──────────────────────────────────────────────────────────────────

def file_summary(f: dict) -> dict:
    """Extract key fields from a Drive file resource."""
    return {
        "id": f.get("id"),
        "name": f.get("name"),
        "mimeType": f.get("mimeType"),
        "parents": f.get("parents"),
        "trashed": f.get("trashed"),
        "webViewLink": f.get("webViewLink"),
        "modifiedTime": f.get("modifiedTime"),
    }


STANDARD_FIELDS = "id,name,mimeType,parents,trashed,webViewLink,modifiedTime"


# ── Tools ───────────────────────────────────────────────────────────────────

@mcp.tool()
def rename_file(file_id: str, new_name: str) -> dict:
    """Rename a file or folder in Google Drive."""
    service = get_drive_service()
    result = service.files().update(
        fileId=file_id,
        body={"name": new_name},
        fields=STANDARD_FIELDS,
        supportsAllDrives=True,
    ).execute()
    return {"file": file_summary(result)}


@mcp.tool()
def move_file(file_id: str, new_parent_id: str, old_parent_id: Optional[str] = None) -> dict:
    """Move a file to a different folder. If old_parent_id not provided, auto-detects current parent."""
    service = get_drive_service()

    if not old_parent_id:
        current = service.files().get(
            fileId=file_id, fields="parents", supportsAllDrives=True
        ).execute()
        parents = current.get("parents", [])
        old_parent_id = parents[0] if parents else None

    kwargs = {"fileId": file_id, "addParents": new_parent_id, "fields": STANDARD_FIELDS, "supportsAllDrives": True}
    if old_parent_id:
        kwargs["removeParents"] = old_parent_id

    result = service.files().update(**kwargs).execute()
    return {"file": file_summary(result)}


@mcp.tool()
def trash_file(file_id: str) -> dict:
    """Move a file to trash (recoverable). Use untrash_file to restore."""
    service = get_drive_service()
    result = service.files().update(
        fileId=file_id,
        body={"trashed": True},
        fields=STANDARD_FIELDS,
        supportsAllDrives=True,
    ).execute()
    return {"file": file_summary(result), "status": "trashed"}


@mcp.tool()
def untrash_file(file_id: str) -> dict:
    """Restore a file from trash."""
    service = get_drive_service()
    result = service.files().update(
        fileId=file_id,
        body={"trashed": False},
        fields=STANDARD_FIELDS,
        supportsAllDrives=True,
    ).execute()
    return {"file": file_summary(result), "status": "restored"}


@mcp.tool()
def delete_file(file_id: str) -> dict:
    """Permanently delete a file. IRREVERSIBLE. Requires GDRIVE_ALLOW_DESTRUCTIVE=true."""
    if not ALLOW_DESTRUCTIVE:
        return {
            "error": "delete_file blocked. Set GDRIVE_ALLOW_DESTRUCTIVE=true to enable.",
            "hint": "Use trash_file instead for recoverable deletion.",
        }
    service = get_drive_service()
    service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
    return {"status": "permanently_deleted", "file_id": file_id}


@mcp.tool()
def create_folder(name: str, parent_id: Optional[str] = None) -> dict:
    """Create a new folder in Google Drive."""
    service = get_drive_service()
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    result = service.files().create(
        body=body, fields=STANDARD_FIELDS, supportsAllDrives=True
    ).execute()
    return {"folder": file_summary(result)}


@mcp.tool()
def list_folder(folder_id: str, page_size: int = 100, include_trashed: bool = False) -> dict:
    """List contents of a folder."""
    service = get_drive_service()
    q = f"'{folder_id}' in parents"
    if not include_trashed:
        q += " and trashed=false"

    results = []
    page_token = None

    while True:
        response = service.files().list(
            q=q,
            fields=f"nextPageToken,files({STANDARD_FIELDS},size)",
            pageSize=min(page_size, 1000),
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        for f in response.get("files", []):
            results.append(file_summary(f) | {"size": f.get("size")})

        page_token = response.get("nextPageToken")
        if not page_token or len(results) >= page_size:
            break

    return {"files": results, "count": len(results), "folder_id": folder_id}


@mcp.tool()
def batch_trash(file_ids: list[str]) -> dict:
    """Trash multiple files in a single batch request (up to 100)."""
    if len(file_ids) > 100:
        return {"error": "Maximum 100 files per batch. Split into multiple calls."}

    service = get_drive_service()
    batch = service.new_batch_http_request()
    results = {"trashed": [], "errors": []}

    def callback(request_id, response, exception):
        fid = file_ids[int(request_id)]
        if exception:
            results["errors"].append({"file_id": fid, "error": str(exception)})
        else:
            results["trashed"].append(fid)

    for i, fid in enumerate(file_ids):
        batch.add(
            service.files().update(fileId=fid, body={"trashed": True}, supportsAllDrives=True),
            request_id=str(i),
            callback=callback,
        )

    batch.execute()
    return results


@mcp.tool()
def batch_move(file_ids: list[str], new_parent_id: str) -> dict:
    """Move multiple files to a new folder in a single batch (up to 100)."""
    if len(file_ids) > 100:
        return {"error": "Maximum 100 files per batch. Split into multiple calls."}

    service = get_drive_service()

    # Get current parents for all files first
    parents_map = {}
    for fid in file_ids:
        current = service.files().get(fileId=fid, fields="parents", supportsAllDrives=True).execute()
        parents_map[fid] = current.get("parents", [None])[0]

    batch = service.new_batch_http_request()
    results = {"moved": [], "errors": []}

    def callback(request_id, response, exception):
        fid = file_ids[int(request_id)]
        if exception:
            results["errors"].append({"file_id": fid, "error": str(exception)})
        else:
            results["moved"].append(fid)

    for i, fid in enumerate(file_ids):
        kwargs = {"fileId": fid, "addParents": new_parent_id, "supportsAllDrives": True}
        if parents_map.get(fid):
            kwargs["removeParents"] = parents_map[fid]
        batch.add(service.files().update(**kwargs), request_id=str(i), callback=callback)

    batch.execute()
    return results


@mcp.tool()
def empty_trash() -> dict:
    """Permanently empty the entire Drive trash. IRREVERSIBLE. Requires GDRIVE_ALLOW_DESTRUCTIVE=true."""
    if not ALLOW_DESTRUCTIVE:
        return {"error": "empty_trash blocked. Set GDRIVE_ALLOW_DESTRUCTIVE=true to enable."}
    service = get_drive_service()
    service.files().emptyTrash().execute()
    return {"status": "trash_emptied"}


# ── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
