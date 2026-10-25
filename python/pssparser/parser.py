import time
from io import StringIO
from typing import Dict, List, NamedTuple, Optional, Tuple, TextIO

#: The marker ID of an internal error -- a defect in pssparser, not in the
#: model (symbol-resolution-plan.md INV-1). Kept in step with
#: INTERNAL_ERROR_ID in src/include/pssp/impl/InternalError.h.
INTERNAL_ERROR_CODE = "PSSP000"


def _no_file() -> str:
    from pssparser.checkers.extension import NO_FILE
    return NO_FILE


def _internal_error_marker(phase: str, exc: BaseException,
                           filename: Optional[str] = None) -> dict:
    """A PSSP000 marker dict for a C++ exception that reached Python."""
    return {
        "severity": "error",
        "message": "internal error %s: %s; please report this" % (phase, exc),
        "file": filename if filename is not None else _no_file(),
        "line": 0 if filename is not None else -1,
        "col": 0 if filename is not None else -1,
        "extent": 0,
        "related": [],
        "code": INTERNAL_ERROR_CODE,
    }


#: The display path of the core library's files: ``<stdlib>/std_pkg.pss``.
STDLIB_PREFIX = "<stdlib>/"

_core_library_sources = None


def core_library_sources() -> List[Tuple[str, int, int, str]]:
    """The compiled-in core library's files, in the order they are built into
    fileid 0: ``(name, first_line, num_lines, text)`` for each.

    The core library is one source unit, fileid 0, and each file occupies its
    own band of its lines; :func:`core_library_location` maps a line back.
    """
    global _core_library_sources
    if _core_library_sources is None:
        import pssparser.core as zspp
        _core_library_sources = zspp.Factory.inst().getCoreLibrarySources()
    return _core_library_sources


def core_library_location(line: int) -> Optional[Tuple[str, int]]:
    """``(path, line)`` within its own file for a fileid-0 ``line``, such as
    ``("<stdlib>/addr_reg_pkg.pss", 12)``; None for a line in no file."""
    for name, first, num, _ in core_library_sources():
        if first <= line < first + num:
            return (STDLIB_PREFIX + name, line - first + 1)
    return None


class InactiveRegion(NamedTuple):
    """A source region left out by `compile if`; see
    :meth:`Parser.inactive_regions`. Both ends inclusive, 1-based."""
    fileid: int
    start_line: int
    start_col: int
    end_line: int
    end_col: int


class ParseException(Exception):
    def __init__(self, message, markers=None):
        super().__init__(message)
        self.markers = markers or []

class Parser(object):
    """Parse and link PSS sources.

    A thin wrapper over the core's parse-and-link session
    (``pssp::IParserSession``; core-in-leaf-plan.md CF1). The session keeps
    the units, the linked root and the file names, loads the core library,
    turns an escaped C++ exception into a PSSP000 marker, and resolves and
    sorts markers. What is left here is reading files and the Python shape of
    the results.
    """

    def __init__(
            self,
            collect_docstrings : bool = False,
            collect_comments : bool = False):
        """Build a parser.

        :param collect_docstrings: collect doc comments and attach them to the
            declarations they document, reachable as ``getDocstring()`` on any
            ``ScopeChild``.
        :param collect_comments: capture *every* comment, on statements as
            well as declarations, as ``ScopeChild.comments``. Implies
            ``collect_docstrings``.

        Both default off: collection costs time and memory that a consumer
        which never reads a comment should not pay.
        """
        import pssparser.core as zspp
        import pssparser.ast as zsp_ast
        self.ast_f = zsp_ast.Factory.inst()
        self.parser_f = zspp.Factory.inst()
        self._session = self.parser_f.mkParserSession()
        self._session.setCollectDocstrings(collect_docstrings)
        self._session.setCollectComments(collect_comments)
        #: The linked root. It owns the units; the session holds it borrowed,
        #: so it must live as long as the session does.
        self._root = None
        self._markers = []
        self._collect_docstrings = collect_docstrings
        self._collect_comments = collect_comments
        #: Phase name -> nanoseconds, accumulated across parse() calls. Read
        #: by the CLI's --stats. Kept here rather than in the CLI because the
        #: standard-library load happens inside parse() and is invisible from
        #: outside -- reporting it as part of the user's parse time would be a
        #: lie the number gets quoted for.
        self._timings_ns : Dict[str,int] = {}

    def _add_timing(self, phase: str, ns: int) -> None:
        self._timings_ns[phase] = self._timings_ns.get(phase, 0) + ns

    @property
    def timings_ns(self) -> Dict[str,int]:
        """Nanoseconds spent per internal phase, accumulated across calls."""
        return dict(self._timings_ns)

    def set_max_errors(self, max_errors: int) -> None:
        """Stop reporting further errors for a file after ``max_errors``.

        ``0`` (the default) means unlimited. Applies to every parse and link
        from this point on. Only error-severity markers count against the cap;
        a file that hits it gets one extra PSSP007 marker announcing the
        cutoff.
        """
        self._session.setMaxErrors(max_errors)

    @property
    def _files(self) -> List['zsp_ast.GlobalScope']:
        """The units parsed since the last link(), core library first.
        Borrowed: the session owns them, and link() hands them to the root."""
        return self._session.units()

    @property
    def _filenames(self) -> Dict[int, str]:
        """fileid -> name of the sources parsed since the last link()."""
        return self._session.sourceNames()

    def _begin(self) -> None:
        """Open a parse call; the first one loads the core library."""
        self._markers = []
        self._session.clearMarkers()
        first = self._session.nextFileid() == 0
        t0 = time.perf_counter_ns()
        self._session.beginParse()
        if first:
            self._add_timing("stdlib", time.perf_counter_ns() - t0)

    def _parse_one(self, name: str, text: str) -> None:
        if not self._session.parseSource(name, text):
            self._markers = self._session.markers()
            raise ParseException(self._mkErrorMessage(), self._markers)

    def parse(self, files : List[str]) -> bool:
        self._begin()
        for f in files:
            # One span for reading and parsing, under a name that says so.
            t0 = time.perf_counter_ns()
            with open(f, "r") as fp:
                text = fp.read()
            self._parse_one(f, text)
            self._add_timing("parse (incl. read)", time.perf_counter_ns() - t0)
        self._markers = self._session.markers()
        return True

    def parses(self, files : List[Tuple[str, str]]) -> bool:
        self._begin()
        for fname, fstr in files:
            self._parse_one(fname, fstr)
        self._markers = self._session.markers()
        return True

    def enable_profiling(self, enable: bool = True):
        """Enable or disable ANTLR profiling for subsequent parse operations."""
        self._session.setEnableProfiling(enable)

    def get_profile_info(self):
        """Get profiling information from the last parse operation.

        Returns ParseProfileInfo object with decision-level and aggregate
        metrics, or None if profiling was not enabled, nothing has been
        parsed, or :meth:`link` has run (it drops the builder that holds the
        profile).
        """
        return self._session.profileInfo()

    def link(self) -> 'zsp_ast.RootSymbolScope':
        """Link every unit parsed so far and return the linked root.

        Raises ParseException if the link produces an error-severity marker,
        after recording the root: a caught exception still leaves ``root``,
        :meth:`user_units` and :attr:`file_map` usable. What it does not leave
        is a trustworthy cross-file view -- type references may be unresolved,
        which is what the error was about.

        Parse-time markers are kept, and link-time ones merged in.
        """
        ok = self._session.link()
        # The session keeps a borrowed pointer; this wrapper owns the root,
        # and with it the units.
        self._root = self._session.releaseRoot()
        self._markers = self._session.markers()
        if not ok:
            raise ParseException(self._mkErrorMessage(), self._markers)
        return self._root

    @property
    def collect_docstrings(self) -> bool:
        """Whether doc comments are collected. Set via the constructor."""
        return self._collect_docstrings

    @property
    def collect_comments(self) -> bool:
        """Whether every comment is collected. Set via the constructor."""
        return self._collect_comments

    @property
    def file_map(self) -> Dict[int, str]:
        """Map fileid -> source path for the user-supplied files.

        Populated by :meth:`link` and valid afterwards. Built-in and library
        units are excluded: they carry fileid 0 or -1 and have no user path.
        Use :meth:`resolve_location` for a path and line that covers the core
        library (fileid 0) too.
        """
        return self._session.fileMap()

    def user_units(self) -> List['zsp_ast.GlobalScope']:
        """The GlobalScope of each user-supplied file, in parse order.

        Read from the linked root, which owns the units after :meth:`link`.
        Built-in and standard-library units are filtered out by fileid.

        Returns an empty list before :meth:`link` has run.
        """
        return self._session.userUnits()

    def inactive_regions(self) -> List['InactiveRegion']:
        """The source regions a `compile if` left out, in the user files.

        One region per branch that was not elaborated -- the `if` branch when
        the condition is false, the `else` branch when it is true, and both
        when the condition could not be evaluated (already an error). A
        region runs from the branch's first token to its last, inclusive
        (``{`` to ``}`` for a braced branch); the ``else`` keyword is not
        part of it. A `compile if` nested inside a region is covered by it and
        not reported separately. Lines and columns are 1-based, as in
        ``Location``. Sorted by position.

        Names inside a region are not in the AST and are not linked. The
        condition's own names are: see ``pssparser.refs.occurrences()``.

        Returns an empty list before :meth:`link` has run.
        """
        return [InactiveRegion(*r) for r in self._session.inactiveRegions()]

    def resolve_location(self, fileid: int, line: int) -> Tuple[str, int]:
        """The display ``(path, line)`` of a location, from its fileid and line.

        A user file's line is its own. The core library is a single unit,
        fileid 0, whose line is mapped to the library file it falls in:
        ``("<stdlib>/addr_reg_pkg.pss", 12)``. Fileid -1, the types the core
        synthesises, is ``<builtin>``.
        """
        return self._session.resolveLocation(fileid, line)

    def _mkErrorMessage(self) -> str:
        """The last call's markers, one per line, for ParseException."""
        prefix = {
            "error": "Error: ",
            "warning": "Warning: ",
            "info": "Info: ",
            "hint": "Hint: ",
        }
        msg = ""
        for m in self._session.callMarkers():
            msg += "%s%s %s:%d:%d\n" % (
                prefix.get(m["severity"], ""),
                m["message"],
                m["file"],
                m["line"],
                m["col"])
        return msg

    @property
    def markers(self) -> list:
        """Structured list of markers from the last parse/link operation,
        sorted by (file, line, col). A parse call starts the list afresh; a
        link adds its markers to the parse's.

        Each marker is a dict with keys:
            severity: "error", "warning", "info", or "hint"
            message: Human-readable error message
            file: Source filename
            line: Line number (1-based)
            col: Column number (1-based)
            extent: Length in characters of the primary span (0 if unknown)
            related: list of {file, line, col, label} secondary locations
            fix: {file, line, col, extent, replacement} machine-applicable
                 repair; absent when the builder has no complete one to offer
            code: stable marker ID (e.g. "PSS020"); absent if not yet assigned
                  by the emitting checker/builder
        """
        return list(self._markers)

    @property
    def root(self) -> 'zsp_ast.RootSymbolScope':
        return self._root
