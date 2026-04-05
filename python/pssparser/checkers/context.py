"""Context object passed to each checker's check() method."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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

    #: Internal – collected markers; use add_marker() to append.
    _markers: list = field(default_factory=list, repr=False)

    #: Internal – index of MarkerDef objects keyed by marker ID.
    #: Populated by CheckerManager before invoking any checker.
    _marker_index: Dict[str, Any] = field(default_factory=dict, repr=False)

    def add_marker(
        self,
        *,
        code: str,
        file: str,
        line: int,
        col: int,
        message: str,
        severity: Optional[str] = None,
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
        entry = {
            "severity": severity if severity is not None else self._lookup_severity(code),
            "message": f"[{code}] {message}",
            "file": file,
            "line": line,
            "col": col,
            "code": code,
        }
        self._markers.append(entry)

    def _lookup_severity(self, code: str) -> str:
        """Return the declared default severity for *code*."""
        md = self._marker_index.get(code)
        if md is not None:
            return md.severity
        return "error"  # safe fallback
