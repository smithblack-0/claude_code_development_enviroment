# RAG Usage Guide

## What is in this directory?

`rag/` holds everything the local RAG system needs:

| File / Directory        | Purpose                                               |
|------------------------|-------------------------------------------------------|
| `config.toml`          | Which paths and file types are indexed                |
| `rag_usage_guide.md`   | This file                                             |
| `sync.py`              | Sync script called automatically by Claude Code hooks |
| `lancedb/`             | Vector database (git-ignored)                         |
| `.sync_manifest.json`  | Hash manifest for change detection (git-ignored)      |

## What is indexed?

Paths: $paths

Extensions: $extensions

To change what is indexed, edit `rag/config.toml` and run `python rag/sync.py`.

## How does sync work?

A hook in `.claude/settings.json` runs `python rag/sync.py` after every file
write/edit and at the start of each Claude Code session. The sync script:

1. Reads `rag/config.toml`
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

## Editing config.toml

```toml
base_dir = "/absolute/path/to/project"
included_paths = ["src", "tests", "README.md"]
extensions = [".py", ".md", ".txt"]
```

After editing, run `python rag/sync.py` to apply changes.

## Manual sync

```
python rag/sync.py
```

## Re-run setup

```
claude-code-bootstrap install
```

Re-running is safe — config is rebuilt interactively and the existing index is preserved.
