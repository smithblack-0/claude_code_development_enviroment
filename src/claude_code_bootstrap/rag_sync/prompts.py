"""Interactive prompts for the rag-sync install flow."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HIGHLIGHTED = {"src", "tests", "documents", "doc", "docs", "README.md", "CLAUDE.md"}
CREATABLE = {"src", "tests", "documents"}
DEFAULT_EXTENSIONS = [".md", ".py", ".txt"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prompt_yes_no(question: str, default: bool = True) -> bool:
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


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def walk_directory(project_root: Path) -> list:
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


def get_extensions() -> list:
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


def confirm_config(config: dict) -> bool:
    """Display full config and ask the user to confirm before writing."""
    import json

    print("\n--- Step 3: Review configuration ---\n")
    print(json.dumps(config, indent=2))
    print()
    return _prompt_yes_no("Write this configuration?", default=True)
