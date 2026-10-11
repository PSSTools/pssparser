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
from pssparser.parser import INTERNAL_ERROR_CODE

#: Exit status when pssparser reported an internal error (PSSP000).
EXIT_INTERNAL_ERROR = 3


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
    config=None,
    show_hints: Optional[bool] = None,
    output_format: Optional[str] = None,
    statistics: bool = False,
    show_waived: bool = False,
    baseline: Optional[str] = None,
    write_baseline: Optional[str] = None,
    rule_load=None,
) -> int:
    """Run the parse (and optionally link) pipeline, report diagnostics.

    Returns an exit code: 0 success, 1 errors found, 2 usage problem,
    3 internal error (a ``PSSP000`` was reported; it outranks 1).

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
    config:
        A ``cli.config.ResolvedConfig``, or ``None``.  Carries the severity
        map and per-checker options; ``checkers``/``no_checkers``/
        ``warning_policy`` above are already resolved from it by the caller.
        Also carries the lint selection; with no config the default profile
        applies.
    show_hints:
        Print ``hint`` diagnostics in text output.  ``None`` takes the
        config's ``[output] show-hints``.
    output_format:
        ``"text"``, ``"json"``, ``"sarif"`` or ``"github"``.  ``None`` means
        ``"json"`` when the deprecated *use_json* is set, else ``"text"``.
    statistics:
        Print a per-code count table (``--statistics``).
    show_waived:
        Print diagnostics that a source waiver covered (``--show-waived``),
        marked as waived; the exit code is unaffected.
    baseline:
        A baseline file (``--baseline`` / ``[lint] baseline``): findings it
        records are left out of the text output, the counts and the exit
        code.  A file that cannot be read is a usage error (2).
    write_baseline:
        Record this run's lint findings in this file (``--write-baseline``)
        instead.  Exits 0, unless the model has errors, which a baseline
        cannot record: then nothing is written and the exit code is 1.
    rule_load:
        The rule files loaded for this run
        (:class:`pssparser.lint.rulefiles.RuleLoad`), or ``None``.  Their
        diagnostics are reported with the run's; an error in a rule file
        makes the exit code 1.
    """
    from pssparser.parser import Parser, ParseException

    _stderr = stderr or sys.stderr
    _stdout = stdout or sys.stdout
    policy = warning_policy or WarningPolicy()

    source_cache = SourceCache()
    coll = DiagnosticCollection()
    coll.set_processed_files(files)

    # Extension-load problems are merged before parsing, not after, so that
    # the two early-return paths below (parse failure, link failure) still
    # report them.  "A checker never ran" is exactly the context a user needs
    # when reading a diagnostic list that came out shorter than expected.
    if manager is None:
        from pssparser.checkers import CheckerManager
        manager = CheckerManager()
        manager.discover()
    for load_marker in manager.load_diagnostics:
        coll.add(Diagnostic.from_marker(load_marker))
    if rule_load is not None:
        for marker in rule_load.diagnostics:
            coll.add(Diagnostic.from_marker(marker))
    if config is not None:
        from .config import alias_note_markers
        for note in alias_note_markers(config):
            coll.add(Diagnostic.from_marker(note))

    baseline_doc = None
    if baseline is not None:
        from pssparser.lint import baseline as baseline_mod
        try:
            baseline_doc = baseline_mod.load(
                baseline, aliases=_retired_aliases(manager))
        except baseline_mod.BaselineError as exc:
            _stderr.write(f"error: {exc}\n")
            return 2

    if show_hints is None:
        show_hints = bool(getattr(config, "show_hints", False))
    if output_format is None:
        output_format = "json" if use_json else "text"
    lint_enabled, lint_ids = _lint_selection(config, manager)
    lint_dropped = 0
    catalog = {md.id: md for md in manager.all_marker_defs()}
    if output_format == "json":
        driver = JsonOutput(stream=_stdout, catalog=catalog,
                            statistics=statistics)
    elif output_format == "sarif":
        from .sarif import SarifOutput
        driver = SarifOutput(stream=_stdout, catalog=catalog,
                             enabled_rules=sorted(lint_enabled))
    elif output_format == "github":
        from .github import GithubOutput
        driver = GithubOutput(stream=_stdout)
    else:
        driver = HumanOutput(source_cache, stream=_stderr, color=color,
                             show_hints=show_hints, statistics=statistics,
                             catalog=catalog, show_waived=show_waived)

    parser = Parser()
    parser.set_max_errors(max_errors)
    linked_root = None
    extra_timings: dict = {}
    # What the waiver pass may rely on: whether the AST exists (annotation
    # waivers need it), and which rules ran (the unused-waiver marker needs
    # that; unknown on a failed parse or link).
    waiver_state: dict = {"ast": False, "ran": None}

    def _finish(force_rc: Optional[int] = None) -> int:
        """Apply the warning policy, emit everything, return the exit code.

        The exit code is computed *after* promotion, so ``-Werror`` moves a
        clean-but-warning run from 0 to 1.
        """
        nonlocal lint_dropped
        # Lint selection first: a rule the profile does not enable, or a
        # finding outside the user's own files, is not a diagnostic at all.
        lint_dropped = coll.apply_lint_selection(
            lint_enabled, lint_ids, owned=_owned_files(files))
        # Severity overrides next: they decide what a diagnostic *is*, and
        # the warning policy then decides what to do with warnings.  Running
        # them the other way round would let -Werror promote a diagnostic
        # the config had already turned off.
        if config is not None:
            coll.apply_severity_map(config.severity)
        # Waivers after the severity map, so a waiver covers a rule the
        # config promoted, and before the warning policy, so -Werror never
        # promotes a waived diagnostic (docs/waivers.rst).
        if config is None or getattr(config, "source_waivers", True):
            _apply_waivers(coll, parser, files, manager, config,
                           ast=waiver_state["ast"], ran=waiver_state["ran"])
        # The baseline after waivers (a waived finding is not recorded) and
        # before the warning policy, so -Werror never promotes a finding the
        # baseline accepted.
        index = None
        if waiver_state["ast"] and (
                output_format == "sarif" or baseline_doc is not None
                or write_baseline is not None):
            from pssparser.lint.declpath import index_for
            index = index_for(parser, files)
        if (output_format == "sarif" or baseline_doc is not None
                or write_baseline is not None):
            _assign_fingerprints(coll, index)
        written = None
        write_error = None
        if write_baseline is not None:
            written, write_error = _write_baseline(
                coll, write_baseline, manager, config)
            if write_error is not None:
                force_rc = 1
        elif baseline_doc is not None:
            _apply_baseline(coll, baseline_doc, manager, config, files,
                            ran=waiver_state["ran"])
        _apply_warning_policy(coll, policy)
        if output_format == "sarif" and index is not None:
            _assign_decl_paths(coll, index)
        _emit_all(driver, coll, quiet)
        stats = None
        if show_stats:
            stats = _collect_stats(
                parser, files, coll,
                timings=extra_timings if stats_timing else None,
            )
            stats.lint_dropped = lint_dropped
            stats.waived_by_code = _by_code(coll.waived)
            stats.baselined_by_code = _by_code(coll.baselined)
        driver.finish(coll, quiet, stats)
        # After the diagnostics, so the last line says what happened.
        if write_error is not None:
            _stderr.write(f"error: {write_error}\n")
        elif written is not None:
            n = written.total()
            _stderr.write(
                f"pssparser: recorded {n} finding{'s' if n != 1 else ''} "
                f"in {write_baseline}\n")
            if force_rc is None:
                force_rc = 0
        # An internal error outranks everything else: whatever else was
        # reported, the run is not trustworthy, and a script must be able to
        # tell "the model is wrong" (1) from "the tool is wrong" (3).
        if any(d.code == INTERNAL_ERROR_CODE for d in coll.diagnostics):
            return EXIT_INTERNAL_ERROR
        if force_rc is not None:
            return force_rc
        return 1 if coll.has_errors else 0

    # -- parse phase --------------------------------------------------------
    try:
        parser.parse(files)
    except ParseException as exc:
        _collect(coll, getattr(exc, "markers", []), parser)
        return _finish(force_rc=1)

    # The AST exists once the parse succeeded, linked or not: a waiver
    # annotation is recognised by its spelled name, so it needs no link.
    waiver_state["ast"] = True

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
    active = _run_checkers(
        coll=coll,
        files=files,
        parser=parser,
        linked_root=linked_root,
        syntax_only=syntax_only,
        manager=manager,
        checkers=checkers,
        no_checkers=no_checkers,
        options=None if config is None else config.checker_options,
        disabled=_disabled_codes(config, lint_enabled, lint_ids),
    )
    extra_timings["checkers"] = time.perf_counter_ns() - t0
    if not syntax_only:
        waiver_state["ran"] = _codes_that_ran(
            manager, active, config, lint_enabled, lint_ids)

    # -- dump-ast -----------------------------------------------------------
    if dump_ast and linked_root is not None:
        try:
            _dump_ast_json(linked_root, dump_ast)
        except OSError as exc:
            _stderr.write(f"error: cannot write AST: {exc}\n")
            return 2

    # -- output diagnostics (warnings etc.) ---------------------------------
    return _finish()


# -- Lint selection -----------------------------------------------------------

def _lint_selection(config, manager) -> tuple:
    """``(enabled_ids, lint_ids)`` for this run.

    The config layer resolves the selection once the registry is loaded;
    a caller that passes no config (the library path, most tests) gets the
    default profile.
    """
    enabled = getattr(config, "lint_enabled", None)
    if enabled is not None:
        return set(enabled), set(config.lint_ids)
    from pssparser.checkers import taxonomy
    from pssparser.checkers.selectors import RuleSet

    rules = RuleSet(manager.all_marker_defs())
    return rules.resolve(taxonomy.DEFAULT_PROFILE), {md.id for md in rules.lint}


def _disabled_codes(config, lint_enabled: set, lint_ids: set) -> frozenset:
    """Codes that must not run: ``off`` in ``[severity]``, or lint rules the
    selection leaves out."""
    off = {code for code, sev in (getattr(config, "severity", None) or {}).items()
           if sev == "off"}
    return frozenset(off | (lint_ids - lint_enabled))


def _owned_files(files: List[str]) -> set:
    """Real paths of the files whose lint findings are reported.

    Today that is exactly the files on the command line: the CLI parses no
    other user file (no search path), so this excludes only the built-in
    standard library.
    """
    import os

    return {os.path.realpath(f) for f in files}


# -- Core-marker code assignment -------------------------------------------

# Ordered list of (compiled-regex, code) pairs.  The first match wins.
_CORE_CODE_PATTERNS: list = []


def _build_core_patterns() -> list:
    """Compile and return the message-to-code pattern table.

    The table is derived from ``CoreChecker.marker_defs`` so that a marker's
    ID, severity, documentation, and message patterns are declared together in
    one record.  Patterns are tried in declaration order (i.e. ascending ID)
    and the first match wins; ``tests/python/test_marker_ids.py`` pins the
    resulting mapping so that a newly-added pattern cannot silently shadow an
    existing code.

    A code that moved namespace (``PSS104`` -> ``LINT601``) is tried at the
    position of its retired row, under its new ID, so moving a code never
    changes which pattern wins.
    """
    from pssparser.checkers.core_checker import CoreChecker

    defs = CoreChecker.marker_defs
    by_id = {mdef.id: mdef for mdef in defs}
    moved = {
        mdef.replaced_by[0] for mdef in defs
        if mdef.status == "retired" and mdef.replaced_by
        and mdef.replaced_by[0] in by_id
    }
    order = []
    for mdef in defs:
        if mdef.status == "retired":
            if mdef.replaced_by and mdef.replaced_by[0] in by_id:
                order.append(by_id[mdef.replaced_by[0]])
        elif mdef.id not in moved:
            order.append(mdef)
    return [
        (re.compile(pat, re.IGNORECASE), mdef.id)
        for mdef in order
        for pat in mdef.patterns
    ]


_MOVED_CODES: Optional[dict] = None


def _moved_codes() -> dict:
    """``{retired_code: current_code}`` for core codes that moved."""
    global _MOVED_CODES
    if _MOVED_CODES is None:
        from pssparser.checkers.core_checker import CoreChecker
        _MOVED_CODES = {
            mdef.id: mdef.replaced_by[0] for mdef in CoreChecker.marker_defs
            if mdef.status == "retired" and mdef.replaced_by
        }
    return _MOVED_CODES


def _assign_core_code(marker: dict) -> dict:
    """Return a copy of *marker* with a ``'code'`` field set if absent.

    Uses message-pattern matching against the known C++ diagnostic strings to
    assign a core code (``PSS``, or ``LINT``/``PSSP`` for the warnings that
    moved).  Markers that already carry a
    ``'code'`` key are returned unchanged.
    """
    code = marker.get("code")
    if code:
        # A code set in C++ that has since moved namespace is reported
        # under its current ID; the retired one never reaches output.
        current = _moved_codes().get(code)
        return {**marker, "code": current} if current else marker

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
    options=None,
    disabled: frozenset = frozenset(),
) -> None:
    """Run the checker phase and merge results into *coll*."""
    from pssparser.checkers import CheckContext, CheckerManager

    if manager is None:
        manager = CheckerManager()
        manager.discover()

    try:
        active = manager.active(
            select=checkers, exclude=no_checkers, options=options,
            disabled=disabled,
        )
    except ValueError as exc:
        import sys
        sys.stderr.write(f"error: {exc}\n")
        return []

    if not active:
        return []

    global_scopes, file_map = _user_global_scopes(parser, files)

    marker_index = manager.build_marker_index(active)

    context = CheckContext(
        root=linked_root,
        files=list(files),
        global_scopes=global_scopes,
        file_map=file_map,
        _marker_index=marker_index,
        _disabled=disabled,
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
    return active


# -- Source waivers ------------------------------------------------------------

def _codes_that_ran(manager, active, config, lint_enabled: set, lint_ids: set) -> set:
    """Codes whose rule ran: the core's (the link ran), the active checkers',
    and the lint rules the selection enabled -- less any ``off``.

    The unused-waiver marker (PSSP202) fires only for a waiver naming one of
    these, so a waiver for a rule turned off here is not "unused".
    """
    from pssparser.checkers.core_checker import CoreChecker

    ran = {md.id for md in CoreChecker.marker_defs if md.status == "active"}
    for checker in active or []:
        ran |= {md.id for md in getattr(checker, "marker_defs", ())}
    ran -= (lint_ids - lint_enabled)
    off = {c for c, sev in (getattr(config, "severity", None) or {}).items()
           if sev == "off"}
    return ran - off


def _apply_waivers(coll: DiagnosticCollection, parser, files: List[str],
                   manager, config, *, ast: bool, ran) -> None:
    """Remove waived diagnostics from *coll*, record them in ``coll.waived``,
    and add the waiver hygiene diagnostics."""
    from pssparser import waivers as waivers_mod
    from pssparser.checkers.selectors import RuleSet, _is_core_error

    try:
        found = waivers_mod.collect(parser if ast else None, files)
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write(f"warning: could not read source waivers: {exc}\n")
        return
    if not found:
        return

    mdefs = list(manager.all_marker_defs())
    catalog = {md.id: md for md in mdefs}
    aliases = {md.id: md.replaced_by[0] for md in mdefs
               if md.status == "retired" and md.replaced_by}

    def is_core_error(code: str) -> bool:
        md = catalog.get(code)
        return md is not None and _is_core_error(md)

    result = waivers_mod.apply(
        coll.diagnostics, found, rules=RuleSet(mdefs),
        is_core_error=is_core_error, ran=ran, aliases=aliases)
    coll.replace_diagnostics(result.kept)
    for diag, waiver in result.waived:
        diag.waiver = waiver.to_json()
    coll.waived = [diag for diag, _ in result.waived]

    severity = (getattr(config, "severity", None) or {})
    for marker in result.markers:
        sev = severity.get(marker["code"])
        if sev == "off":
            continue
        diag = Diagnostic.from_marker(marker)
        if sev:
            diag.severity = sev
        coll.add(diag)


def _assign_decl_paths(coll: DiagnosticCollection, index) -> None:
    """Set each diagnostic's enclosing declaration (SARIF logical location)."""
    for diag in list(coll.diagnostics) + list(coll.waived) + list(coll.baselined):
        if diag.line < 1:
            continue
        scope = index.scope_at(diag.file, diag.line, diag.col)
        if scope is not None:
            diag.decl = {"path": scope.path, "name": scope.name,
                         "kind": scope.kind}


# -- Baselines -----------------------------------------------------------------

def _retired_aliases(manager) -> dict:
    """``{retired_id: successor}`` across every loaded marker definition."""
    return {md.id: md.replaced_by[0] for md in manager.all_marker_defs()
            if md.status == "retired" and md.replaced_by}


def _baseline_eligible(manager):
    """A predicate: may a baseline record or match this diagnostic?"""
    from pssparser.lint import baseline as baseline_mod
    from pssparser.checkers.selectors import _is_core_error

    catalog = {md.id: md for md in manager.all_marker_defs()}

    def is_core_error(code: str) -> bool:
        md = catalog.get(code)
        return md is not None and _is_core_error(md)

    return lambda d: baseline_mod.eligible(d, is_core_error)


def _assign_fingerprints(coll: DiagnosticCollection, index) -> None:
    from pssparser.lint.fingerprint import Fingerprinter, assign

    fp = Fingerprinter(index)
    assign(list(coll.diagnostics) + list(coll.waived), fp)


def _write_baseline(coll: DiagnosticCollection, path: str, manager,
                    config) -> tuple:
    """Record the run's eligible findings in *path*.

    Returns ``(baseline, None)``, or ``(None, message)`` when nothing was
    written: the model has errors, or the file cannot be written.
    """
    from pssparser.lint import baseline as baseline_mod

    eligible = _baseline_eligible(manager)
    recorded = [d for d in coll.diagnostics if eligible(d)]
    if any(d.severity == "error" and not eligible(d) for d in coll.diagnostics):
        return None, (
            f"not writing the baseline {path}: the model has errors, and a "
            "baseline records lint findings, not errors; fix the errors "
            "first")
    doc = baseline_mod.build(
        path, recorded, rules_version=getattr(config, "rules_version", "") or None)
    try:
        baseline_mod.write(doc)
    except OSError as exc:
        return None, f"cannot write the baseline {path}: {exc}"
    keep = set(map(id, recorded))
    coll.replace_diagnostics([d for d in coll.diagnostics if id(d) not in keep])
    coll.baselined = recorded
    return doc, None


def _apply_baseline(coll: DiagnosticCollection, doc, manager, config,
                    files: List[str], *, ran) -> None:
    """Move the findings *doc* records out of *coll*, and report its stale
    entries (PSSP206)."""
    import os
    from pssparser.lint import baseline as baseline_mod

    eligible = _baseline_eligible(manager)
    owned = _owned_files(files)

    def checked(entry) -> bool:
        # An entry can be stale only if this run could have reported it:
        # its file was checked and its rule ran.
        if ran is None or entry.code not in ran:
            return False
        path = os.path.realpath(os.path.join(doc.directory, entry.file))
        return path in owned

    result = baseline_mod.match(coll.diagnostics, doc, is_eligible=eligible,
                                checked=checked)
    for d in result.new:
        if eligible(d):
            d.baseline_state = "new"
    for d in result.baselined:
        d.baseline_state = "unchanged"
    coll.replace_diagnostics(result.new)
    coll.baselined = result.baselined

    severity = (getattr(config, "severity", None) or {})
    sev = severity.get("PSSP206")
    if sev == "off":
        return
    if result.stale:
        coll.non_source_files.add(doc.path)
    for entry, missing in result.stale:
        if missing == entry.count:
            what = ("its finding is" if entry.count == 1
                    else f"all {entry.count} of its findings are")
        else:
            what = f"{missing} of its {entry.count} findings are"
        diag = Diagnostic.from_marker({
            "severity": sev or "info",
            "code": "PSSP206",
            "file": doc.path,
            "line": entry.line,
            "col": 1,
            "message": (f"[PSSP206] stale baseline entry: {what} no longer "
                        f"reported ({entry.code} in {entry.file}); rewrite "
                        "the baseline with --write-baseline"),
        })
        coll.add(diag)


def _by_code(diags) -> dict:
    counts: dict = {}
    for d in diags:
        key = d.code or "<uncoded>"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


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
