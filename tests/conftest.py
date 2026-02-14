"""
Pytest configuration and shared fixtures.

Marks:
    integration -- requires node, npx, and mcp (mcptools) on PATH
    e2e         -- requires claude CLI on PATH and ANTHROPIC_API_KEY set

Tests decorated with these marks are skipped automatically when their
dependencies are absent, so the unit test suite always runs cleanly.

Local setup:
    - Install node/npx: https://nodejs.org/
    - Install mcptools: go install github.com/f/mcptools/cmd/mcp@latest
    - Install claude CLI: npm install -g @anthropic-ai/claude-code
    - Set ANTHROPIC_API_KEY in your shell or in a .env file at the project root
"""

import os
import shutil

import pytest


# ---------------------------------------------------------------------------
# Dependency detection
# ---------------------------------------------------------------------------

_HAVE_NODE = shutil.which("node") is not None
_HAVE_NPX = shutil.which("npx") is not None
_HAVE_MCP = shutil.which("mcp") is not None
_HAVE_CLAUDE = shutil.which("claude") is not None
_HAVE_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))

_INTEGRATION_DEPS = _HAVE_NODE and _HAVE_NPX and _HAVE_MCP
_E2E_DEPS = _INTEGRATION_DEPS and _HAVE_CLAUDE and _HAVE_API_KEY


# ---------------------------------------------------------------------------
# Auto-skip via markers
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("integration") and not _INTEGRATION_DEPS:
            missing = [
                name
                for name, present in [
                    ("node", _HAVE_NODE),
                    ("npx", _HAVE_NPX),
                    ("mcp", _HAVE_MCP),
                ]
                if not present
            ]
            item.add_marker(
                pytest.mark.skip(
                    reason=f"integration deps missing: {', '.join(missing)}"
                )
            )
        if item.get_closest_marker("e2e") and not _E2E_DEPS:
            missing = []
            if not _HAVE_NODE:
                missing.append("node")
            if not _HAVE_NPX:
                missing.append("npx")
            if not _HAVE_MCP:
                missing.append("mcp")
            if not _HAVE_CLAUDE:
                missing.append("claude CLI")
            if not _HAVE_API_KEY:
                missing.append("ANTHROPIC_API_KEY")
            item.add_marker(
                pytest.mark.skip(reason=f"e2e deps missing: {', '.join(missing)}")
            )
