# claude-rag-sync

Set up a local RAG system with automatic sync for Claude Code projects.

## Install

```bash
pip install claude-rag-sync
```

## Usage

From your project root:

```bash
claude-rag-sync install
```

This walks you through selecting which files to index, writes `rag/config.json`, registers the MCP server with Claude Code, and wires sync hooks so the index stays current as you work.
