"""Tests for the sync engine (templates/sync.py) and setup_sync.py."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Import sync module from its template location
# ---------------------------------------------------------------------------

_SYNC_TEMPLATE = (
    Path(__file__).parent.parent
    / "src/claude_code_bootstrap/rag_sync/templates/sync.py"
)


def _load_sync():
    spec = importlib.util.spec_from_file_location("sync", _SYNC_TEMPLATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync = _load_sync()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path):
    """A minimal project layout with a rag/ dir and config.toml."""
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')", encoding="utf-8")
    (src_dir / "notes.txt").write_text("some notes", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Project", encoding="utf-8")

    config_lines = [
        f'base_dir = "{str(tmp_path).replace(chr(92), "/")}"',
        'included_paths = ["src", "README.md"]',
        'extensions = [".py", ".md"]',
    ]
    (rag_dir / "config.toml").write_text("\n".join(config_lines), encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# collect_files
# ---------------------------------------------------------------------------


def test_collect_files_includes_matching(project):
    config = sync.read_config(project / "rag")
    files = sync.collect_files(config)
    assert any("main.py" in k for k in files)
    assert any("README.md" in k for k in files)


def test_collect_files_excludes_non_matching_extension(project):
    config = sync.read_config(project / "rag")
    files = sync.collect_files(config)
    assert not any("notes.txt" in k for k in files)


def test_collect_files_skips_missing_path(project):
    config = sync.read_config(project / "rag")
    config["included_paths"].append("nonexistent")
    files = sync.collect_files(config)
    assert all("nonexistent" not in k for k in files)


def test_collect_files_recursive(project):
    nested = project / "src" / "sub"
    nested.mkdir()
    (nested / "deep.py").write_text("x = 1", encoding="utf-8")

    config = sync.read_config(project / "rag")
    files = sync.collect_files(config)
    assert any("deep.py" in k for k in files)


# ---------------------------------------------------------------------------
# hash_file
# ---------------------------------------------------------------------------


def test_hash_file_format(project):
    path = project / "README.md"
    h = sync.hash_file(path)
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64


def test_hash_file_consistent(project):
    path = project / "README.md"
    assert sync.hash_file(path) == sync.hash_file(path)


def test_hash_file_changes_on_content_change(project):
    path = project / "README.md"
    h1 = sync.hash_file(path)
    path.write_text("# Changed", encoding="utf-8")
    h2 = sync.hash_file(path)
    assert h1 != h2


# ---------------------------------------------------------------------------
# load_manifest / save_manifest
# ---------------------------------------------------------------------------


def test_load_manifest_missing(tmp_path):
    manifest = sync.load_manifest(tmp_path)
    assert manifest == {"files": {}, "last_sync": None}


def test_save_and_load_manifest(tmp_path):
    manifest = {"files": {"README.md": "sha256:abc"}, "last_sync": None}
    sync.save_manifest(manifest, tmp_path)
    loaded = sync.load_manifest(tmp_path)
    assert loaded["files"] == {"README.md": "sha256:abc"}
    assert loaded["last_sync"] is not None


# ---------------------------------------------------------------------------
# sync (integration, mcp_call mocked)
# ---------------------------------------------------------------------------


def test_sync_ingests_new_file(project):
    calls = []

    def fake_mcp(tool, path):
        calls.append((tool, path))
        return True

    with patch.object(sync, "mcp_call", side_effect=fake_mcp):
        sync.sync(project / "rag")

    assert any(tool == "ingest_file" for tool, _ in calls)


def test_sync_no_changes_exits(project):
    """Second sync with nothing changed should fast-exit."""
    with patch.object(sync, "mcp_call", return_value=True):
        sync.sync(project / "rag")

    with patch.object(sync, "mcp_call", return_value=True):
        with pytest.raises(SystemExit) as exc:
            sync.sync(project / "rag")
        assert exc.value.code == 0


def test_sync_removes_deleted_file(project):
    # First sync to populate manifest
    with patch.object(sync, "mcp_call", return_value=True):
        sync.sync(project / "rag")

    # Delete a file
    (project / "README.md").unlink()

    calls = []

    def fake_mcp(tool, path):
        calls.append((tool, path))
        return True

    with patch.object(sync, "mcp_call", side_effect=fake_mcp):
        sync.sync(project / "rag")

    assert any(tool == "delete_file" for tool, _ in calls)


def test_sync_reingest_on_change(project):
    with patch.object(sync, "mcp_call", return_value=True):
        sync.sync(project / "rag")

    (project / "README.md").write_text("# Updated", encoding="utf-8")

    calls = []

    def fake_mcp(tool, path):
        calls.append((tool, path))
        return True

    with patch.object(sync, "mcp_call", side_effect=fake_mcp):
        sync.sync(project / "rag")

    ingest_calls = [p for t, p in calls if t == "ingest_file"]
    assert any("README" in str(p) for p in ingest_calls)


# ---------------------------------------------------------------------------
# setup_sync
# ---------------------------------------------------------------------------


def test_run_initial_sync_copies_script(project):
    from claude_code_bootstrap.rag_sync.setup_sync import run_initial_sync

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        run_initial_sync(project)

    assert (project / "rag" / "sync.py").exists()


def test_run_initial_sync_invokes_python(project):
    from claude_code_bootstrap.rag_sync.setup_sync import run_initial_sync

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        run_initial_sync(project)

    args = mock_run.call_args[0][0]
    assert "sync.py" in args[-1]


# ---------------------------------------------------------------------------
# mcp_call error reporting
# ---------------------------------------------------------------------------


def test_sync_exits_nonzero_on_mcp_failure(project, capsys):
    """If mcp_call fails for all files, sync should exit non-zero, not silently succeed."""
    with patch.object(sync, "mcp_call", return_value=False):
        with pytest.raises(SystemExit) as exc:
            sync.sync(project / "rag")
        assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "failed" in captured.err


def test_sync_partial_failure_reports_counts(project, capsys):
    """Partial failures: succeeded files are tracked, failed ones are reported."""
    calls = []

    def fake_mcp(tool, path):
        calls.append(path)
        # Fail on README.md, succeed on everything else
        return "README" not in str(path)

    with patch.object(sync, "mcp_call", side_effect=fake_mcp):
        with pytest.raises(SystemExit) as exc:
            sync.sync(project / "rag")
        assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "failed" in captured.err


def test_mcp_call_prints_stderr_on_failure(project, capsys):
    from unittest.mock import MagicMock

    failed = MagicMock()
    failed.returncode = 1
    failed.stderr = b"connection refused"

    with patch("subprocess.run", return_value=failed):
        result = sync.mcp_call("ingest_file", project / "README.md")

    assert result is False
    captured = capsys.readouterr()
    assert "ingest_file" in captured.err
    assert "connection refused" in captured.err


def test_mcp_call_no_output_on_success(project, capsys):
    from unittest.mock import MagicMock

    ok = MagicMock()
    ok.returncode = 0
    ok.stderr = b""

    with patch("subprocess.run", return_value=ok):
        result = sync.mcp_call("ingest_file", project / "README.md")

    assert result is True
    captured = capsys.readouterr()
    assert captured.err == ""
