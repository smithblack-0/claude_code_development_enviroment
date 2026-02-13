"""
CLAUDE.md instructions for rag-sync.

Appends a managed section to CLAUDE.md bounded by markers:
    <!-- claude-rag-sync:start -->
    <!-- claude-rag-sync:end -->

On rerun the existing section is replaced. Other content is untouched.
"""

from pathlib import Path
from string import Template

_START_MARKER = "<!-- claude-rag-sync:start -->"
_END_MARKER = "<!-- claude-rag-sync:end -->"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _strip_managed_section(text: str) -> str:
    """Remove an existing managed section from text, if present."""
    if _START_MARKER not in text:
        return text
    before = text[: text.index(_START_MARKER)]
    after_end = text[text.index(_END_MARKER) + len(_END_MARKER) :]
    return before.rstrip() + "\n" + after_end.lstrip()


def write_claude_md(project_root: Path, config: dict) -> None:
    """
    Append (or replace) the rag-sync managed section in CLAUDE.md.
    Creates CLAUDE.md if it does not exist.
    """
    claude_md_path = project_root / "CLAUDE.md"

    template_text = (_TEMPLATES_DIR / "claude_md_section.md").read_text(
        encoding="utf-8"
    )
    content = Template(template_text).safe_substitute(
        paths=", ".join(f"`{p}`" for p in config["included_paths"]),
        extensions=", ".join(config["extensions"]),
    )
    section = f"{_START_MARKER}\n{content.strip()}\n{_END_MARKER}\n"

    existing = (
        claude_md_path.read_text(encoding="utf-8") if claude_md_path.exists() else ""
    )
    stripped = _strip_managed_section(existing)
    result = (stripped.rstrip() + "\n\n" + section) if stripped.strip() else section

    claude_md_path.write_text(result, encoding="utf-8")
    print(f"\nUpdated {claude_md_path}")
