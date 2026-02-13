"""MCP server registration — Stage 4 stub."""

from pathlib import Path


def register_mcp_server(project_root: Path) -> None:
    """
    STUB (Stage 4): Register mcp-local-rag with Claude Code.

    Will invoke:
        claude mcp add local-rag --scope project
            --env BASE_DIR=<project_root>
            --env DB_PATH=<project_root>/rag/lancedb
            -- npx -y mcp-local-rag
    """
    print(
        "\n[stub] register_mcp_server — will run 'claude mcp add local-rag' (Stage 4)"
    )
