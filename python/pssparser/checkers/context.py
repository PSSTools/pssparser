"""Context object passed to each checker's check() method."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

RelatedLocation = Dict[str, Any]


@dataclass
class CheckContext:
    """Provides AST access and a diagnostic-emission API to checkers.

    Attributes
    ----------
    root:
        Fully-linked root symbol scope, or ``None`` when ``--syntax-only``.
    files:
        Ordered list of source file paths that were parsed.
    global_scopes:
        Raw per-file ``GlobalScope`` AST nodes (same order as *files*).
    """

    #: Fully-linked root symbol scope, or None when --syntax-only.
    root: Optional[Any]

    #: Ordered list of source file paths that were parsed.
    files: List[str]

    #: Raw per-file GlobalScope AST nodes (same order as *files*).
    global_scopes: List[Any]

    #: Maps fileid (int) -> source file path; allows checkers to resolve
    #: GlobalScope.getFileid() to a human-readable path when getFilename()
    #: is unavailable.
    file_map: Dict[int, str] = field(default_factory=dict)

    #: Internal – collected markers; use add_marker() to append.
    _markers: list = field(default_factory=list, repr=False)

    #: Internal – index of MarkerDef objects keyed by marker ID.
    #: Populated by CheckerManager before invoking any checker.
    _marker_index: Dict[str, Any] = field(default_factory=dict, repr=False)

    #: Internal – codes turned off for this run, by ``[severity] = "off"``
    #: or by lint selection.  Read through :meth:`is_enabled`.
    _disabled: frozenset = field(default_factory=frozenset, repr=False)

    #: Internal – errors from parse, link and the semantic checks: when
    #: non-zero, the declarative rules do not run (the lint gate, L8.1).
    _gate_errors: int = field(default=0, repr=False)

    #: Internal – ``[lint.rule.<name>]`` option values, by rule ID.
    _lint_options: Dict[str, dict] = field(default_factory=dict, repr=False)

    #: Per-rule counts from the declarative rules' run, for ``--stats``:
    #: ``[{"id", "matches", "findings", "steps", "ns", "errors"}]``.
    lint_stats: List[dict] = field(default_factory=list, repr=False)

    #: Internal – built on first use of :attr:`facts`.
    _facts: Optional["Facts"] = field(default=None, repr=False)

    @property
    def facts(self) -> "Facts":
        """Derived, cached facts about the model (see :class:`Facts`)."""
        if self._facts is None:
            self._facts = Facts(self)
        return self._facts

    def is_enabled(self, code: str) -> bool:
        """False when *code* is turned off for this run.

        A checker with several rules can skip the work for a disabled one.
        Checking is optional: :meth:`add_marker` drops a disabled code
        anyway, so a checker that never asks is still correct, only slower.
        """
        return code not in self._disabled

    def add_marker(
        self,
        *,
        code: str,
        file: str,
        line: int,
        col: int,
        message: str,
        severity: Optional[str] = None,
        extent: int = 0,
        related: Optional[List[RelatedLocation]] = None,
    ) -> None:
        """Emit one diagnostic from within a checker.

        Parameters
        ----------
        code:
            The ``MarkerDef.id`` for this diagnostic.  Must be declared in
            the checker's ``marker_defs`` list (enforced via
            ``_marker_index``).
        file:
            Source file path.
        line:
            1-based line number.
        col:
            1-based column number.
        message:
            Human-readable diagnostic text.
        severity:
            Override the default severity declared in the ``MarkerDef``.
            If omitted, the ``MarkerDef.severity`` is used.
        extent:
            Length in characters of the primary span, so the CLI can
            underline the whole offending token/name instead of one column.
            Defaults to 0 (unknown).
        related:
            Secondary locations relevant to the diagnostic — e.g. the
            declaration a duplicate collides with, or the opener of an
            unclosed scope. Each entry is a dict with keys ``file``,
            ``line``, ``col``, and ``label`` (the note text shown under that
            location). Defaults to none.

        Raises
        ------
        ValueError
            If *code* is not present in ``_marker_index``.
        """
        if code not in self._marker_index:
            raise ValueError(
                f"Unknown marker code {code!r}; it must be declared in a "
                "checker's marker_defs before it can be emitted."
            )
        if code in self._disabled:
            return
        entry = {
            "severity": severity if severity is not None else self._lookup_severity(code),
            "message": f"[{code}] {message}",
            "file": file,
            "line": line,
            "col": col,
            "code": code,
            "extent": extent,
            "related": related if related is not None else [],
        }
        self._markers.append(entry)

    def _lookup_severity(self, code: str) -> str:
        """Return the declared default severity for *code*."""
        md = self._marker_index.get(code)
        if md is not None:
            return md.severity
        return "error"  # safe fallback


class Facts:
    """Facts derived from the AST on demand and cached for the run.

    Each is computed the first time a checker asks, so a run whose checkers
    never ask pays nothing.
    """

    def __init__(self, ctx: CheckContext):
        self._ctx = ctx
        self._decl_paths = None

    @property
    def decl_paths(self):
        """The :class:`pssparser.lint.declpath.DeclPathIndex` for the run."""
        if self._decl_paths is None:
            from pssparser.lint.declpath import DeclPathIndex
            self._decl_paths = DeclPathIndex(self._ctx.global_scopes,
                                             self._ctx.file_map)
        return self._decl_paths

    def decl_path(self, loc) -> str:
        """The qualified path of the declaration enclosing *loc*, e.g.
        ``pkg::C::A::constraint c``; ``""`` at global scope.

        *loc* is a marker dict, anything with ``file``/``line``/``col``
        attributes, or a ``(file, line, col)`` tuple.
        """
        from pssparser.lint.declpath import location_of
        return self.decl_paths.path_at(*location_of(loc))
