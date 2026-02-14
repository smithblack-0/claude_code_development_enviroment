"""
Integration tests for the sync engine against a real mcp-local-rag instance.

Requires: node, npx, mcp (mcptools) on PATH.
Skipped automatically when these are absent -- see conftest.py.

These tests exercise the full mcp call round-trip: ingest → query → delete.
"""

import json
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
# Shared model cache so mcp-local-rag only downloads embeddings once across runs.
_MODEL_CACHE_DIR = Path(__file__).parent.parent / ".test_cache" / "mcp_models"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path):
    """
    A real project layout with config.toml and sync.py in place.
    DB is isolated to this temp dir so tests don't share state.
    """
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()
    db_dir = rag_dir / "lancedb"

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "hello.py").write_text("# hello\ndef greet():\n    return 'hello'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Integration Test Project\n\nThis is a test.", encoding="utf-8")

    base_dir_str = str(tmp_path).replace("\\", "/")
    config_lines = [
        f'base_dir = "{base_dir_str}"',
        'included_paths = ["src", "README.md"]',
        'extensions = [".py", ".md"]',
    ]
    (rag_dir / "config.toml").write_text("\n".join(config_lines), encoding="utf-8")

    shutil.copy(_SYNC_TEMPLATE, rag_dir / "sync.py")

    return tmp_path


def _mcp_env(project: Path) -> dict:
    """Env vars pointing mcp-local-rag at this project's isolated database."""
    import os
    base = str(project).replace("\\", "/")
    db = str(project / "rag" / "lancedb").replace("\\", "/")
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "BASE_DIR": base,
        "DB_PATH": db,
        "CACHE_DIR": str(_MODEL_CACHE_DIR),
    }


def _mcp_call(tool: str, params: dict, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["mcp", "call", tool, "--params", json.dumps(params)] + _MCP_SERVER_CMD,
        capture_output=True,
        env=_mcp_env(project),
    )


def _list_files(project: Path) -> list[str]:
    """Return list of file paths currently in the index."""
    result = _mcp_call("list_files", {}, project)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout.decode())
        # mcp-local-rag returns content as a list of text blocks
        text = " ".join(
            block.get("text", "") for block in data.get("content", [])
        )
        return text.splitlines()
    except (json.JSONDecodeError, KeyError):
        return result.stdout.decode().splitlines()


def _run_sync(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(project / "rag" / "sync.py")],
        capture_output=True,
        cwd=str(project),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_sync_ingests_files(project):
    """Running sync.py indexes files into mcp-local-rag."""
    result = _run_sync(project)
    assert result.returncode == 0, result.stderr.decode()

    files = _list_files(project)
    assert any("hello.py" in f for f in files)
    assert any("README.md" in f for f in files)


@pytest.mark.integration
def test_sync_query_returns_results(project):
    """After ingestion, query_documents finds relevant content."""
    _run_sync(project)

    result = _mcp_call("query_documents", {"query": "greet hello"}, project)
    assert result.returncode == 0, result.stderr.decode()

    output = result.stdout.decode()
    assert "hello" in output.lower()


@pytest.mark.integration
def test_sync_removes_deleted_file(project):
    """After a file is deleted, re-running sync removes it from the index."""
    _run_sync(project)

    (project / "README.md").unlink()
    result = _run_sync(project)
    assert result.returncode == 0, result.stderr.decode()

    files = _list_files(project)
    assert not any("README.md" in f for f in files)


@pytest.mark.integration
def test_sync_no_op_on_unchanged_files(project):
    """Second sync with nothing changed exits 0 with no output."""
    _run_sync(project)

    result = _run_sync(project)
    assert result.returncode == 0
    assert result.stdout.decode().strip() == ""


@pytest.mark.integration
def test_sync_reingest_on_change(project):
    """Modified file is re-ingested on next sync."""
    _run_sync(project)

    (project / "README.md").write_text("# Changed\n\nCompletely different content.", encoding="utf-8")
    _run_sync(project)

    result = _mcp_call("query_documents", {"query": "completely different"}, project)
    assert result.returncode == 0, result.stderr.decode()
    assert "different" in result.stdout.decode().lower()


@pytest.mark.integration
def test_sync_and_query_share_same_database(project):
    """Proves sync writes to the same DB that queries read from."""
    unique_token = "xq7z_unique_integration_token_xq7z"
    (project / "src" / "unique.py").write_text(
        f"# {unique_token}", encoding="utf-8"
    )

    _run_sync(project)

    result = _mcp_call("query_documents", {"query": unique_token}, project)
    assert result.returncode == 0, result.stderr.decode()
    assert unique_token in result.stdout.decode()
