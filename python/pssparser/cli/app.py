"""Argument parsing and top-level dispatch for the CLI."""
from __future__ import annotations

import argparse
import os
import sys

from . import config as config_mod


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


def _report_load_issues(manager, stream) -> None:
    """Write extension-load problems to *stream* as plain ``severity:`` lines.

    Only for the query-and-exit paths, which never construct a
    ``DiagnosticCollection``.  The parse path routes the same issues through
    the normal diagnostic machinery instead, so they are counted, rendered,
    and included in ``--json`` like anything else.
    """
    for marker in manager.load_diagnostics:
        stream.write(f"{marker['severity']}: {marker['message']}\n")


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
    query_grp.add_argument(
        "--list-extensions",
        action="store_true",
        default=False,
        help="List installed checker extensions and exit",
    )
    query_grp.add_argument(
        "--describe-checker",
        metavar="NAME",
        default=None,
        help="Print a checker's markers and configurable options, and exit",
    )
    query_grp.add_argument(
        "--show-config",
        action="store_true",
        default=False,
        help="Print the resolved configuration with per-value provenance "
             "and exit",
    )

    # -- configuration ----------------------------------------------------
    cfg_grp = top.add_argument_group("configuration")
    cfg_grp.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Read configuration from PATH instead of searching for "
             f"{config_mod.CONFIG_FILENAME} / pyproject.toml",
    )
    cfg_grp.add_argument(
        "--no-config",
        action="store_true",
        default=False,
        help="Ignore any configuration file",
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
    sel_grp.add_argument(
        "--no-extensions",
        action="store_true",
        default=False,
        help="Skip installed checker extensions; run the built-in checks only "
             "(same as PSSPARSER_NO_EXTENSIONS=1)",
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
    from .checker_cmds import (
        cmd_describe,
        cmd_describe_checker,
        cmd_list_checkers,
        cmd_list_extensions,
        cmd_list_markers,
    )

    manager = CheckerManager()
    manager.discover(load_extensions=not args.no_extensions)

    # -- Configuration ----------------------------------------------------
    #
    # Resolved before --load-checker so that `load` from a config file and
    # --load-checker go through one code path, and before the query flags so
    # that --list-checkers reflects a config that disabled an extension.
    try:
        cfg = config_mod.resolve(args)
    except config_mod.ConfigError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    for ext_name, enabled in cfg.extensions_enabled.items():
        if not enabled:
            manager.disable_extension(ext_name)

    for spec in cfg.load:
        try:
            manager.load(spec)
        except ValueError as exc:
            # A spec typed on the command line needs no attribution; one
            # that came from a file does, since the user is not looking at
            # the file when they read the error.
            source = cfg.provenance.get("load", "command line")
            where = "" if source == "command line" else f"{source}: "
            sys.stderr.write(f"error: {where}{exc}\n")
            return 2

    try:
        config_mod.validate_against_registry(cfg, manager)
    except config_mod.ConfigError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    try:
        manager.validate_options(cfg.checker_options)
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    if args.show_config:
        _report_load_issues(manager, sys.stderr)
        sys.stdout.write(config_mod.format_show_config(cfg))
        return 0

    # -- Query-and-exit flags (no source files needed) --------------------
    #
    # The query paths never build a DiagnosticCollection, so an extension that
    # failed to load has nowhere to be reported except stderr.  Print it
    # first: "this extension is missing" is the context that explains a
    # --list-checkers output with a checker absent from it.
    if (args.list_checkers or args.list_markers or args.list_extensions
            or args.describe is not None
            or args.describe_checker is not None):
        _report_load_issues(manager, sys.stderr)

    if args.list_checkers:
        return cmd_list_checkers(manager)

    if args.list_markers:
        return cmd_list_markers(manager)

    if args.list_extensions:
        return cmd_list_extensions(manager)

    if args.describe is not None:
        return cmd_describe(manager, args.describe)

    if args.describe_checker is not None:
        return cmd_describe_checker(manager, args.describe_checker)

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

    # The config layer already resolved CLI-versus-file precedence for every
    # warning setting, so the policy is written from `cfg`, not from `args`.
    policy = args.warning_policy or WarningPolicy()
    config_mod.to_warning_policy(cfg, policy)

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
            checkers=cfg.select,
            no_checkers=cfg.disable,
            warning_policy=policy,
            config=cfg,
            # --stats-no-timing implies --stats; it is a variant of it, not
            # a modifier that needs both flags spelled out.
            show_stats=args.stats or args.stats_no_timing,
            stats_timing=not args.stats_no_timing,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted\n")
        return 130
