"""
claude-rag-sync CLI entry point.

Subcommand-based CLI using stdlib argparse.
Current commands: install
"""

import argparse
import sys


def cmd_install(args):
    """Run the interactive RAG setup and sync wiring."""
    print("claude-rag-sync install — coming in Stage 2")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="claude-rag-sync",
        description="Set up a local RAG system with automatic sync for Claude Code projects.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    install_parser = subparsers.add_parser(
        "install",
        help="Interactive setup: configure paths, wire MCP server and hooks",
    )
    install_parser.set_defaults(func=cmd_install)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
