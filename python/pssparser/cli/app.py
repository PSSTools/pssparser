"""Argument parsing and top-level dispatch for the CLI."""
from __future__ import annotations

import argparse
import os
import sys


class _WarningAction(argparse.Action):
    """Parse the GCC-style ``-W...`` family into a ``WarningPolicy``.

    ``argparse`` splits ``-Wno-error=PSS104`` into the option string ``-W``
    with the explicit argument ``no-error=PSS104`` -- exactly the shape GCC
    uses -- so a single ``-W`` option covers the whole family.  Pre-scanning
    ``sys.argv`` would also work, but it breaks ``--`` and ``@file``
    handling, so it is deliberately not done here.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        from .diagnostics import WarningPolicy

        policy = getattr(namespace, "warning_policy", None)
        if policy is None:
            policy = WarningPolicy()
            setattr(namespace, "warning_policy", policy)

        spec = values
        if spec == "error":
            policy.error_all = True
        elif spec.startswith("error="):
            policy.error_codes.add(spec[len("error="):])
        elif spec.startswith("no-error="):
            policy.no_error_codes.add(spec[len("no-error="):])
        else:
            parser.error(
                f"unrecognised warning option '-W{spec}' "
                "(expected -Werror, -Werror=ID, or -Wno-error=ID)"
            )


def _build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog="pssparser",
        description="PSS compiler frontend -- syntax and semantic checker",
    )

    top.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help=".pss source files",
    )

    # -- checker query-and-exit flags ------------------------------------
    query_grp = top.add_argument_group("checker query flags (no source files required)")
    query_grp.add_argument(
        "--list-checkers",
        action="store_true",
        default=False,
        help="List all registered checkers and exit",
    )
    query_grp.add_argument(
        "--list-markers",
        action="store_true",
        default=False,
        help="List all declared marker IDs across all checkers and exit",
    )
    query_grp.add_argument(
        "--describe",
        metavar="ID",
        default=None,
        help="Print the full definition for marker ID and exit",
    )

    # -- checker selection flags ----------------------------------------
    sel_grp = top.add_argument_group("checker selection flags")
    sel_grp.add_argument(
        "--checker",
        action="append",
        metavar="NAME",
        dest="checkers",
        default=None,
        help="Run only this checker (may be repeated)",
    )
    sel_grp.add_argument(
        "--no-checker",
        action="append",
        metavar="NAME",
        dest="no_checkers",
        default=None,
        help="Exclude this checker (may be repeated)",
    )
    sel_grp.add_argument(
        "--load-checker",
        action="append",
        metavar="MODULE:CLASS",
        dest="load_checkers",
        default=None,
        help="Dynamically load a checker from MODULE:CLASS (may be repeated)",
    )
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
    # -- warning policy ---------------------------------------------------
    warn_grp = top.add_argument_group("warning policy")
    warn_grp.add_argument(
        "-W",
        action=_WarningAction,
        dest="warning_policy",
        default=None,
        metavar="SPEC",
        help="-Werror (all warnings are errors), -Werror=ID (only ID), "
             "-Wno-error=ID (exempt ID from -Werror)",
    )
    warn_grp.add_argument(
        "--no-warnings",
        action="store_true",
        default=False,
        help="Suppress all warnings (applied before -Werror)",
    )
    # -- run statistics ---------------------------------------------------
    stats_grp = top.add_argument_group("run statistics")
    stats_grp.add_argument(
        "--stats",
        action="store_true",
        default=False,
        help="Report declaration counts, diagnostic codes, and phase timings",
    )
    stats_grp.add_argument(
        "--stats-no-timing",
        action="store_true",
        default=False,
        help="As --stats, but omit wall times so the output is reproducible",
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

    # -- Build and populate CheckerManager --------------------------------
    from pssparser.checkers import CheckerManager
    from .checker_cmds import cmd_list_checkers, cmd_list_markers, cmd_describe

    manager = CheckerManager()
    manager.discover()

    # Apply any --load-checker specs before handling query flags
    if args.load_checkers:
        for spec in args.load_checkers:
            try:
                manager.load(spec)
            except ValueError as exc:
                sys.stderr.write(f"error: {exc}\n")
                return 2

    # -- Query-and-exit flags (no source files needed) --------------------
    if args.list_checkers:
        return cmd_list_checkers(manager)

    if args.list_markers:
        return cmd_list_markers(manager)

    if args.describe is not None:
        return cmd_describe(manager, args.describe)

    # -- Require source files when no query flag is active ----------------
    if not args.files:
        sys.stderr.write(
            "error: at least one source FILE is required "
            "(or use --list-checkers / --list-markers / --describe)\n"
        )
        return 2

    # Validate files exist
    missing = [f for f in args.files if not os.path.isfile(f)]
    if missing:
        for m in missing:
            sys.stderr.write(f"error: file not found: {m}\n")
        return 2

    from .commands import cmd_parse
    from .diagnostics import WarningPolicy

    policy = args.warning_policy or WarningPolicy()
    policy.no_warnings = args.no_warnings

    try:
        return cmd_parse(
            files=args.files,
            syntax_only=args.syntax_only,
            dump_ast=args.dump_ast,
            use_json=args.json,
            quiet=args.quiet,
            color=args.color,
            max_errors=args.max_errors,
            manager=manager,
            checkers=args.checkers,
            no_checkers=args.no_checkers,
            warning_policy=policy,
            # --stats-no-timing implies --stats; it is a variant of it, not
            # a modifier that needs both flags spelled out.
            show_stats=args.stats or args.stats_no_timing,
            stats_timing=not args.stats_no_timing,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted\n")
        return 130
