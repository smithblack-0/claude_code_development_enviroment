"""Thin orchestrator for the rag-sync install flow."""

import os
import sys
from pathlib import Path

from claude_code_bootstrap.dependencies import check_dependencies
from claude_code_bootstrap.rag_sync.claude_md import write_claude_md
from claude_code_bootstrap.rag_sync.config import write_config, write_usage_guide
from claude_code_bootstrap.rag_sync.hooks import wire_hooks
from claude_code_bootstrap.rag_sync.mcp import register_mcp_server
from claude_code_bootstrap.rag_sync.prompts import (
    confirm_config,
    get_extensions,
    walk_directory,
)
from claude_code_bootstrap.rag_sync.setup_sync import run_initial_sync

# ---------------------------------------------------------------------------
# RAG-specific dependency requirements
# ---------------------------------------------------------------------------

RAG_REQUIRED_TOOLS = {
    "node": "https://nodejs.org/",
    "npx": "https://nodejs.org/  (comes with Node)",
    "mcp": "https://github.com/f/mcptools  (go install github.com/f/mcptools/cmd/mcp@latest)",
    "claude": "https://claude.ai/code  (install Claude Code CLI)",
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_install() -> None:
    """Run the full rag-sync install sequence."""
    project_root = Path(os.getcwd()).resolve()

    print("=== claude-code-bootstrap: rag-sync install ===")

    check_dependencies(RAG_REQUIRED_TOOLS)

    included_paths = walk_directory(project_root)
    extensions = get_extensions()

    config = {
        "included_paths": included_paths,
        "extensions": extensions,
        "base_dir": str(project_root),
    }

    if not confirm_config(config):
        print("Aborted.")
        sys.exit(0)

    rag_dir = project_root / "rag"
    write_config(rag_dir, config)
    write_usage_guide(rag_dir, config)

    python_cmd = sys.executable

    run_initial_sync(project_root)
    register_mcp_server(project_root)
    wire_hooks(project_root, python_cmd)
    write_claude_md(project_root, config)

    print(f"\nDone. Run '{python_cmd} rag/sync.py' at any time to manually sync the index.")
