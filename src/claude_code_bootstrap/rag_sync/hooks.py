"""
Claude Code hooks wiring for rag-sync.

Merges PostToolUse and SessionStart hooks into .claude/settings.json
without clobbering unrelated hooks.

Managed hooks are identified by the presence of 'rag/sync.py' in their
command string. On rerun, existing managed hooks are removed and replaced.

Hook behaviour:
    PostToolUse  (matcher: Write|Edit)  -- sync after every file write/edit
    SessionStart (matcher: startup)     -- sync at the start of each session
"""

import json
from pathlib import Path

_SETTINGS_FILE = ".claude/settings.json"
_MANAGED_MARKER = "rag/sync.py"
_HOOK_TIMEOUT = 30


def _is_managed(entry: dict) -> bool:
    """Return True if this hook entry is managed by claude-rag-sync."""
    return any(
        _MANAGED_MARKER in hook.get("command", "") for hook in entry.get("hooks", [])
    )


def wire_hooks(project_root: Path, python_cmd: str) -> None:
    """
    Merge rag-sync hooks into .claude/settings.json.
    Removes any previously managed hooks before adding fresh ones.

    python_cmd: concrete Python executable path from the installer (sys.executable),
                ensuring the correct interpreter and venv are used by the hook.
    """
    sync_command = f'"{python_cmd}" rag/sync.py'
    rag_hooks = {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": sync_command,
                        "timeout": _HOOK_TIMEOUT,
                    }
                ],
            }
        ],
        "SessionStart": [
            {
                "matcher": "startup",
                "hooks": [
                    {
                        "type": "command",
                        "command": sync_command,
                        "timeout": _HOOK_TIMEOUT,
                    }
                ],
            }
        ],
    }

    settings_path = project_root / _SETTINGS_FILE
    settings_path.parent.mkdir(exist_ok=True)

    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {}

    existing_hooks = settings.get("hooks", {})

    # Strip our managed hooks (idempotent)
    cleaned: dict = {}
    for event, entries in existing_hooks.items():
        filtered = [e for e in entries if not _is_managed(e)]
        if filtered:
            cleaned[event] = filtered

    # Add fresh managed hooks
    for event, new_entries in rag_hooks.items():
        cleaned.setdefault(event, []).extend(new_entries)

    settings["hooks"] = cleaned

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

    print(f"\nUpdated {settings_path}")
