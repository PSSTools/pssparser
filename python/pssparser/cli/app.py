"""Argument parsing and top-level dispatch for the CLI."""
from __future__ import annotations

import argparse
import os
import sys


def _build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog="pssparser",
        description="PSS compiler frontend -- syntax and semantic checker",
    )

    top.add_argument("files", nargs="+", metavar="FILE", help=".pss source files")
    top.add_argument(
        "--syntax-only",
        action="store_true",
        default=False,
        help="Parse only; skip linking / symbol resolution",
    )
    top.add_argument(
        "--dump-ast",
        metavar="OUT",
        default=None,
        help="Write the linked AST to OUT as JSON",
    )
    top.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit diagnostics as JSON to stdout",
    )
    top.add_argument("-q", "--quiet", action="store_true", default=False)
    top.add_argument(
        "--color",
        action="store_true",
        default=None,
        dest="color",
        help="Force coloured output",
    )
    top.add_argument(
        "--no-color",
        action="store_false",
        dest="color",
        help="Disable coloured output",
    )
    top.add_argument(
        "--max-errors",
        type=int,
        default=20,
        metavar="N",
        help="Stop after N errors (0 = unlimited, default 20)",
    )

    return top


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns a process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()

    if argv and argv[0] == "parse":
        sys.stderr.write(
            "error: the 'parse' subcommand is no longer required; "
            "use 'pssparser [options] FILE...'\n"
        )
        return 2

    if argv and argv[0] in ("--version", "-V"):
        from pssparser.__version__ import get_version
        print(get_version())
        return 0

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    # Validate files exist
    missing = [f for f in args.files if not os.path.isfile(f)]
    if missing:
        for m in missing:
            sys.stderr.write(f"error: file not found: {m}\n")
        return 2

    from .commands import cmd_parse

    try:
        return cmd_parse(
            files=args.files,
            syntax_only=args.syntax_only,
            dump_ast=args.dump_ast,
            use_json=args.json,
            quiet=args.quiet,
            color=args.color,
            max_errors=args.max_errors,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted\n")
        return 130
