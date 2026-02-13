"""Tests for claude_rag_sync.installer"""

import json
from unittest.mock import patch

import pytest

from claude_rag_sync.installer import (
    DEFAULT_EXTENSIONS,
    check_dependencies,
    confirm_config,
    get_extensions,
    walk_directory,
    write_config,
    write_usage_guide,
)

# ---------------------------------------------------------------------------
# check_dependencies
# ---------------------------------------------------------------------------


def test_check_dependencies_all_present():
    with patch("shutil.which", return_value="/usr/bin/something"):
        check_dependencies()  # should not raise or exit


def test_check_dependencies_missing_exits(capsys):
    def fake_which(name):
        return None if name == "mcp" else "/usr/bin/something"

    with patch("shutil.which", side_effect=fake_which):
        with pytest.raises(SystemExit):
            check_dependencies()

    captured = capsys.readouterr()
    assert "mcp" in captured.out


# ---------------------------------------------------------------------------
# walk_directory
# ---------------------------------------------------------------------------


def test_walk_directory_include_all(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").touch()

    # Always answer "y"
    with patch("builtins.input", return_value="y"):
        included = walk_directory(tmp_path)

    assert "src" in included
    assert "README.md" in included


def test_walk_directory_skip_all(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").touch()

    # Always answer "n"
    with patch("builtins.input", return_value="n"):
        included = walk_directory(tmp_path)

    assert included == []


def test_walk_directory_skips_hidden_and_rag(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "rag").mkdir()
    (tmp_path / "src").mkdir()

    with patch("builtins.input", return_value="y"):
        included = walk_directory(tmp_path)

    assert ".git" not in included
    assert "rag" not in included
    assert "src" in included


def test_walk_directory_creates_dir(tmp_path):
    # tmp_path is empty so no directory-entry prompts fire.
    # CREATABLE dirs are prompted in sorted order: documents, src, tests.
    # Answer y for documents, n for the rest.
    answers = iter(["y", "n", "n"])
    with patch("builtins.input", side_effect=lambda _: next(answers)):
        included = walk_directory(tmp_path)

    assert (tmp_path / "documents").exists()
    assert "documents" in included


# ---------------------------------------------------------------------------
# get_extensions
# ---------------------------------------------------------------------------


def test_get_extensions_defaults():
    with patch("builtins.input", return_value="y"):
        exts = get_extensions()
    assert exts == DEFAULT_EXTENSIONS


def test_get_extensions_custom():
    # Decline defaults, then enter .rst and .json, then empty to finish
    answers = iter(["n", ".rst", ".json", ""])
    with patch("builtins.input", side_effect=lambda _: next(answers)):
        exts = get_extensions()
    assert exts == [".rst", ".json"]


def test_get_extensions_adds_dot():
    answers = iter(["n", "rst", ""])
    with patch("builtins.input", side_effect=lambda _: next(answers)):
        exts = get_extensions()
    assert ".rst" in exts


# ---------------------------------------------------------------------------
# confirm_config
# ---------------------------------------------------------------------------


def test_confirm_config_yes():
    config = {"included_paths": ["src"], "extensions": [".py"], "base_dir": "/tmp"}
    with patch("builtins.input", return_value="y"):
        assert confirm_config(config) is True


def test_confirm_config_no():
    config = {"included_paths": [], "extensions": [], "base_dir": "/tmp"}
    with patch("builtins.input", return_value="n"):
        assert confirm_config(config) is False


# ---------------------------------------------------------------------------
# write_config
# ---------------------------------------------------------------------------


def test_write_config(tmp_path):
    rag_dir = tmp_path / "rag"
    config = {
        "included_paths": ["src", "README.md"],
        "extensions": [".py", ".md"],
        "base_dir": str(tmp_path),
    }
    write_config(rag_dir, config)

    config_path = rag_dir / "config.json"
    assert config_path.exists()
    loaded = json.loads(config_path.read_text())
    assert loaded == config


def test_write_config_creates_rag_dir(tmp_path):
    rag_dir = tmp_path / "rag"
    assert not rag_dir.exists()
    write_config(
        rag_dir, {"included_paths": [], "extensions": [], "base_dir": str(tmp_path)}
    )
    assert rag_dir.exists()


# ---------------------------------------------------------------------------
# write_usage_guide
# ---------------------------------------------------------------------------


def test_write_usage_guide(tmp_path):
    rag_dir = tmp_path / "rag"
    config = {
        "included_paths": ["src"],
        "extensions": [".py"],
        "base_dir": str(tmp_path),
    }
    write_usage_guide(rag_dir, config)

    guide = (rag_dir / "usage_guide.md").read_text()
    assert "query_documents" in guide
    assert "sync.py" in guide
    assert ".py" in guide
