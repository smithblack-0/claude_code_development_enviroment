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

_DB_SUBPATH = "rag/lancedb"


def register_mcp_server(project_root: Path) -> None:
    """Register mcp-local-rag with Claude Code at project scope."""
    base_dir = str(project_root).replace("\\", "/")
    db_path = f"{base_dir}/{_DB_SUBPATH}"

    result = subprocess.run(
        [
            "claude",
            "mcp",
            "add",
            "local-rag",
            "--scope",
            "project",
            "--env",
            f"BASE_DIR={base_dir}",
            "--env",
            f"DB_PATH={db_path}",
            "--",
            "npx",
            "-y",
            "mcp-local-rag",
        ],
        capture_output=True,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        print(f"\nWarning: MCP server registration failed:\n{stderr}", file=sys.stderr)
    else:
        print("\nRegistered MCP server 'local-rag'.")
