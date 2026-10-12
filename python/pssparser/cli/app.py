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

        # The text after '=' may be any rule selector -- an ID, a rule
        # name, a tier, 'family:x', a prefix -- or 'info'.  Selectors are
        # resolved to IDs once the registry is loaded (config layer).
        spec = values
        if spec == "error":
            policy.error_all = True
        elif spec == "error=info":
            policy.error_info = True
        elif spec.startswith("error="):
            policy.error_codes.add(spec[len("error="):])
        elif spec.startswith("no-error="):
            policy.no_error_codes.add(spec[len("no-error="):])
        else:
            parser.error(
                f"unrecognised warning option '-W{spec}' "
                "(expected -Werror, -Werror=SELECTOR, or -Wno-error=SELECTOR)"
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
        "--explain",
        metavar="RULE",
        default=None,
        help="Explain a rule -- by ID, old ID, or name -- with its tier, "
             "LRM references and examples, and exit",
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
        help="Print the resolved configuration with per-value provenance, "
             "and the rule files loaded, and exit",
    )
    query_grp.add_argument(
        "--for",
        action="append",
        metavar="FILE",
        dest="show_config_for",
        default=None,
        help="With --show-config: also show the overrides that match FILE "
             "and the lint rules it gets (may be repeated)",
    )
    query_grp.add_argument(
        "--rules-for",
        action="store_true",
        default=False,
        help="Print the lint rules that would run on each FILE, after the "
             "configuration and its overrides, and exit; no model is parsed "
             "and a FILE need not exist. --format json adds docs, options "
             "and examples",
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
        "--format",
        choices=("text", "json", "sarif", "github"),
        default=None,
        dest="output_format",
        help="Output format: text (default, to stderr), or json, sarif or "
             "github (GitHub Actions annotations), to stdout",
    )
    top.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Same as --format json",
    )
    top.add_argument(
        "--statistics",
        action="store_true",
        default=False,
        help="Print a per-code count of the diagnostics reported",
    )
    top.add_argument("-q", "--quiet", action="store_true", default=False)
    top.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Also say what was skipped: files in a rules directory that "
             "are not rule files",
    )
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
        help="-Werror (all warnings are errors), -Werror=SEL (only rules "
             "matching SEL: an ID, rule name, tier, family:NAME, ID prefix, "
             "or 'info'), -Wno-error=SEL (exempt SEL from -Werror)",
    )
    # -- lint ---------------------------------------------------------------
    lint_grp = top.add_argument_group("lint")
    lint_grp.add_argument(
        "--lint-profile",
        metavar="NAME",
        default=None,
        choices=("minimal", "recommended", "library", "strict", "all", "none"),
        help="Lint profile: minimal (default), recommended, library, strict, "
             "all, or none",
    )
    lint_grp.add_argument(
        "--no-lint",
        action="store_true",
        default=False,
        help="Report no lint findings (same as --lint-profile none); "
             "LRM errors and the tool's own diagnostics are unaffected",
    )
    lint_grp.add_argument(
        "--select",
        action="append",
        metavar="SEL",
        dest="cli_select",
        default=None,
        help="Enable the lint rules matching SEL -- an ID, rule name, tier, "
             "family:NAME or ID prefix such as a rule file's namespace -- on "
             "top of the configuration (may be repeated)",
    )
    lint_grp.add_argument(
        "--ignore",
        action="append",
        metavar="SEL",
        dest="cli_ignore",
        default=None,
        help="Disable the lint rules matching SEL, on top of the "
             "configuration; beats a --select of the same specificity "
             "(may be repeated)",
    )
    lint_grp.add_argument(
        "--rules",
        action="append",
        metavar="PATH",
        dest="rule_paths",
        default=None,
        help="Load pss-rules files from PATH, a file or a directory, after "
             "those in [lint] rules (may be repeated)",
    )
    lint_grp.add_argument(
        "--check-rules",
        action="store_true",
        default=False,
        help="Load and validate rule files and exit: the FILE arguments, "
             "or else [lint] rules and --rules. Exit 0 clean, 1 rule errors",
    )
    lint_grp.add_argument(
        "--show-hints",
        action="store_true",
        default=False,
        help="Print 'hint' diagnostics, which are hidden by default",
    )
    lint_grp.add_argument(
        "--show-waived",
        action="store_true",
        default=False,
        help="Also print diagnostics that a source waiver covered, marked "
             "[waived: <reason>]; the exit code is unaffected",
    )
    lint_grp.add_argument(
        "--baseline",
        metavar="PATH",
        default=None,
        help="Report only findings that the baseline file PATH does not "
             "record (overrides [lint] baseline)",
    )
    lint_grp.add_argument(
        "--no-baseline",
        action="store_true",
        default=False,
        help="Ignore the configured baseline and report every finding",
    )
    lint_grp.add_argument(
        "--write-baseline",
        metavar="PATH",
        default=None,
        help="Record every lint finding of this run in the baseline file "
             "PATH and exit 0",
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
        cmd_explain,
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

    # -- Rule files ------------------------------------------------------
    #
    # The built-in ones, then [lint] rules, then --rules (pss-rules-format
    # §6.2); for --check-rules PATH..., the PATHs instead of the configured
    # ones.  Loaded before the configuration is checked against the
    # registry, since their rules join it (lint-core-plan C4.4): a selector,
    # a [severity] key, --describe and --explain may all name them.  A path
    # that does not exist is a usage error, like a missing FILE; problems
    # inside a rule file are diagnostics, reported with the run's.
    from . import rule_cmds
    from pssparser.lint import ruleview
    from pssparser.lint.rulefiles import RulePathError
    rule_entries = rule_cmds.configured_paths(cfg)
    if args.check_rules and args.files:
        rule_entries = rule_cmds.named_paths(args.files)
    try:
        rule_load = rule_cmds.load_rules(rule_entries, manager)
    except RulePathError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    manager.add_rule_view(
        ruleview.marker_defs(rule_load.engine.rules(), rule_load.refused),
        engine=rule_load.engine)

    try:
        config_mod.validate_against_registry(cfg, manager, engine=rule_load.engine,
                                             refused=rule_load.refused)
    except config_mod.ConfigError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    try:
        manager.validate_options(cfg.checker_options)
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    if args.show_config_for and not args.show_config:
        sys.stderr.write("error: --for FILE goes with --show-config\n")
        return 2
    if args.show_config:
        _report_load_issues(manager, sys.stderr)
        sys.stdout.write(config_mod.format_show_config(
            cfg, rule_sources=rule_cmds.rule_sources(rule_load),
            for_files=args.show_config_for or ()))
        return 0

    if args.rules_for:
        if not args.files:
            sys.stderr.write("error: --rules-for needs at least one FILE\n")
            return 2
        fmt = args.output_format or ("json" if args.json else "text")
        if fmt not in ("text", "json"):
            sys.stderr.write(f"error: --rules-for prints text or json, not {fmt}\n")
            return 2
        rule_cmds.report_problems(rule_load, sys.stderr)
        return rule_cmds.cmd_rules_for(args.files, cfg=cfg, manager=manager,
                                       output_format=fmt)

    # -- Query-and-exit flags (no source files needed) --------------------
    #
    # The query paths never build a DiagnosticCollection, so an extension that
    # failed to load has nowhere to be reported except stderr.  Print it
    # first: "this extension is missing" is the context that explains a
    # --list-checkers output with a checker absent from it.
    if (args.list_checkers or args.list_markers or args.list_extensions
            or args.describe is not None or args.explain is not None
            or args.describe_checker is not None):
        _report_load_issues(manager, sys.stderr)
        rule_cmds.report_problems(rule_load, sys.stderr)

    if args.list_checkers:
        return cmd_list_checkers(manager)

    if args.list_markers:
        return cmd_list_markers(manager)

    if args.list_extensions:
        return cmd_list_extensions(manager)

    if args.describe is not None:
        return cmd_describe(manager, args.describe)

    if args.explain is not None:
        return cmd_explain(manager, args.explain)

    if args.describe_checker is not None:
        return cmd_describe_checker(manager, args.describe_checker)

    output_format = args.output_format
    if args.json:
        if output_format not in (None, "json"):
            sys.stderr.write(
                f"error: --json conflicts with --format {output_format}\n")
            return 2
        output_format = "json"

    if args.check_rules:
        return rule_cmds.cmd_check_rules(
            args.files, cfg=cfg, manager=manager,
            output_format=output_format or "text", quiet=args.quiet,
            color=args.color, verbose=args.verbose, load=rule_load)

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

    write_baseline = args.write_baseline
    if write_baseline is not None and (
            write_baseline.endswith(".pss") or write_baseline in args.files):
        # `--write-baseline m.pss` most likely forgot the PATH; writing a
        # baseline over a source file would destroy it.
        sys.stderr.write(
            f"error: --write-baseline would overwrite the source file "
            f"{write_baseline}; give the baseline file's path, e.g. "
            f"--write-baseline lint-baseline.json\n")
        return 2
    if write_baseline is not None and (args.baseline or args.no_baseline):
        sys.stderr.write(
            "error: --write-baseline conflicts with --baseline and "
            "--no-baseline\n")
        return 2

    if args.verbose:
        rule_cmds.report_skipped(rule_load, sys.stderr)

    # The config layer already resolved CLI-versus-file precedence for every
    # warning setting, so the policy is written from `cfg`, not from `args`.
    policy = args.warning_policy or WarningPolicy()
    config_mod.to_warning_policy(cfg, policy)

    try:
        return cmd_parse(
            files=args.files,
            syntax_only=args.syntax_only,
            dump_ast=args.dump_ast,
            output_format=output_format or "text",
            statistics=args.statistics,
            show_waived=args.show_waived,
            baseline=None if write_baseline is not None else cfg.baseline,
            write_baseline=write_baseline,
            quiet=args.quiet,
            color=args.color,
            max_errors=args.max_errors,
            manager=manager,
            checkers=cfg.select,
            no_checkers=cfg.disable,
            warning_policy=policy,
            config=cfg,
            rule_load=rule_load,
            # --stats-no-timing implies --stats; it is a variant of it, not
            # a modifier that needs both flags spelled out.
            show_stats=args.stats or args.stats_no_timing,
            stats_timing=not args.stats_no_timing,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted\n")
        return 130
