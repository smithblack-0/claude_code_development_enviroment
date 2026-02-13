"""
Initial sync setup: copies the sync script into the project and runs first index.

Copies templates/sync.py to rag/sync.py, then invokes it to populate the index.
"""

import shutil
import subprocess
import sys
from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def run_initial_sync(project_root: Path) -> None:
    """Copy sync.py to rag/ and run the initial index population."""
    rag_dir = project_root / "rag"
    rag_dir.mkdir(exist_ok=True)

    dest = rag_dir / "sync.py"
    shutil.copy(_TEMPLATES_DIR / "sync.py", dest)
    print(f"\nWrote {dest}")

    print("Running initial sync...")
    result = subprocess.run([sys.executable, str(dest)], capture_output=False)
    if result.returncode != 0:
        print(
            "Warning: initial sync encountered errors. Run 'python rag/sync.py' to retry."
        )
