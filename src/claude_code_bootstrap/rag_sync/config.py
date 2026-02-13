"""Config reading and writing for rag-sync."""

from pathlib import Path
from string import Template

import tomli

_TEMPLATES_DIR = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# TOML helpers
# ---------------------------------------------------------------------------


def _toml_array(items: list) -> str:
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def write_config(rag_dir: Path, config: dict) -> None:
    """Write rag/config.toml."""
    rag_dir.mkdir(exist_ok=True)
    config_path = rag_dir / "config.toml"
    base_dir = config["base_dir"].replace("\\", "/")
    lines = [
        f'base_dir = "{base_dir}"',
        f'included_paths = {_toml_array(config["included_paths"])}',
        f'extensions = {_toml_array(config["extensions"])}',
    ]
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {config_path}")


def read_config(rag_dir: Path) -> dict:
    """Read rag/config.toml."""
    config_path = rag_dir / "config.toml"
    with open(config_path, "rb") as f:
        return tomli.load(f)


def write_usage_guide(rag_dir: Path, config: dict) -> None:
    """Write rag/rag_usage_guide.md from template."""
    template_text = (_TEMPLATES_DIR / "rag_usage_guide.md").read_text(encoding="utf-8")
    content = Template(template_text).safe_substitute(
        paths=", ".join(f"`{p}`" for p in config["included_paths"]),
        extensions=", ".join(config["extensions"]),
    )
    rag_dir.mkdir(exist_ok=True)
    guide_path = rag_dir / "rag_usage_guide.md"
    guide_path.write_text(content, encoding="utf-8")
    print(f"Wrote {guide_path}")
