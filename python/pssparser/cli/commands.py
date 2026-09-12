"""Command implementations for the CLI."""
from __future__ import annotations

import json
import re
import sys
import time
from typing import List, Optional, TextIO

from .diagnostics import Diagnostic, DiagnosticCollection, WarningPolicy
from .output import HumanOutput, JsonOutput
from .source_context import SourceCache


def cmd_parse(
    files: List[str],
    *,
    syntax_only: bool = False,
    dump_ast: Optional[str] = None,
    use_json: bool = False,
    quiet: bool = False,
    color: Optional[bool] = None,
    max_errors: int = 20,
    stderr: TextIO | None = None,
    stdout: TextIO | None = None,
    manager=None,
    checkers: Optional[List[str]] = None,
    no_checkers: Optional[List[str]] = None,
    warning_policy: Optional[WarningPolicy] = None,
    show_stats: bool = False,
    stats_timing: bool = True,
) -> int:
    """Run the parse (and optionally link) pipeline, report diagnostics.

    Returns an exit code: 0 success, 1 errors found, 2 usage problem.

    Parameters
    ----------
    manager:
        A pre-configured ``CheckerManager``.  When ``None``, a fresh manager
        is created and ``discover()`` is called automatically.
    checkers:
        Names of checkers to run (``--checker``).  ``None`` means run all.
    no_checkers:
        Names of checkers to exclude (``--no-checker``).
    warning_policy:
        ``-Werror`` / ``--no-warnings`` handling.  ``None`` means the
        default policy: warnings are reported as warnings.
    show_stats:
        Emit the ``--stats`` report.  Never affects the exit code and never
        suppresses a diagnostic.
    stats_timing:
        Include wall-clock timings in the stats report.  ``False``
        (``--stats-no-timing``) makes the output byte-stable, which is what
        makes it goldenable and safe to paste into documentation.
    """
    from pssparser.parser import Parser, ParseException

    _stderr = stderr or sys.stderr
    _stdout = stdout or sys.stdout
    policy = warning_policy or WarningPolicy()

    source_cache = SourceCache()
    coll = DiagnosticCollection()
    coll.set_processed_files(files)

    if use_json:
        driver = JsonOutput(stream=_stdout)
    else:
        driver = HumanOutput(source_cache, stream=_stderr, color=color)

    parser = Parser()
    parser.set_max_errors(max_errors)
    linked_root = None
    extra_timings: dict = {}

    def _finish(force_rc: Optional[int] = None) -> int:
        """Apply the warning policy, emit everything, return the exit code.

        The exit code is computed *after* promotion, so ``-Werror`` moves a
        clean-but-warning run from 0 to 1.
        """
        _apply_warning_policy(coll, policy)
        _emit_all(driver, coll, quiet)
        stats = None
        if show_stats:
            stats = _collect_stats(
                parser, files, coll,
                timings=extra_timings if stats_timing else None,
            )
        driver.finish(coll, quiet, stats)
        if force_rc is not None:
            return force_rc
        return 1 if coll.has_errors else 0

    # -- parse phase --------------------------------------------------------
    try:
        parser.parse(files)
    except ParseException as exc:
        _collect(coll, getattr(exc, "markers", []), parser)
        return _finish(force_rc=1)

    # -- link phase (unless --syntax-only) ----------------------------------
    if not syntax_only:
        t0 = time.perf_counter_ns()
        try:
            linked_root = parser.link()
        except ParseException as exc:
            extra_timings["link"] = time.perf_counter_ns() - t0
            _collect(coll, getattr(exc, "markers", []), parser)
            return _finish(force_rc=1)
        extra_timings["link"] = time.perf_counter_ns() - t0

    # Collect any non-fatal markers from successful phases
    _collect(coll, [], parser)

    # -- checker phase ------------------------------------------------------
    t0 = time.perf_counter_ns()
    _run_checkers(
        coll=coll,
        files=files,
        parser=parser,
        linked_root=linked_root,
        syntax_only=syntax_only,
        manager=manager,
        checkers=checkers,
        no_checkers=no_checkers,
    )
    extra_timings["checkers"] = time.perf_counter_ns() - t0

    # -- dump-ast -----------------------------------------------------------
    if dump_ast and linked_root is not None:
        try:
            _dump_ast_json(linked_root, dump_ast)
        except OSError as exc:
            _stderr.write(f"error: cannot write AST: {exc}\n")
            return 2

    # -- output diagnostics (warnings etc.) ---------------------------------
    return _finish()


# -- Core-marker code assignment -------------------------------------------

# Ordered list of (compiled-regex, PSS-code) pairs.  The first match wins.
_CORE_CODE_PATTERNS: list = []


def _build_core_patterns() -> list:
    """Compile and return the message-to-PSS-code pattern table.

    The table is derived from ``CoreChecker.marker_defs`` so that a marker's
    ID, severity, documentation, and message patterns are declared together in
    one record.  Patterns are tried in declaration order (i.e. ascending ID)
    and the first match wins; ``tests/python/test_marker_ids.py`` pins the
    resulting mapping so that a newly-added pattern cannot silently shadow an
    existing code.
    """
    from pssparser.checkers.core_checker import CoreChecker

    return [
        (re.compile(pat, re.IGNORECASE), mdef.id)
        for mdef in CoreChecker.marker_defs
        for pat in mdef.patterns
    ]


def _assign_core_code(marker: dict) -> dict:
    """Return a copy of *marker* with a ``'code'`` field set if absent.

    Uses message-pattern matching against the known C++ diagnostic strings to
    assign a ``PSS001``–``PSS005`` code.  Markers that already carry a
    ``'code'`` key are returned unchanged.
    """
    if marker.get("code"):
        return marker

    global _CORE_CODE_PATTERNS
    if not _CORE_CODE_PATTERNS:
        _CORE_CODE_PATTERNS = _build_core_patterns()

    msg = marker.get("message", "")
    for pattern, code in _CORE_CODE_PATTERNS:
        if pattern.search(msg):
            return {**marker, "code": code}

    return marker


# -- helpers ----------------------------------------------------------------

def _user_global_scopes(parser, files: List[str]) -> tuple:
    """Return ``(global_scopes, file_map)`` for the user's files only.

    ``Parser.parse`` prepends a synthesised standard-library unit, so anything
    that walks the tree -- checkers, ``--stats`` -- has to filter it out or
    report the same ~200 phantom types for every model.  Both consumers go
    through this one function so they cannot drift apart.

    Prefers the public snapshots, which survive ``link()``.  The private
    ``_files``/``_filenames`` are cleared by ``link()``, so reading them after
    a link yields an empty file_map and no global scopes -- exactly the two
    things the plug-in guide tells checkers to use.
    """
    file_map: dict = dict(getattr(parser, "file_map", {}) or {})

    user_files = set(files)
    global_scopes: list = []
    if hasattr(parser, "user_units"):
        global_scopes = [
            gs for gs in parser.user_units()
            if file_map.get(gs.getFileid(), "") in user_files
        ]

    if not global_scopes and hasattr(parser, "_files"):
        # --syntax-only never calls link(), so no snapshot was taken.
        filenames = getattr(parser, "_filenames", {}) or {}
        if not file_map:
            file_map = dict(filenames)
        global_scopes = [
            gs for gs in parser._files
            if filenames.get(gs.getFileid(), "") in user_files
        ]

    return global_scopes, file_map


def _run_checkers(
    coll: DiagnosticCollection,
    files: List[str],
    parser,
    linked_root,
    syntax_only: bool,
    manager,
    checkers,
    no_checkers,
) -> None:
    """Run the checker phase and merge results into *coll*."""
    from pssparser.checkers import CheckContext, CheckerManager

    if manager is None:
        manager = CheckerManager()
        manager.discover()

    try:
        active = manager.active(select=checkers, exclude=no_checkers)
    except ValueError as exc:
        import sys
        sys.stderr.write(f"error: {exc}\n")
        return

    if not active:
        return

    global_scopes, file_map = _user_global_scopes(parser, files)

    marker_index = manager.build_marker_index(active)

    context = CheckContext(
        root=linked_root,
        files=list(files),
        global_scopes=global_scopes,
        file_map=file_map,
        _marker_index=marker_index,
    )

    for checker in active:
        if not syntax_only or checker.runs_without_link:
            try:
                checker.check(context)
            except Exception as exc:
                import sys
                sys.stderr.write(
                    f"warning: checker {checker.name!r} raised an exception: {exc}\n"
                )

    for m in context._markers:
        coll.add(Diagnostic.from_marker(m))


def _collect(
    coll: DiagnosticCollection,
    exc_markers: list,
    parser,
) -> None:
    """Merge markers from an exception and from ``parser.markers``."""
    seen = set()
    for src in (exc_markers, parser.markers):
        for m in src:
            key = (m.get("file"), m.get("line"), m.get("col"), m.get("message"))
            if key in seen:
                continue
            seen.add(key)
            enriched = _assign_core_code(m)
            coll.add(Diagnostic.from_marker(enriched))


def _collect_stats(parser, files: List[str], coll: DiagnosticCollection,
                   timings: Optional[dict] = None):
    """Build the ``RunStats`` for a finished run.

    Called after the warning policy has been applied, so the code histogram
    describes the diagnostics the user actually saw.  ``timings`` is ``None``
    under ``--stats-no-timing``; the parser's own phase timings are merged in
    ahead of the caller's so the rows read in execution order.
    """
    from . import stats as stats_mod

    global_scopes, _ = _user_global_scopes(parser, files)

    run = stats_mod.RunStats(files=len(files))
    try:
        run.decls = stats_mod.collect_decls(global_scopes)
    except Exception as exc:  # pragma: no cover - defensive
        # Stats are a reporting nicety; never let them turn a successful
        # parse into a traceback.
        sys.stderr.write(f"warning: could not compute stats: {exc}\n")

    run.diagnostics_by_code = stats_mod.diagnostics_by_code(coll.diagnostics)

    if timings is not None:
        merged = dict(getattr(parser, "timings_ns", {}) or {})
        merged.update(timings)
        run.timings_ns = merged

    return run


def _apply_warning_policy(coll: DiagnosticCollection, policy: WarningPolicy) -> None:
    """Rewrite *coll* in place according to *policy*.

    Suppression runs before promotion, so ``--no-warnings -Werror`` reports
    nothing: there is no warning left to promote by the time promotion is
    considered.

    Note that ``--max-errors`` is *not* re-applied here.  The cap is enforced
    upstream in the C++ marker collector, long before promotion happens, so
    ``-Werror --max-errors 3`` can legitimately print more than three errors.
    See ``docs/cli.rst``.
    """
    if policy.is_default:
        return

    out: List[Diagnostic] = []
    for diag in coll.diagnostics:
        if policy.no_warnings and diag.severity == "warning":
            continue
        flag = policy.promotion_flag(diag)
        if flag is not None:
            diag.original_severity = diag.severity
            diag.severity = "error"
            diag.werror_flag = flag
        out.append(diag)

    coll.replace_diagnostics(out)


def _emit_all(driver, coll: DiagnosticCollection, quiet: bool) -> None:
    if quiet:
        return
    for diag in coll.diagnostics:
        driver.emit(diag)


def _dump_ast_json(root, path: str) -> None:
    """Serialise the linked RootSymbolScope to a JSON file.

    This is a best-effort tree walk; unknown node types are represented
    as their Python ``repr``.
    """
    def _walk(node, depth: int = 0):
        if node is None or depth > 64:
            return None
        info: dict = {"type": type(node).__name__}
        if hasattr(node, "getName"):
            n = node.getName()
            if hasattr(n, "getId"):
                info["name"] = n.getId()
            elif isinstance(n, str):
                info["name"] = n
        children = []
        if hasattr(node, "children"):
            for ch in node.children():
                c = _walk(ch, depth + 1)
                if c is not None:
                    children.append(c)
        if children:
            info["children"] = children
        return info

    tree = _walk(root)
    with open(path, "w") as fh:
        json.dump(tree, fh, indent=2)
        fh.write("\n")
