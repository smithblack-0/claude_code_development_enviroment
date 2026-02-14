"""
End-to-end tests: Claude Code hooks fire and drive real RAG sync.

Requires: node, npx, mcp (mcptools), claude CLI on PATH, ANTHROPIC_API_KEY set.
Skipped automatically when these are absent -- see conftest.py.

These tests run a real Claude Code session (Haiku model) against a temp project
wired with our hooks. They verify that:
  - PostToolUse hook fires after a file edit and updates the index
  - SessionStart hook fires at session start and populates the index

The session prompt is minimal -- just enough to trigger a file write.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SYNC_TEMPLATE = (
    Path(__file__).parent.parent
    / "src/claude_code_bootstrap/rag_sync/templates/sync.py"
)
_MCP_SERVER_CMD = ["npx", "-y", "mcp-local-rag"]
_CLAUDE_MODEL = "claude-haiku-4-5-20251001"
# Shared model cache so mcp-local-rag only downloads embeddings once across runs.
_MODEL_CACHE_DIR = Path(__file__).parent.parent / ".test_cache" / "mcp_models"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path):
    """
    A wired project: sync.py in rag/, hooks in .claude/settings.json,
    and a target file for Claude to edit.
    """
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "example.py").write_text("# example\nx = 1\n", encoding="utf-8")
    (tmp_path / "test_target.txt").write_text("original content\n", encoding="utf-8")

    base_dir_str = str(tmp_path).replace("\\", "/")
    db_path_str = f"{base_dir_str}/rag/lancedb"

    config_lines = [
        f'base_dir = "{base_dir_str}"',
        'included_paths = ["src", "test_target.txt"]',
        'extensions = [".py", ".txt"]',
    ]
    (rag_dir / "config.toml").write_text("\n".join(config_lines), encoding="utf-8")

    shutil.copy(_SYNC_TEMPLATE, rag_dir / "sync.py")

    # Wire hooks
    sync_command = f'"{sys.executable}" rag/sync.py'
    settings = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [{"type": "command", "command": sync_command, "timeout": 60}],
                }
            ],
            "SessionStart": [
                {
                    "matcher": "startup",
                    "hooks": [{"type": "command", "command": sync_command, "timeout": 60}],
                }
            ],
        }
    }
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")

    return tmp_path, db_path_str


def _mcp_env(base_dir: str, db_path: str) -> dict:
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "BASE_DIR": base_dir,
        "DB_PATH": db_path,
        "CACHE_DIR": str(_MODEL_CACHE_DIR),
    }


def _list_files(base_dir: str, db_path: str) -> list[str]:
    result = subprocess.run(
        ["mcp", "call", "list_files", "--params", "{}"] + _MCP_SERVER_CMD,
        capture_output=True,
        env=_mcp_env(base_dir, db_path),
    )
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout.decode())
        text = " ".join(block.get("text", "") for block in data.get("content", []))
        return text.splitlines()
    except (json.JSONDecodeError, KeyError):
        return result.stdout.decode().splitlines()


def _run_claude(prompt: str, project_dir: Path, db_path: str) -> subprocess.CompletedProcess:
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"],
        "BASE_DIR": str(project_dir).replace("\\", "/"),
        "DB_PATH": db_path,
        "CACHE_DIR": str(_MODEL_CACHE_DIR),
    }
    return subprocess.run(
        ["claude", "--model", _CLAUDE_MODEL, "-p", prompt],
        cwd=str(project_dir),
        capture_output=True,
        env=env,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_post_tool_use_hook_fires_and_indexes_edited_file(project):
    """
    Claude edits test_target.txt → PostToolUse hook fires → sync.py runs
    → test_target.txt appears in the RAG index.
    """
    project_dir, db_path = project
    base_dir = str(project_dir).replace("\\", "/")

    result = _run_claude(
        "You are being used for automated integration testing. "
        "Edit the file test_target.txt so it contains exactly the text: hook test fired",
        project_dir,
        db_path,
    )
    assert result.returncode == 0, result.stderr.decode()

    # Verify the file was actually edited
    content = (project_dir / "test_target.txt").read_text(encoding="utf-8")
    assert "hook test fired" in content

    # Verify the hook fired and the file is in the index
    files = _list_files(base_dir, db_path)
    assert any("test_target" in f for f in files), (
        f"test_target.txt not found in index. Indexed files: {files}"
    )


@pytest.mark.e2e
def test_session_start_hook_fires_and_populates_index(project):
    """
    Starting a Claude session triggers SessionStart hook → sync.py runs
    → pre-existing files appear in the RAG index even without edits.
    """
    project_dir, db_path = project
    base_dir = str(project_dir).replace("\\", "/")

    # Confirm index is empty before the session
    files_before = _list_files(base_dir, db_path)
    assert not any("example.py" in f for f in files_before)

    # Start a session -- SessionStart hook should fire immediately
    result = _run_claude(
        "You are being used for automated integration testing. "
        "Reply with only the word: ready",
        project_dir,
        db_path,
    )
    assert result.returncode == 0, result.stderr.decode()

    # Verify the session start hook populated the index
    files_after = _list_files(base_dir, db_path)
    assert any("example.py" in f for f in files_after), (
        f"example.py not found in index after session start. Indexed files: {files_after}"
    )
