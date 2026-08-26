"""Helpers for asserting on template parameter *binding*, not just linking.

The pre-existing template tests all have the shape::

    root = assert_parse_ok(" ... S<int> v; ... ")
    assert root is not None

which asserts only that the model linked without an error.  That cannot see
the failure mode that actually matters here: a template parameter bound to the
*wrong* type.  A wrong binding is silent -- it either resolves to something and
produces a confusing error far downstream in an unrelated file, or it resolves
to something with a compatible-looking member and produces no error at all.

So the helpers below are built around answering one question precisely:

    "parameter ``T`` of this specialization is bound to *that exact
     declaration*"

and comparing by node identity rather than by spelling.  Comparing names would
pass on a wrong binding whenever two types share a short name, which is normal
across packages.

Background on the representation
--------------------------------

``TaskBuildParamValList::build`` produces, for each use of a generic, a *new*
``TemplateParamDeclList`` in which each parameter declaration carries the
**supplied argument** in its ``dflt`` slot, falling back to the declared
default for parameters the use did not supply.  The list is then marked
``setSpecialized(true)``.

The consequence to keep in mind while reading this module: ``getDflt()`` means
"declared default" on an unspecialized list and "bound argument" on a
specialized one.  Everything here deliberately operates on specializations
reached via ``getSpec_types()``, where the second reading is the correct one.
"""
from typing import Any, List, Optional, Union

from pssparser.core import resolveSymbolPathRef


# ---------------------------------------------------------------------------
# Generic tree navigation
# ---------------------------------------------------------------------------

def node_name(node) -> Optional[str]:
    """The declared name of any AST node, or None if it has none.

    Symbol scopes return a ``str`` from ``getName()``; fields and enum items
    return an ``ExprId``.  Normalizing here keeps every caller from having to
    care which it is holding.
    """
    if node is None or not hasattr(node, "getName"):
        return None
    name = node.getName()
    if name is None:
        return None
    if isinstance(name, str):
        return name
    getter = getattr(name, "getId", None)
    return getter() if getter is not None else None


def child_by_name(scope, name: str):
    """Find a direct child of ``scope`` by name, by scanning.

    Deliberately a scan rather than a ``symtabAt()`` lookup.  A symtab index is
    an index into ``getChildren()`` only for a *synthetic* scope; for a
    non-synthetic one it records the child's position in the physical AST
    parent, which need not line up.  Scanning is O(n) on scopes that are small
    in every test here, and it cannot silently return the wrong node.
    """
    if scope is None or not hasattr(scope, "numChildren"):
        return None
    for i in range(scope.numChildren()):
        c = scope.getChild(i)
        if node_name(c) == name:
            return c
    return None


def lookup(root, qname: str):
    """Resolve a ``::``-qualified name from the root symbol scope."""
    node = root
    for part in qname.split("::"):
        node = child_by_name(node, part)
        if node is None:
            raise AssertionError(
                "could not resolve %r: no element named %r" % (qname, part))
    return node


# ---------------------------------------------------------------------------
# Specializations
# ---------------------------------------------------------------------------

def generic(root, qname: str):
    """The *unspecialized* declaration of a parameterized type."""
    node = lookup(root, qname)
    assert hasattr(node, "numSpec_types"), (
        "%s is not a type scope, so it cannot be a generic" % qname)
    return node


def specializations(root, qname: str) -> List[Any]:
    """Every specialization of ``qname``, in creation order."""
    g = generic(root, qname)
    return [g.getSpec_type(i) for i in range(g.numSpec_types())]


def param_decls(spec) -> List[Any]:
    """The bound parameter list of a specialization."""
    target = spec.getTarget()
    assert target is not None, "specialization %r has no target" % spec.getName()
    params = target.getParams()
    if params is None:
        return []
    assert params.getSpecialized(), (
        "parameter list of %r is not marked specialized -- this is the "
        "*declaration's* list, whose dflt slots hold declared defaults rather "
        "than bound arguments" % spec.getName()
    )
    return [params.getParam(i) for i in range(params.numParams())]


def _param(spec, param: Union[int, str]):
    decls = param_decls(spec)
    if isinstance(param, int):
        assert 0 <= param < len(decls), (
            "parameter index %d out of range: %r has %d parameter(s)"
            % (param, spec.getName(), len(decls)))
        return decls[param]
    for pd in decls:
        if node_name(pd) == param:
            return pd
    raise AssertionError(
        "no parameter named %r; have %r"
        % (param, [node_name(pd) for pd in decls]))


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------

def binding_decl(root, spec, param: Union[int, str]):
    """The *declaration node* a parameter is bound to, or None.

    Returns None when the argument is a builtin scalar (``int``, ``bit[8]``,
    ``bool``) or a plain value, since those name no declaration.  Use
    :func:`binding_desc` to describe those, and :func:`assert_binds_to` to
    assert on either uniformly.
    """
    dflt = _param(spec, param).getDflt()
    if dflt is None:
        return None
    type_id = getattr(dflt, "getType_id", None)
    if type_id is None:
        return None
    tid = type_id()
    if tid is None or tid.getTarget() is None:
        return None
    return resolveSymbolPathRef(root, tid.getTarget())


def binding_desc(root, spec, param: Union[int, str]) -> str:
    """A canonical, readable description of what a parameter is bound to.

    Covers every argument form uniformly so tests can assert on a literal:
    ``"int"``, ``"bit[8]"``, ``"bool"``, ``"my_s"``, ``"4"``.
    """
    dflt = _param(spec, param).getDflt()
    return _describe(root, dflt)


def _describe(root, node) -> str:
    if node is None:
        return "<unbound>"

    # A user-defined type argument: describe by the declaration it resolves
    # to, falling back to the written name when it did not resolve.
    if hasattr(node, "getType_id"):
        tid = node.getType_id()
        if tid is not None:
            if tid.getTarget() is not None:
                decl = resolveSymbolPathRef(root, tid.getTarget())
                name = node_name(decl)
                if name:
                    return name
            return "::".join(
                tid.getElem(i).getId().getId() for i in range(tid.numElems()))

    kind = type(node).__name__

    if kind == "DataTypeInt":
        width = node.getWidth()
        signed = node.getIs_signed()
        if width is not None and hasattr(width, "getValue"):
            w = width.getValue()
            # A plain `int` is signed and 32 bits wide; anything else is
            # spelled with its width so the two never compare equal.
            if signed and w == 32:
                return "int"
            if not signed and w == 1:
                return "bit"
            return "%s[%d]" % ("int" if signed else "bit", w)
        return "int" if signed else "bit"

    if kind == "DataTypeBool":
        return "bool"

    if kind == "ExprUnsignedNumber":
        return str(node.getValue())

    if kind == "ExprId":
        return node.getId()

    # Anything else -- a compound value expression, say -- is described by its
    # node kind.  Deliberately not evaluated: some defaults are recursive
    # expressions that are unsafe to evaluate here.
    return "<%s>" % kind


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def assert_binds_to(root, spec, param: Union[int, str], expected) -> None:
    """Assert parameter ``param`` of ``spec`` is bound to ``expected``.

    ``expected`` is either a declaration node -- compared by native handle
    identity, which is what makes this immune to two types sharing a name --
    or a string, compared against :func:`binding_desc`.
    """
    if isinstance(expected, str):
        actual = binding_desc(root, spec, param)
        assert actual == expected, (
            "parameter %r of %r is bound to %r, expected %r"
            % (param, spec.getName(), actual, expected))
        return

    actual = binding_decl(root, spec, param)
    assert actual is not None, (
        "parameter %r of %r is not bound to any declaration (it describes as "
        "%r)" % (param, spec.getName(), binding_desc(root, spec, param)))
    assert actual == expected, (
        "parameter %r of %r is bound to the declaration %r, expected %r"
        % (param, spec.getName(), node_name(actual), node_name(expected)))


def bindings(root, spec) -> List[str]:
    """Every parameter of ``spec`` described, in declaration order."""
    return [binding_desc(root, spec, i) for i in range(len(param_decls(spec)))]


def assert_specialization_count(root, qname: str, count: int) -> None:
    """Assert ``qname`` has exactly ``count`` specializations.

    Catches both failure directions: too few means distinct argument lists were
    silently merged into one specialization, too many means identical argument
    lists failed to deduplicate.
    """
    specs = specializations(root, qname)
    assert len(specs) == count, (
        "%s has %d specialization(s), expected %d; bindings are %r"
        % (qname, len(specs), count, [bindings(root, s) for s in specs]))


def find_specialization(root, qname: str, *descs: str):
    """The unique specialization of ``qname`` whose bindings are ``descs``."""
    want = list(descs)
    matches = [s for s in specializations(root, qname)
               if bindings(root, s) == want]
    assert len(matches) == 1, (
        "expected exactly 1 specialization of %s bound as %r, found %d; all "
        "bindings are %r"
        % (qname, want, len(matches),
           [bindings(root, s) for s in specializations(root, qname)]))
    return matches[0]
