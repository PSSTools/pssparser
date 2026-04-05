"""CheckerManager: discovery, filtering, loading, and invocation of checkers."""
from __future__ import annotations

import importlib
from typing import Dict, List, Optional, Type

from .base import CheckerBase


class CheckerManager:
    """Manages discovery, filtering, and invocation of checker plug-ins.

    Typical usage::

        manager = CheckerManager()
        manager.discover()                        # load entry_points
        manager.load("mypkg.rules:MyChecker")     # optional: ad-hoc load
        checkers = manager.active(select=None, exclude=["some-checker"])
    """

    def __init__(self) -> None:
        self._registered: Dict[str, Type[CheckerBase]] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> None:
        """Register CoreChecker then all ``pssparser.checkers`` entry-points.

        Idempotent: safe to call more than once, though once per process is
        the normal pattern (second call will raise on duplicate IDs if any
        entry-points were already registered).
        """
        from .core_checker import CoreChecker

        if "core" not in self._registered:
            self._registered["core"] = CoreChecker

        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="pssparser.checkers")
        except Exception:
            eps = []

        for ep in eps:
            if ep.name not in self._registered:
                try:
                    cls = ep.load()
                    self._registered[ep.name] = cls
                except Exception as exc:
                    import warnings
                    warnings.warn(
                        f"Failed to load checker entry-point {ep.name!r}: {exc}",
                        stacklevel=2,
                    )

        self._check_unique_ids()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_unique_ids(self) -> None:
        """Raise ``ValueError`` if any ``MarkerDef.id`` is declared by two checkers."""
        seen: Dict[str, str] = {}  # marker_id -> checker_name
        for name, cls in self._registered.items():
            for md in cls().marker_defs:
                if md.id in seen:
                    raise ValueError(
                        f"Duplicate MarkerDef ID {md.id!r}: "
                        f"declared by both {seen[md.id]!r} and {name!r}"
                    )
                seen[md.id] = name

    # ------------------------------------------------------------------
    # Ad-hoc loading
    # ------------------------------------------------------------------

    def load(self, spec: str) -> None:
        """Load a checker from a ``'module.path:ClassName'`` spec string.

        Parameters
        ----------
        spec:
            A string of the form ``"module.path:ClassName"``.

        Raises
        ------
        ValueError
            On malformed spec, missing module/class, empty checker name, or
            duplicate marker IDs.
        """
        module_path, sep, class_name = spec.rpartition(":")
        if not sep or not module_path or not class_name:
            raise ValueError(
                f"Invalid checker spec {spec!r}; expected 'module.path:ClassName'"
            )
        try:
            mod = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            raise ValueError(
                f"Cannot load checker spec {spec!r}: module not found — {exc}"
            ) from exc
        try:
            cls = getattr(mod, class_name)
        except AttributeError as exc:
            raise ValueError(
                f"Cannot load checker spec {spec!r}: attribute not found — {exc}"
            ) from exc

        instance = cls()
        if not instance.name:
            raise ValueError(
                f"Checker {cls.__name__!r} loaded from {spec!r} has an empty 'name' attribute"
            )
        self._registered[instance.name] = cls
        self._check_unique_ids()

    # ------------------------------------------------------------------
    # Active-checker selection
    # ------------------------------------------------------------------

    def active(
        self,
        select: Optional[List[str]],
        exclude: Optional[List[str]],
    ) -> List[CheckerBase]:
        """Return instantiated active checkers after applying filters.

        ``is_builtin`` checkers are never included (they are metadata-only).

        Parameters
        ----------
        select:
            If non-empty, keep *only* these checker names.  Unknown names
            raise ``ValueError`` (fail-fast).
        exclude:
            If ``select`` is ``None``/empty and this is non-empty, remove
            these checker names from the active set.  Unknown names are
            silently ignored.

        Raises
        ------
        ValueError
            When *select* contains names not in the registry.
        """
        non_builtin = [
            n for n, cls in self._registered.items()
            if not getattr(cls, "is_builtin", False)
        ]

        if select:
            unknown = [n for n in select if n not in self._registered]
            if unknown:
                raise ValueError(f"Unknown checker(s): {', '.join(unknown)}")
            names = [n for n in select if n in self._registered]
        elif exclude:
            names = [n for n in non_builtin if n not in exclude]
        else:
            names = non_builtin

        return [self._registered[n]() for n in names]

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_checkers(self) -> List[dict]:
        """Return info dicts for ``--list-checkers`` display."""
        result = []
        for name, cls in self._registered.items():
            inst = cls()
            result.append({
                "name": name,
                "description": inst.description or "(no description)",
                "marker_ids": [md.id for md in inst.marker_defs],
                "is_builtin": getattr(inst, "is_builtin", False),
            })
        return result

    def list_all_markers(self) -> List[dict]:
        """Return every ``MarkerDef`` across all registered checkers."""
        result = []
        for name, cls in self._registered.items():
            for md in cls().marker_defs:
                result.append({
                    "id": md.id,
                    "severity": md.severity,
                    "checker": name,
                    "summary": md.summary,
                })
        return result

    def describe_marker(self, marker_id: str) -> Optional[dict]:
        """Return a full description dict for *marker_id*, or ``None``."""
        for name, cls in self._registered.items():
            for md in cls().marker_defs:
                if md.id == marker_id:
                    return {
                        "id": md.id,
                        "severity": md.severity,
                        "checker": name,
                        "summary": md.summary,
                        "detail": md.detail,
                    }
        return None

    def build_marker_index(self, active_checkers: List[CheckerBase]) -> dict:
        """Build a ``{marker_id: MarkerDef}`` index for the given checkers.

        Always includes ``CoreChecker`` marker defs so that built-in codes
        can be looked up even though ``CoreChecker`` is not in
        *active_checkers*.
        """
        from .core_checker import CoreChecker

        index: dict = {}
        for md in CoreChecker().marker_defs:
            index[md.id] = md
        for checker in active_checkers:
            for md in checker.marker_defs:
                index[md.id] = md
        return index
