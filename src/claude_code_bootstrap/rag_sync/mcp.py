"""
MCP server registration for rag-sync.

Registers mcp-local-rag with Claude Code at project scope so the
query_documents, list_files, and status tools are available in sessions.

Registration command:
    claude mcp add local-rag --scope project
        --env BASE_DIR=<project_root>
        --env DB_PATH=<project_root>/rag/lancedb
        -- npx -y mcp-local-rag

Writes: .mcp.json at project root (managed by Claude Code CLI).
Idempotent: re-running replaces the existing registration.
"""

import subprocess
import sys
from pathlib import Path

_SERVER_NAME = "local-rag"
_SCOPE = "project"
_DB_SUBPATH = "rag/lancedb"
_MCP_SERVER_CMD = ["npx", "-y", "mcp-local-rag"]


def register_mcp_server(project_root: Path) -> None:
    """Register mcp-local-rag with Claude Code at project scope.

    Removes any existing registration first so re-runs always reflect
    the current project root and DB path.
    """
    # Remove existing registration (ignore errors if not present)
    subprocess.run(
        ["claude", "mcp", "remove", _SERVER_NAME, "--scope", _SCOPE],
        capture_output=True,
    )

    base_dir = str(project_root).replace("\\", "/")
    db_path = f"{base_dir}/{_DB_SUBPATH}"

    result = subprocess.run(
        [
            "claude",
            "mcp",
            "add",
            _SERVER_NAME,
            "--scope",
            _SCOPE,
            "--env",
            f"BASE_DIR={base_dir}",
            "--env",
            f"DB_PATH={db_path}",
            "--",
            *_MCP_SERVER_CMD,
        ],
        capture_output=True,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        print(f"\nWarning: MCP server registration failed:\n{stderr}", file=sys.stderr)
    else:
        print("\nRegistered MCP server 'local-rag'.")
