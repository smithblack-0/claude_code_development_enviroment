#!/usr/bin/env python3
"""
Install dependencies required to run integration and e2e tests.

Usage:
    python scripts/install_test_deps.py

What this installs (if missing):
    - mcptools (mcp)     via: go install github.com/f/mcptools/cmd/mcp@latest
    - claude CLI          via: npm install -g @anthropic-ai/claude-code

Prerequisites this script cannot install for you:
    - Node.js / npm       https://nodejs.org/
    - Go                  https://go.dev/dl/

After running this script, set your API key:
    - Copy .env to .env and fill in ANTHROPIC_API_KEY
    - Or: set ANTHROPIC_API_KEY in your shell environment

Running the tests:
    pytest -m unit                   # always runs, no deps needed
    pytest -m integration            # needs node, npx, mcp
    pytest -m e2e                    # needs all of the above + claude + API key
    pytest                           # runs everything, skips what it can't
"""

import shutil
import subprocess
import sys


def check(tool: str) -> bool:
    return shutil.which(tool) is not None


def run(cmd: list[str], description: str) -> bool:
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"  FAILED: {description}")
        return False
    print(f"  OK: {description}")
    return True


def main() -> None:
    print("=== claude-code-bootstrap: install test dependencies ===\n")

    # -----------------------------------------------------------------------
    # Check prerequisites
    # -----------------------------------------------------------------------

    missing_prereqs = []
    if not check("node"):
        missing_prereqs.append(("node", "https://nodejs.org/"))
    if not check("npm"):
        missing_prereqs.append(("npm", "https://nodejs.org/  (comes with Node)"))
    if not check("go"):
        missing_prereqs.append(("go", "https://go.dev/dl/"))

    if missing_prereqs:
        print("The following prerequisites must be installed manually:\n")
        for name, url in missing_prereqs:
            print(f"  {name:6s}  {url}")
        print()

    # -----------------------------------------------------------------------
    # Install mcptools
    # -----------------------------------------------------------------------

    if check("mcp"):
        print("mcp (mcptools): already installed")
    elif not check("go"):
        print("mcp (mcptools): skipped (go not available)")
    else:
        print("mcp (mcptools): installing...")
        run(
            ["go", "install", "github.com/f/mcptools/cmd/mcp@latest"],
            "install mcptools",
        )
        if not check("mcp"):
            print(
                "  NOTE: ensure $GOPATH/bin (or %GOPATH%\\bin on Windows) is on PATH\n"
                "        Typically: ~/go/bin on Linux/Mac, %USERPROFILE%\\go\\bin on Windows"
            )

    # -----------------------------------------------------------------------
    # Install claude CLI
    # -----------------------------------------------------------------------

    if check("claude"):
        print("claude CLI: already installed")
    elif not check("npm"):
        print("claude CLI: skipped (npm not available)")
    else:
        print("claude CLI: installing...")
        run(
            ["npm", "install", "-g", "@anthropic-ai/claude-code"],
            "install claude CLI",
        )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    print("\n--- Status ---")
    deps = [
        ("node", "integration + e2e"),
        ("npx", "integration + e2e"),
        ("mcp", "integration + e2e"),
        ("claude", "e2e only"),
    ]
    all_good = True
    for tool, needed_for in deps:
        present = check(tool)
        status = "OK" if present else "MISSING"
        print(f"  {tool:10s} {status:8s} ({needed_for})")
        if not present:
            all_good = False

    import os
    api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    print(f"  {'API key':10s} {'OK' if api_key_set else 'NOT SET':8s} (e2e only -- set in .env or shell)")

    print()
    if all_good and api_key_set:
        print("All dependencies present. Run: pytest")
    elif all_good:
        print("Tools ready. Set ANTHROPIC_API_KEY to enable e2e tests.")
        print("  cp .env .env  # then edit .env")
    else:
        print("Some deps still missing. Integration/e2e tests will be skipped.")
        print("Re-run this script after installing prerequisites.")


if __name__ == "__main__":
    main()
