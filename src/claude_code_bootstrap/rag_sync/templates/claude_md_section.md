## RAG Index (managed by claude-code-bootstrap)

A local RAG index is available via the `local-rag` MCP server.

### What is indexed

Paths: $paths

Extensions: $extensions

### Querying

Use the `query_documents` tool to search the index:

```
query_documents(query="your search terms")
```

Results are ranked chunks with source file paths and surrounding context.

Other available tools: `list_files` (show indexed files), `status` (index health).

### Sync

The index is kept current automatically:
- After every file write or edit (PostToolUse hook)
- At the start of each session (SessionStart hook)

To sync manually: `python rag/sync.py`

To reconfigure what is indexed: `claude-code-bootstrap install`
