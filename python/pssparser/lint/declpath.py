"""The declaration that encloses a source location.

``DeclPathIndex`` answers "where in the model is line 42, column 7?" with a
qualified path such as ``pkg::C::A::constraint c``.  Fingerprints (baselines)
hash it instead of a line number, so a finding keeps its identity when code is
inserted above it, and SARIF reports it as the result's logical location.

Path segments:

* a package, type, enum, typedef or monitor contributes its name
  (``a::b`` for ``package a::b``);
* a function, constraint block, exec block, activity or activity symbol
  contributes its keyword and name: ``function f``, ``constraint c``,
  ``exec post_solve``, ``activity``, ``symbol s``;
* an unnamed constraint is ``constraint``; an extension is
  ``extend <kind> <target as written>``.  When one of these repeats in its
  parent scope, the second is ``#2``, the third ``#3``, in source order.

An extension's path is where it is written, not the extended type's path:
``extend action C::A`` inside ``package p`` is ``p::extend action C::A``.  It
is stable without the link, and correct when the type comes from another
package.

Locations are 1-based lines and columns, end exclusive, as in the AST and in
diagnostics.
"""
from __future__ import annotations

import bisect
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

Pos = Tuple[int, int]

#: Column used for "to the end of the line" when a node has no end location.
_EOL = 1 << 30

_EXEC_KINDS = {
    "ExecKind_Body": "body",
    "ExecKind_Header": "header",
    "ExecKind_Declaration": "declaration",
    "ExecKind_RunStart": "run_start",
    "ExecKind_RunEnd": "run_end",
    "ExecKind_InitDown": "init_down",
    "ExecKind_InitUp": "init_up",
    "ExecKind_PreSolve": "pre_solve",
    "ExecKind_PostSolve": "post_solve",
    "ExecKind_PreBody": "pre_body",
    "ExecKind_File": "file",
}

#: Kinds whose children are statements or items, never a named scope.
_LEAVES = frozenset({
    "ActivityDecl", "ExecBlock", "SymbolDeclaration", "FunctionDefinition",
    "FunctionPrototype", "FunctionImportProto", "TargetTemplateFunction",
    "ConstraintBlock", "CovergroupType", "EnumDecl", "ExtendEnum",
    "TypedefDeclaration",
})

#: Segments that may legally repeat in one scope, and so are numbered.
_NUMBERED = frozenset({"constraint", "exec", "activity", "extend"})


@dataclass
class DeclScope:
    """One named (or positionally named) declaration and its extent."""

    path: str
    name: str
    #: package, component, action, struct, monitor, covergroup, enum,
    #: typedef, function, constraint, exec, activity, symbol, extend,
    #: class.
    kind: str
    file: str
    start: Pos
    end: Pos
    children: List["DeclScope"] = field(default_factory=list, repr=False)

    def contains(self, pos: Pos) -> bool:
        return self.start <= pos < self.end


def _real(path: str) -> str:
    try:
        return os.path.realpath(path)
    except (OSError, ValueError):
        return path


def _ident(expr) -> str:
    try:
        return expr.getId()
    except Exception:
        return ""


def _spelled(type_id) -> str:
    try:
        names = [e.getId().getId() for e in type_id.getElems()]
    except Exception:
        return "?"
    prefix = "::" if getattr(type_id, "getIs_global", lambda: False)() else ""
    return prefix + "::".join(names)


def _proto_name(node) -> str:
    proto = node
    if hasattr(node, "getProto"):
        proto = node.getProto()
    try:
        return proto.getName().getId()
    except Exception:
        return "?"


def _enum_name(enum: str, value, names: Optional[Dict[str, str]] = None) -> str:
    import pssparser.ast as A
    try:
        name = getattr(A, enum)(int(value)).name
    except (AttributeError, ValueError, TypeError):
        return str(value)
    return names.get(name, name) if names else name


def _segment(node) -> Optional[Tuple[str, str]]:
    """(kind, segment) for a node that names a scope, else None."""
    cls = type(node).__name__
    if cls == "PackageScope":
        try:
            ids = [i.getId() for i in node.getIdList()]
        except Exception:
            ids = []
        return "package", "::".join(ids) or "?"
    if cls in ("Component", "Action", "Struct", "Monitor", "CovergroupType",
               "EnumDecl", "TypedefDeclaration", "ImportClassDecl"):
        kind = {"CovergroupType": "covergroup", "EnumDecl": "enum",
                "TypedefDeclaration": "typedef",
                "ImportClassDecl": "class"}.get(cls, cls.lower())
        return kind, _ident(node.getName()) or "?"
    if cls in ("FunctionDefinition", "FunctionPrototype",
               "FunctionImportProto", "TargetTemplateFunction"):
        return "function", "function " + _proto_name(node)
    if cls == "ConstraintBlock":
        name = _ident(node.getName()) if node.getName() is not None else ""
        return "constraint", ("constraint " + name) if name else "constraint"
    if cls == "ExecBlock":
        return "exec", "exec " + _enum_name("ExecKind", node.getKind(),
                                             _EXEC_KINDS)
    if cls == "ActivityDecl":
        return "activity", "activity"
    if cls == "SymbolDeclaration":
        return "symbol", "symbol " + (node.getName() or "?")
    if cls in ("ExtendType", "ExtendEnum"):
        if cls == "ExtendEnum":
            what = "enum"
        else:
            what = _enum_name("ExtendTargetE", node.getKind()).lower()
        return "extend", "extend %s %s" % (what, _spelled(node.getTarget()))
    return None


class MissingEndLocation(ValueError):
    """A declaration the index needs has a start but no end location."""


class DeclPathIndex:
    """Per-file tree of declaration extents over linked or unlinked units.

    *global_scopes* are ``GlobalScope`` nodes (``parser.user_units()``, or
    ``CheckContext.global_scopes``); *file_map* maps a unit's file id to its
    path.  With *strict*, a scope node that has a start location but no end
    raises :class:`MissingEndLocation`; otherwise it extends to the end of
    its first line and is listed in :attr:`missing_end`.
    """

    def __init__(self, global_scopes: Iterable[Any], file_map: Dict[int, str],
                 *, strict: bool = False):
        self._roots: Dict[str, List[DeclScope]] = {}
        self._strict = strict
        self._starts: Dict[int, List[Pos]] = {}
        #: (kind, file, line, col) of each scope node with no end location.
        self.missing_end: List[Tuple[str, str, int, int]] = []
        for unit in global_scopes:
            path = file_map.get(unit.getFileid(), "")
            if not path:
                continue
            roots = self._roots.setdefault(_real(path), [])
            self._walk(unit, path, "", roots, {})
        for roots in self._roots.values():
            _sort(roots)

    # -- building -----------------------------------------------------------

    def _walk(self, node, path: str, prefix: str, out: List[DeclScope],
              seen: Dict[str, int]) -> None:
        children = getattr(node, "getChildren", None)
        if children is None:
            return
        for child in children():
            seg = _segment(child)
            if seg is None:
                if type(child).__name__ not in _LEAVES:
                    self._walk(child, path, prefix, out, seen)
                continue
            kind, name = seg
            b = child.getLocation()
            if b.lineno < 1:
                continue
            e = child.getEndLocation()
            if e.lineno < 1:
                self.missing_end.append(
                    (type(child).__name__, path, b.lineno, b.linepos))
                if self._strict:
                    raise MissingEndLocation(
                        "%s at %s:%d:%d has no end location" % (
                            type(child).__name__, path, b.lineno, b.linepos))
                end = (b.lineno, _EOL)
            else:
                end = (e.lineno, e.linepos)
            if kind in _NUMBERED:
                n = seen.get(name, 0) + 1
                seen[name] = n
                if n > 1:
                    name = "%s#%d" % (name, n)
            full = prefix + "::" + name if prefix else name
            scope = DeclScope(path=full, name=name, kind=kind, file=path,
                              start=(b.lineno, b.linepos), end=end)
            out.append(scope)
            if type(child).__name__ not in _LEAVES:
                self._walk(child, path, full, scope.children, {})

    # -- queries ------------------------------------------------------------

    def chain_at(self, file: str, line: int, col: int) -> List[DeclScope]:
        """Every declaration containing *line*:*col*, outermost first."""
        level = self._roots.get(_real(file))
        pos = (line, col)
        out: List[DeclScope] = []
        while level:
            starts = self._starts.get(id(level))
            if starts is None:
                starts = self._starts[id(level)] = [s.start for s in level]
            # Siblings do not overlap, so only the last one starting at or
            # before pos can contain it.
            i = bisect.bisect_right(starts, pos) - 1
            if i < 0 or not level[i].contains(pos):
                break
            out.append(level[i])
            level = level[i].children
        return out

    def scope_at(self, file: str, line: int, col: int) -> Optional[DeclScope]:
        """The innermost declaration containing *line*:*col*, or None."""
        chain = self.chain_at(file, line, col)
        return chain[-1] if chain else None

    def path_at(self, file: str, line: int, col: int) -> str:
        """The qualified path at *line*:*col*; ``""`` at global scope."""
        scope = self.scope_at(file, line, col)
        return scope.path if scope is not None else ""

    def scopes(self, file: str) -> List[DeclScope]:
        """The top-level declarations of *file*, in source order."""
        return list(self._roots.get(_real(file), []))


def _sort(scopes: List[DeclScope]) -> None:
    scopes.sort(key=lambda s: s.start)
    for s in scopes:
        _sort(s.children)


def location_of(loc) -> Tuple[str, int, int]:
    """(file, line, col) from a marker dict, a Diagnostic or a tuple."""
    if isinstance(loc, tuple):
        return loc[0], int(loc[1]), int(loc[2])
    if isinstance(loc, dict):
        return loc.get("file", ""), int(loc.get("line", 0)), int(loc.get("col", 0))
    return getattr(loc, "file", ""), int(getattr(loc, "line", 0)), int(getattr(loc, "col", 0))


def index_for(parser, files: Optional[Iterable[str]] = None,
              *, strict: bool = False) -> DeclPathIndex:
    """A :class:`DeclPathIndex` over a parser's user units (after
    ``parse()`` or ``link()``), limited to *files* when given."""
    from pssparser.waivers import _user_units

    if files is None:
        file_map = dict(getattr(parser, "file_map", {}) or {})
        files = list(file_map.values())
    units, file_map = _user_units(parser, list(files))
    return DeclPathIndex(units, file_map, strict=strict)
