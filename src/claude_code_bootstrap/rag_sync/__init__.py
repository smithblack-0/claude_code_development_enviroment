"""RAG sync feature — registers CLI commands into the generic dispatcher."""


def register_commands(subparsers) -> None:
    """Register the 'install' subcommand with the top-level dispatcher."""
    parser = subparsers.add_parser(
        "install",
        help="Interactive setup: configure paths, wire MCP server and hooks",
    )
    parser.set_defaults(func=_cmd_install)


def _cmd_install(args) -> None:
    from claude_code_bootstrap.rag_sync.installer import run_install

    run_install()
