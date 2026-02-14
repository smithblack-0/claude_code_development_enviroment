"""Tests for Stage 4 wiring: mcp.py, hooks.py, claude_md.py."""

import json
from unittest.mock import MagicMock, patch

import pytest

from claude_code_bootstrap.rag_sync.claude_md import (
    _strip_managed_section,
    write_claude_md,
)
from claude_code_bootstrap.rag_sync.hooks import _is_managed, wire_hooks
from claude_code_bootstrap.rag_sync.mcp import register_mcp_server


@pytest.fixture()
def config():
    return {
        "included_paths": ["src", "README.md"],
        "extensions": [".py", ".md"],
        "base_dir": "/tmp/project",
    }


# ---------------------------------------------------------------------------
# mcp.py
# ---------------------------------------------------------------------------


def test_register_mcp_server_success(tmp_path, capsys):
    ok = MagicMock()
    ok.returncode = 0

    with patch("subprocess.run", return_value=ok) as mock_run:
        register_mcp_server(tmp_path)

    args = mock_run.call_args[0][0]
    assert "claude" in args
    assert "local-rag" in args
    assert "--scope" in args
    assert "project" in args

    captured = capsys.readouterr()
    assert "local-rag" in captured.out


def test_register_mcp_server_failure_reports_stderr(tmp_path, capsys):
    fail = MagicMock()
    fail.returncode = 1
    fail.stderr = b"something went wrong"

    with patch("subprocess.run", return_value=fail):
        register_mcp_server(tmp_path)

    captured = capsys.readouterr()
    assert "something went wrong" in captured.err


def test_register_mcp_server_removes_before_adding(tmp_path):
    ok = MagicMock()
    ok.returncode = 0

    with patch("subprocess.run", return_value=ok) as mock_run:
        register_mcp_server(tmp_path)

    calls = [c[0][0] for c in mock_run.call_args_list]
    # First call must be the remove, second must be the add
    assert "remove" in calls[0]
    assert "add" in calls[1]


def test_register_mcp_server_arg_order(tmp_path):
    """--scope and --env flags must precede server name; server name must precede --."""
    ok = MagicMock()
    ok.returncode = 0

    with patch("subprocess.run", return_value=ok) as mock_run:
        register_mcp_server(tmp_path)

    args = mock_run.call_args[0][0]
    scope_idx = args.index("--scope")
    name_idx = args.index("local-rag")
    separator_idx = args.index("--")
    assert scope_idx < name_idx, "--scope must come before server name"
    assert name_idx < separator_idx, "server name must come before -- separator"


def test_register_mcp_server_includes_base_dir_and_db_path(tmp_path):
    ok = MagicMock()
    ok.returncode = 0

    with patch("subprocess.run", return_value=ok) as mock_run:
        register_mcp_server(tmp_path)

    args = mock_run.call_args[0][0]
    joined = " ".join(args)
    assert "BASE_DIR=" in joined
    assert "DB_PATH=" in joined
    assert "rag/lancedb" in joined


# ---------------------------------------------------------------------------
# hooks.py
# ---------------------------------------------------------------------------


def test_wire_hooks_creates_settings_file(tmp_path):
    wire_hooks(tmp_path, "/fake/python")
    assert (tmp_path / ".claude" / "settings.json").exists()


def test_wire_hooks_adds_post_tool_use(tmp_path):
    wire_hooks(tmp_path, "/fake/python")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "PostToolUse" in settings["hooks"]


def test_wire_hooks_adds_session_start(tmp_path):
    wire_hooks(tmp_path, "/fake/python")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "SessionStart" in settings["hooks"]


def test_wire_hooks_idempotent(tmp_path):
    wire_hooks(tmp_path, "/fake/python")
    wire_hooks(tmp_path, "/fake/python")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    # Should not have duplicate entries
    post_hooks = settings["hooks"]["PostToolUse"]
    assert len(post_hooks) == 1


def test_wire_hooks_preserves_unrelated_hooks(tmp_path):
    existing = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "echo hello"}],
                }
            ]
        }
    }
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text(json.dumps(existing))

    wire_hooks(tmp_path, "/fake/python")

    settings = json.loads(settings_path.read_text())
    post_hooks = settings["hooks"]["PostToolUse"]
    commands = [h["command"] for entry in post_hooks for h in entry["hooks"]]
    assert "echo hello" in commands
    assert any("rag/sync.py" in cmd for cmd in commands)


def test_is_managed_true():
    entry = {
        "hooks": [{"type": "command", "command": "python rag/sync.py"}]
    }
    assert _is_managed(entry) is True


def test_is_managed_false():
    entry = {"hooks": [{"type": "command", "command": "echo hello"}]}
    assert _is_managed(entry) is False


# ---------------------------------------------------------------------------
# claude_md.py
# ---------------------------------------------------------------------------


def test_write_claude_md_creates_file(tmp_path, config):
    write_claude_md(tmp_path, config)
    assert (tmp_path / "CLAUDE.md").exists()


def test_write_claude_md_contains_markers(tmp_path, config):
    write_claude_md(tmp_path, config)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "<!-- claude-rag-sync:start -->" in content
    assert "<!-- claude-rag-sync:end -->" in content


def test_write_claude_md_contains_paths_and_extensions(tmp_path, config):
    write_claude_md(tmp_path, config)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "src" in content
    assert ".py" in content


def test_write_claude_md_idempotent(tmp_path, config):
    write_claude_md(tmp_path, config)
    write_claude_md(tmp_path, config)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert content.count("<!-- claude-rag-sync:start -->") == 1


def test_write_claude_md_preserves_existing_content(tmp_path, config):
    (tmp_path / "CLAUDE.md").write_text("# My Project\n\nExisting content.\n")
    write_claude_md(tmp_path, config)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "# My Project" in content
    assert "Existing content." in content
    assert "<!-- claude-rag-sync:start -->" in content


def test_write_claude_md_replaces_old_section(tmp_path, config):
    (tmp_path / "CLAUDE.md").write_text(
        "# Project\n\n"
        "<!-- claude-rag-sync:start -->\nOld content.\n<!-- claude-rag-sync:end -->\n"
    )
    write_claude_md(tmp_path, config)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "Old content." not in content
    assert content.count("<!-- claude-rag-sync:start -->") == 1


def test_strip_managed_section_no_markers():
    text = "# Project\n\nSome content.\n"
    assert _strip_managed_section(text) == text


def test_strip_managed_section_removes_section():
    text = (
        "# Project\n\n"
        "<!-- claude-rag-sync:start -->\nManaged.\n<!-- claude-rag-sync:end -->\n"
        "\nOther content.\n"
    )
    result = _strip_managed_section(text)
    assert "Managed." not in result
    assert "# Project" in result
    assert "Other content." in result
