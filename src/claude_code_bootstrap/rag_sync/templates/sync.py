#!/usr/bin/env python3
"""
rag/sync.py -- RAG index sync script.

Placed in your project's rag/ directory by claude-code-bootstrap install.
Called by Claude Code hooks after file edits and at session start.

Standalone: no imports from the claude_code_bootstrap package.

Config:   rag/config.toml          (sibling of this script)
Manifest: rag/.sync_manifest.json  (sibling of this script, git-ignored)

Config format (config.toml):

    base_dir = "/absolute/path/to/project"
    included_paths = ["src", "tests", "README.md"]
    extensions = [".py", ".md", ".txt"]
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

# Script lives in rag/ -- config and manifest are siblings.
_RAG_DIR = Path(__file__).parent

_CONFIG_FILE = "config.toml"
_MANIFEST_FILE = ".sync_manifest.json"
_MCP_SERVER_CMD = ["npx", "-y", "mcp-local-rag"]
_HASH_CHUNK_SIZE = 65536


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def read_config(rag_dir: Path = _RAG_DIR) -> dict:
    """Read rag/config.toml."""
    with open(rag_dir / _CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


def collect_files(config: dict) -> dict:
    """
    Walk included_paths recursively, filter by extensions.
    Returns {relative_path_str: absolute_Path} for all matching files.
    Paths are relative to base_dir.
    """
    base_dir = Path(config["base_dir"])
    extensions = set(config["extensions"])
    files = {}

    for rel in config["included_paths"]:
        target = base_dir / rel
        if not target.exists():
            continue
        if target.is_file():
            if target.suffix in extensions:
                files[str(target.relative_to(base_dir))] = target
        else:
            for path in target.rglob("*"):
                if path.is_file() and path.suffix in extensions:
                    files[str(path.relative_to(base_dir))] = path

    return files


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def hash_file(path: Path) -> str:
    """Return SHA256 digest of a file as 'sha256:<hex>'."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_HASH_CHUNK_SIZE), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def load_manifest(rag_dir: Path = _RAG_DIR) -> dict:
    """Load .sync_manifest.json; return empty manifest if missing."""
    manifest_path = rag_dir / _MANIFEST_FILE
    if not manifest_path.exists():
        return {"files": {}, "last_sync": None}
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: dict, rag_dir: Path = _RAG_DIR) -> None:
    """Write .sync_manifest.json."""
    manifest["last_sync"] = datetime.now(timezone.utc).isoformat()
    with open(rag_dir / _MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


# ---------------------------------------------------------------------------
# MCP calls
# ---------------------------------------------------------------------------


def mcp_call(tool: str, file_path: Path, env=None) -> bool:
    """
    Invoke an mcp-local-rag tool via mcptools.
    Prints stderr to sys.stderr on failure.
    Returns True on success.

    env: environment variables for the mcp-local-rag subprocess.
         Should include BASE_DIR and DB_PATH so the server uses the
         correct security boundary and database.  When None, inherits
         the current process environment (useful in tests).
    """
    params = json.dumps({"file": str(file_path)})
    result = subprocess.run(
        ["mcp", "call", tool, "--params", params] + _MCP_SERVER_CMD,
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        print(f"[rag/sync] {tool} failed for {file_path}:", file=sys.stderr)
        if result.stderr:
            print(result.stderr.decode(errors="replace"), file=sys.stderr)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def sync(rag_dir: Path = _RAG_DIR) -> None:
    """
    Sync the RAG index with the filesystem.

    - Ingests new and changed files.
    - Removes files that no longer exist.
    - Exits immediately (no output) if nothing has changed.
    """
    config = read_config(rag_dir)
    base_dir = config["base_dir"]
    db_path = str(Path(base_dir) / "rag" / "lancedb")
    mcp_env = {**os.environ, "BASE_DIR": base_dir, "DB_PATH": db_path}

    current_files = collect_files(config)
    manifest = load_manifest(rag_dir)
    tracked = manifest.get("files", {})

    changed = 0
    removed = 0
    failed = 0

    for rel, abs_path in current_files.items():
        new_hash = hash_file(abs_path)
        if tracked.get(rel) != new_hash:
            if mcp_call("ingest_file", abs_path, mcp_env):
                tracked[rel] = new_hash
                changed += 1
            else:
                failed += 1

    for rel in list(tracked.keys()):
        if rel not in current_files:
            abs_path = Path(base_dir) / rel
            if mcp_call("delete_file", abs_path, mcp_env):
                del tracked[rel]
                removed += 1
            else:
                failed += 1

    if changed == 0 and removed == 0 and failed == 0:
        sys.exit(0)  # fast no-op

    manifest["files"] = tracked
    save_manifest(manifest, rag_dir)

    if failed:
        print(
            f"Sync: {changed} updated, {removed} removed, {failed} failed (see stderr).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Sync complete: {changed} updated, {removed} removed.")


if __name__ == "__main__":
    sync()
