"""Every identifier occurrence in the user's files, with its declaration.

::

    import pssparser
    from pssparser import refs

    p = pssparser.Parser()
    p.parse(files)
    try:
        p.link()
    except pssparser.ParseException:
        pass                        # occurrences are still available

    for o in refs.occurrences(p):
        print(o.fileid, o.line, o.col, o.text, o.resolution, o.decl_location)

Occurrences are read from the linked tree: the linker records what each name
binds to, and this module reports it. Nothing here re-resolves a name, so the
answers are the linker's answers, gaps included -- a name the linker does not
bind yet is reported ``unresolved`` rather than dropped.

Grouping: every occurrence of one declaration carries the same ``decl``.
Compare with ``==`` or use ``hash`` -- AST wrappers compare by the underlying
node -- but not with ``id()``: each access creates a new wrapper object.

``exports`` and ``export_of`` answer "which ``export`` statements name this
function" (20.4.2) from the same bindings.

See docs/refs.rst.
"""
import dataclasses
import enum
from typing import Any, List, NamedTuple, Optional, Tuple

__all__ = ["Location", "Occurrence", "Resolution", "occurrences",
           "exports", "export_of"]


class Resolution(str, enum.Enum):
    """How an occurrence was bound.

    A **closed set**. A client that meets a value it does not know should
    fail, not guess: a new value here is a deliberate, versioned change.
    The members compare equal to their string values
    (``Resolution.BUILTIN == "builtin"``).
    """

    #: Bound to a declaration in a user file (fileid >= 1).
    USER = "user"
    #: Bound to a standard-library declaration (fileid 0). The library is
    #: one unit: :func:`library_location` names the file and line within it.
    LIBRARY = "library"
    #: A built-in with no declaration in any source: ``comp``, ``this``, and
    #: collection methods such as ``push_back``. ``decl`` is None, or a
    #: synthetic node with no location.
    BUILTIN = "builtin"
    #: Not bound. ``decl`` is None.
    UNRESOLVED = "unresolved"
    #: Not bound, inside a generic template body, where the declaration can
    #: depend on a template parameter. ``decl`` is None.
    DEPENDENT = "dependent"


# The order of pssp::OccurrenceResolution (src/include/pssp/IOccurrenceCollector.h).
_RESOLUTION_BY_ORDINAL = (
    Resolution.USER,
    Resolution.LIBRARY,
    Resolution.BUILTIN,
    Resolution.UNRESOLVED,
    Resolution.DEPENDENT,
)


class Location(NamedTuple):
    """A name's position. ``line`` and ``col`` are 1-based, as in
    ``ExprId.getLocation()``; ``extent`` is its length in characters."""
    fileid: int
    line: int
    col: int
    extent: int


@dataclasses.dataclass(frozen=True, eq=False)
class Occurrence:
    """One identifier, as written in a user file."""

    fileid: int
    line: int
    col: int
    extent: int
    #: The identifier as written (without a leading ``\\`` if escaped).
    text: str
    #: True where this occurrence is the name being declared.
    is_declaration: bool
    #: The declaring AST node, as its most-derived wrapper class, or None.
    #: For a declaration occurrence it is that declaration.
    decl: Any
    #: Where the declaration's name is, or None (unbound, or a declaration
    #: with no source location).
    decl_location: Optional[Location]
    resolution: Resolution
    #: For a declaration that overrides or shadows one in a base type (a
    #: constraint, an override function, a field hiding a base field): the
    #: declaration it overrides -- the *immediate* one, so follow
    #: ``base_decl`` of that to walk the chain. None otherwise.
    base_decl: Any = None
    #: The ExprId node itself.
    node: Any = dataclasses.field(default=None, repr=False)
    # Keeps the linked tree alive for as long as any occurrence is: every AST
    # object above is borrowed from it.
    _root: Any = dataclasses.field(default=None, repr=False)

    @property
    def location(self) -> Location:
        return Location(self.fileid, self.line, self.col, self.extent)


def library_location(loc: Location) -> Optional[Tuple[str, int]]:
    """The core-library file and line of a fileid-0 location, such as a
    ``decl_location`` that resolves to ``Resolution.LIBRARY``:
    ``("<stdlib>/std_pkg.pss", 12)``. None for any other location.
    """
    if loc.fileid != 0:
        return None
    from .parser import core_library_location
    return core_library_location(loc.line)


def occurrences(parser_or_root) -> List[Occurrence]:
    """Every identifier occurrence in the user files, sorted by
    ``(fileid, line, col)``.

    Takes a :class:`pssparser.Parser` after :meth:`~pssparser.Parser.link`
    -- including one whose ``link()`` raised -- or the linked
    ``RootSymbolScope`` itself. Names with no source location (the implicit
    ``pss_top``, the synthetic ``comp`` field) are not reported.
    """
    import pssparser.core as core

    from pssparser.parser import Parser

    root = parser_or_root
    if isinstance(parser_or_root, Parser):
        root = parser_or_root.root
    if root is None:
        raise ValueError("occurrences() needs a linked Parser; call link() first")

    ret = []
    for (node, decl, decl_name, base_decl, is_decl, res) in \
            core.Factory.inst().collectOccurrences(root):
        loc = node.getLocation()
        decl_loc = None
        if decl_name is not None:
            dl = decl_name.getLocation()
            if dl.lineno > 0:
                decl_loc = Location(dl.fileid, dl.lineno, dl.linepos, dl.extent)
        ret.append(Occurrence(
            fileid=loc.fileid,
            line=loc.lineno,
            col=loc.linepos,
            extent=loc.extent,
            text=node.getId(),
            is_declaration=bool(is_decl),
            decl=decl,
            decl_location=decl_loc,
            resolution=_RESOLUTION_BY_ORDINAL[res],
            base_decl=base_decl,
            node=node,
            _root=root))
    return ret


def _linked_root(parser_or_root, what):
    from pssparser.parser import Parser

    root = parser_or_root
    if isinstance(parser_or_root, Parser):
        root = parser_or_root.root
    if root is None:
        raise ValueError("%s() needs a linked Parser; call link() first" % what)
    return root


def exports(parser_or_root) -> dict:
    """Every ``export`` statement of the model, by the function it names:
    ``{SymbolFunctionScope: [ExportFunction, ...]}``, each list in source
    order. The function is the one the linker bound; an export it did not
    bind is left out. A function may be exported more than once (an
    ``export target`` and an ``export solve``, say), so the values are lists.
    """
    import pssparser.core as core

    root = _linked_root(parser_or_root, "exports")
    out: dict = {}
    stack = [root]
    while stack:
        s = stack.pop()
        for i in range(s.numChildren()):
            c = s.getChild(i)
            if type(c).__name__ == "ExportFunction":
                name = c.getName()
                ref = name.getTarget() if name is not None else None
                fn = core.resolveSymbolPathRef(root, ref) if ref is not None else None
                # An extension's members are also merged into the type they
                # extend, so the same export is reachable twice.
                if fn is not None and c not in out.setdefault(fn, []):
                    out[fn].append(c)
            elif hasattr(c, "numChildren") and hasattr(c, "getUpper"):
                stack.append(c)
    for v in out.values():
        v.sort(key=lambda e: (e.getLocation().fileid, e.getLocation().lineno,
                              e.getLocation().linepos))
    return out


def export_of(parser_or_root, fn) -> list:
    """The ``export`` statements that name *fn*, in source order; ``[]`` if
    none. *fn* is the function's ``SymbolFunctionScope``, its
    ``FunctionDefinition`` or one of its ``FunctionPrototype``\ s. To ask
    of many functions, build :func:`exports` once instead.
    """
    table = exports(parser_or_root)
    for scope, exps in table.items():
        if scope == fn or scope.getTarget() == fn or scope.getDefinition() == fn:
            return exps
        if any(scope.getPrototype(i) == fn for i in range(scope.numPrototypes())):
            return exps
    return []
