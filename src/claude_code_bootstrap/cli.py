"""
Generic CLI dispatcher for claude-code-bootstrap.

Feature subpackages register their own subcommands via register_commands().
"""

import argparse
import sys

from claude_code_bootstrap import __version__


def build_parser():
    parser = argparse.ArgumentParser(
        prog="claude-code-bootstrap",
        description="Bootstrap tools for Claude Code projects.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    from claude_code_bootstrap.rag_sync import (
        register_commands as register_rag_commands,
    )

    register_rag_commands(subparsers)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
