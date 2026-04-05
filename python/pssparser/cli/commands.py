"""Command implementations for the CLI."""
from __future__ import annotations

import json
import sys
from typing import List, Optional, TextIO

from .diagnostics import Diagnostic, DiagnosticCollection
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
    """
    from pssparser.parser import Parser, ParseException

    _stderr = stderr or sys.stderr
    _stdout = stdout or sys.stdout

    source_cache = SourceCache()
    coll = DiagnosticCollection(max_errors=max_errors)

    if use_json:
        driver = JsonOutput(stream=_stdout)
    else:
        driver = HumanOutput(source_cache, stream=_stderr, color=color)

    parser = Parser()
    linked_root = None

    # -- parse phase --------------------------------------------------------
    try:
        parser.parse(files)
    except ParseException as exc:
        _collect(coll, getattr(exc, "markers", []), parser)
        _emit_all(driver, coll, quiet)
        if not quiet:
            driver.summary(coll)
        return 1

    # -- link phase (unless --syntax-only) ----------------------------------
    if not syntax_only:
        try:
            linked_root = parser.link()
        except ParseException as exc:
            _collect(coll, getattr(exc, "markers", []), parser)
            _emit_all(driver, coll, quiet)
            if not quiet:
                driver.summary(coll)
            return 1

    # Collect any non-fatal markers from successful phases
    _collect(coll, [], parser)

    # -- checker phase ------------------------------------------------------
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

    # -- dump-ast -----------------------------------------------------------
    if dump_ast and linked_root is not None:
        try:
            _dump_ast_json(linked_root, dump_ast)
        except OSError as exc:
            _stderr.write(f"error: cannot write AST: {exc}\n")
            return 2

    # -- output diagnostics (warnings etc.) ---------------------------------
    _emit_all(driver, coll, quiet)
    if not quiet:
        driver.summary(coll)

    return 1 if coll.has_errors else 0


# -- helpers ----------------------------------------------------------------

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

    # Build per-file global scopes list (best-effort)
    global_scopes: list = []
    if hasattr(parser, "global_scopes"):
        global_scopes = list(parser.global_scopes)

    marker_index = manager.build_marker_index(active)

    context = CheckContext(
        root=linked_root,
        files=list(files),
        global_scopes=global_scopes,
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
            coll.add(Diagnostic.from_marker(m))


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
