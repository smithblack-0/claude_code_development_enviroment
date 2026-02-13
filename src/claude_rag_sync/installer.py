"""
Core install logic for claude-rag-sync.

Install sequence:
  1. check_dependencies()       - verify node, npx, mcp, claude are available
  2. walk_directory()           - interactive include/skip of top-level paths
  3. get_extensions()           - confirm/edit extension filter
  4. confirm_config()           - display full config, require confirmation
  5. write_config()             - write rag/config.json
  6. write_usage_guide()        - write rag/usage_guide.md
  7. run_initial_sync()         - STUB: run python rag/sync.py  (Stage 3)
  8. register_mcp_server()      - STUB: claude mcp add local-rag  (Stage 4)
  9. wire_hooks()               - STUB: write hooks to .claude/settings.json  (Stage 4)
 10. write_claude_md()          - STUB: append instructions to CLAUDE.md  (Stage 4)
"""

import json
import os
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency checking
# ---------------------------------------------------------------------------

REQUIRED_TOOLS = {
    "node": "https://nodejs.org/",
    "npx": "https://nodejs.org/  (comes with Node)",
    "mcp": "https://github.com/f/mcptools  (go install github.com/f/mcptools/cmd/mcp@latest)",
    "claude": "https://claude.ai/code  (install Claude Code CLI)",
}


def check_dependencies():
    """Verify all required tools are on PATH. Exit with guidance if any are missing."""
    missing = {
        name: url for name, url in REQUIRED_TOOLS.items() if not shutil.which(name)
    }
    if not missing:
        return

    print("\nMissing required tools:\n")
    for name, url in missing.items():
        print(f"  {name:10s}  Install from: {url}")
    print()
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1: Interactive directory walk
# ---------------------------------------------------------------------------

HIGHLIGHTED = {"src", "tests", "documents", "doc", "docs", "README.md", "CLAUDE.md"}
CREATABLE = {"src", "tests", "documents"}


def _prompt_yes_no(question, default=True):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {hint}: ").strip().lower()
        if answer == "":
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please enter y or n.")


def walk_directory(project_root: Path) -> list[str]:
    """
    Interactively walk top-level entries of project_root.
    Returns a list of relative path strings to include.
    """
    print("\n--- Step 1: Select paths to index ---\n")
    print(f"Project root: {project_root}\n")

    entries = sorted(
        project_root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
    )
    included = []

    for entry in entries:
        rel = entry.name
        if rel.startswith(".") or rel == "rag":
            continue  # skip hidden dirs and the rag dir itself

        tag = " (recommended)" if rel in HIGHLIGHTED else ""
        kind = "file" if entry.is_file() else "dir"
        if _prompt_yes_no(
            f"  Include {kind} '{rel}'{tag}?", default=(rel in HIGHLIGHTED)
        ):
            included.append(rel)

    # Offer to create common dirs if they don't exist
    print()
    for name in sorted(CREATABLE):
        target = project_root / name
        if not target.exists():
            if _prompt_yes_no(f"  '{name}/' doesn't exist — create it?", default=False):
                target.mkdir()
                print(f"    Created {target}")
                included.append(name)

    return included


# ---------------------------------------------------------------------------
# Step 2: Extension filter
# ---------------------------------------------------------------------------

DEFAULT_EXTENSIONS = [".md", ".py", ".txt"]


def get_extensions() -> list[str]:
    """Prompt the user to confirm or modify the extension filter."""
    print("\n--- Step 2: File extensions to index ---\n")
    print(f"  Defaults: {', '.join(DEFAULT_EXTENSIONS)}")

    if _prompt_yes_no("  Use defaults?", default=True):
        return list(DEFAULT_EXTENSIONS)

    print("  Enter extensions one per line (e.g. .rst). Empty line when done.")
    extensions = []
    while True:
        ext = input("  Extension: ").strip()
        if ext == "":
            break
        if not ext.startswith("."):
            ext = "." + ext
        extensions.append(ext)

    return extensions if extensions else list(DEFAULT_EXTENSIONS)


# ---------------------------------------------------------------------------
# Step 3: Config summary + confirmation
# ---------------------------------------------------------------------------


def confirm_config(config: dict) -> bool:
    """Display full config and ask the user to confirm before writing."""
    print("\n--- Step 3: Review configuration ---\n")
    print(json.dumps(config, indent=2))
    print()
    return _prompt_yes_no("Write this configuration?", default=True)


# ---------------------------------------------------------------------------
# Steps 4-5: Write outputs
# ---------------------------------------------------------------------------


def write_config(rag_dir: Path, config: dict):
    """Write rag/config.json."""
    rag_dir.mkdir(exist_ok=True)
    config_path = rag_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {config_path}")


def write_usage_guide(rag_dir: Path, config: dict):
    """Write rag/usage_guide.md explaining how the RAG system works."""
    rag_dir.mkdir(exist_ok=True)
    guide_path = rag_dir / "usage_guide.md"
    extensions = ", ".join(config["extensions"])
    paths = ", ".join(f"`{p}`" for p in config["included_paths"])
    guide_path.write_text(
        f"""\
# RAG Usage Guide

## What is in this directory?

`rag/` holds everything the local RAG system needs:

| File / Directory | Purpose |
|-----------------|---------|
| `config.json` | Which paths and file types are indexed |
| `usage_guide.md` | This file |
| `sync.py` | Sync script — called automatically by Claude Code hooks |
| `lancedb/` | Vector database (git-ignored) |
| `.sync_manifest.json` | Hash manifest for change detection (git-ignored) |

## What is indexed?

Paths: {paths}

Extensions: {extensions}

To change what is indexed, edit `rag/config.json` and run `python rag/sync.py`.

## How does sync work?

A hook in `.claude/settings.json` runs `python rag/sync.py` after every file
write/edit and at the start of each Claude Code session. The sync script:

1. Reads `rag/config.json`
2. Walks the included paths, filtering by extension
3. Hashes each file and compares against `rag/.sync_manifest.json`
4. Ingests new/changed files and removes deleted ones via the MCP server
5. If nothing has changed, exits in milliseconds (no-op)

## How to query

In Claude Code, use the `query_documents` tool from the `local-rag` MCP server:

```
query_documents(query="your search terms")
```

Other available tools: `list_files`, `status`.

## Manual sync

```bash
python rag/sync.py
```

## How to re-run setup

```bash
claude-rag-sync install
```

Re-running is safe — config is rebuilt interactively and the existing index is preserved.
""",
        encoding="utf-8",
    )
    print(f"Wrote {guide_path}")


# ---------------------------------------------------------------------------
# Step 6: Initial sync  (Stage 3 stub)
# ---------------------------------------------------------------------------


def run_initial_sync(project_root: Path):
    """
    STUB (Stage 3): Run python rag/sync.py to populate the index.

    Will invoke: python rag/sync.py
    """
    print("\n[stub] run_initial_sync — will run 'python rag/sync.py' (Stage 3)")


# ---------------------------------------------------------------------------
# Step 7: Register MCP server  (Stage 4 stub)
# ---------------------------------------------------------------------------


def register_mcp_server(project_root: Path):
    """
    STUB (Stage 4): Register the mcp-local-rag server with Claude Code.

    Will invoke:
        claude mcp add local-rag --scope project
            --env BASE_DIR=<project_root>
            --env DB_PATH=<project_root>/rag/lancedb
            -- npx -y mcp-local-rag
    """
    print(
        "\n[stub] register_mcp_server — will run 'claude mcp add local-rag' (Stage 4)"
    )


# ---------------------------------------------------------------------------
# Step 8: Wire hooks  (Stage 4 stub)
# ---------------------------------------------------------------------------


def wire_hooks(project_root: Path):
    """
    STUB (Stage 4): Merge PostToolUse and SessionStart hooks into
    .claude/settings.json without clobbering unrelated hooks.
    """
    print("\n[stub] wire_hooks — will write hooks to .claude/settings.json (Stage 4)")


# ---------------------------------------------------------------------------
# Step 9: Write CLAUDE.md instructions  (Stage 4 stub)
# ---------------------------------------------------------------------------


def write_claude_md(project_root: Path, config: dict):
    """
    STUB (Stage 4): Append a managed section to CLAUDE.md between
    <!-- claude-rag-sync:start --> and <!-- claude-rag-sync:end --> markers.
    """
    print(
        "\n[stub] write_claude_md — will append RAG instructions to CLAUDE.md (Stage 4)"
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_install():
    """Run the full install sequence."""
    project_root = Path(os.getcwd()).resolve()

    print("=== claude-rag-sync install ===")

    check_dependencies()

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

    run_initial_sync(project_root)
    register_mcp_server(project_root)
    wire_hooks(project_root)
    write_claude_md(project_root, config)

    print("\nDone. Run 'python rag/sync.py' at any time to manually sync the index.")
