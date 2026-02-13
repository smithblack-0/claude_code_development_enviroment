"""
Reusable dependency checking for claude-code-bootstrap commands.

Each feature provides its own tools dict; this module provides the check function.
"""

import shutil
import sys


def check_dependencies(tools: dict) -> None:
    """
    Verify that all tools in `tools` are on PATH.
    Prints install guidance and exits if any are missing.

    Args:
        tools: mapping of tool name -> install URL/instructions
    """
    missing = {name: url for name, url in tools.items() if not shutil.which(name)}
    if not missing:
        return

    print("\nMissing required tools:\n")
    for name, url in missing.items():
        print(f"  {name:10s}  Install from: {url}")
    print()
    sys.exit(1)
