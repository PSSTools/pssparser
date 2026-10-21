"""The annotations on an element, and the values they give their fields.

An annotation (LRM 7.13) gives a value to each field of its type: the one
written in its parameter list, or the field's declared initializer. The type
may inherit fields from a base annotation and gain more from ``extend
annotation``; a generator reading an annotation wants all of them, folded::

    from pssparser import annotations

    p = pssparser.Parser()
    p.parses([("hal.pss", text)])
    root = p.link()

    for ann in annotations.find(root, comp, "hal_pkg::hal_s"):
        vals = annotations.effective(root, ann)
        vals["name"].value          # "UART", a str
        vals["prefix"].is_default   # True: the field's initializer was used

An annotation is matched on the type the linker resolved, never on its
spelling: ``@hal_s`` under an import and ``@hal_pkg::hal_s`` are the same
annotation, and a model's own ``hal_s`` in another package is not.

Values are folded here, once, so that every consumer gets the same answer.
A value that does not fold (it names something that is not a constant, or
uses an operator this module does not fold) is ``None``; ``Value.expr`` still
holds the expression.

``pssparser.waivers`` matches ``@lint_pkg::waive`` by spelling on purpose and
does not use this module: it must work on a model that never imports
``lint_pkg``.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, Iterator, List, Optional, Union

__all__ = ["EnumValue", "Value", "find", "on", "standalone", "type_of",
           "effective", "fields", "fold", "qualified_name"]


@dataclasses.dataclass(frozen=True)
class EnumValue:
    """An enum item as a value: its enum's qualified name, its own name and
    its integer value (``None`` if that does not fold). Two are equal when
    they name the same item; ``item`` is the AST node and is not compared."""
    enum: str
    name: str
    value: Optional[int]
    item: Any = dataclasses.field(default=None, compare=False, repr=False)


@dataclasses.dataclass(frozen=True, eq=False)
class Value:
    """One field's value in one annotation.

    ``expr`` is the parameter's expression, or the field's initializer when
    the annotation does not set the field (``is_default``). Both are ``None``
    for a field with no initializer that the annotation leaves unset; the
    linker warns about that (LINT411). ``value`` is ``expr`` folded: a
    ``str``, ``int``, ``bool`` or ``EnumValue``, or ``None``. ``location`` is
    the parameter's, or the field declaration's for a default.
    """
    name: str
    field: Any
    expr: Any
    value: Any
    is_default: bool
    location: Any


def _root_of(parser_or_root):
    root = getattr(parser_or_root, "root", None)
    if root is not None and not callable(root):
        return root
    return parser_or_root


def _resolve(root, ref):
    if ref is None:
        return None
    import pssparser.core as core
    return core.resolveSymbolPathRef(root, ref)


def qualified_name(scope) -> str:
    """``pkg::name`` of a symbol scope, from its enclosing scopes."""
    names = []
    while scope is not None:
        n = scope.getName()
        if n:
            names.append(n)
        scope = scope.getUpper()
    return "::".join(reversed(names))


def _decl_scope(root, ann):
    """The SymbolTypeScope of an annotation's type, or None if unresolved."""
    t = ann.getType()
    return _resolve(root, t.getTarget()) if t is not None else None


def _own_annotations(node) -> Iterator[Any]:
    """Every annotation written on ``node``.

    ``node`` may be an AST declaration or the symbol scope the linker wraps
    one in: a type's scope holds it as ``target``, an enum's as ``decl``, and
    a function's annotations may be on its prototype and its definition.
    """
    seen = set()
    cands = [node]
    for acc in ("getTarget", "getDecl", "getDefinition"):
        f = getattr(node, acc, None)
        if f is not None:
            try:
                cands.append(f())
            except TypeError:
                pass
    num = getattr(node, "numPrototypes", None)
    if num is not None:
        cands.extend(node.getPrototype(i) for i in range(num()))
    for c in cands:
        if c is None or not hasattr(c, "numAnnotations"):
            continue
        for i in range(c.numAnnotations()):
            a = c.getAnnotation(i)
            loc = a.getLocation()
            key = (loc.fileid, loc.lineno, loc.linepos)
            if key not in seen:
                seen.add(key)
                yield a


def find(parser_or_root, node, type: Union[str, Any]) -> List[Any]:
    """The annotations of type ``type`` on ``node``, in source order.

    ``type`` is a qualified name (``"hal_pkg::hal_s"``; a type in the global
    scope is just its name) or the declaration itself, as its symbol scope or
    its ``AnnotationDecl``. An annotation whose type did not resolve (LINT403)
    matches nothing.
    """
    root = _root_of(parser_or_root)
    want = type.lstrip(":") if isinstance(type, str) else type
    out = []
    for ann in _own_annotations(node):
        ts = _decl_scope(root, ann)
        if ts is None:
            continue
        if isinstance(want, str):
            hit = qualified_name(ts) == want
        else:
            hit = want == ts or want == ts.getTarget()
        if hit:
            out.append(ann)
    return out


def on(parser_or_root, node) -> List[Any]:
    """Every annotation written on ``node`` whose type resolved, in source
    order. ``node`` is as for :func:`find`. A standalone annotation is not on
    any element; see :func:`standalone`."""
    root = _root_of(parser_or_root)
    return [a for a in _own_annotations(node)
            if _decl_scope(root, a) is not None]


def standalone(parser_or_root, scope) -> List[Any]:
    """The standalone annotations (``@a_s {...};``) written directly in
    ``scope``, whose type resolved, in source order. ``scope`` is a
    declaration with a body (a component, action, struct or package) or the
    symbol scope that wraps one. A standalone annotation is anchored at its
    place in the scope (7.13); it describes the scope, not the next element."""
    root = _root_of(parser_or_root)
    body = scope
    tgt = getattr(scope, "getTarget", None)
    if tgt is not None:
        try:
            body = tgt() or scope
        except TypeError:
            pass
    out = []
    num = getattr(body, "numChildren", None)
    if num is None:
        return out
    for i in range(num()):
        c = body.getChild(i)
        if type(c).__name__ == "Annotation" and c.getIs_standalone() \
                and _decl_scope(root, c) is not None:
            out.append(c)
    return out


def type_of(parser_or_root, ann):
    """The symbol scope of ``ann``'s type, or ``None`` if it did not resolve.
    ``qualified_name(type_of(root, ann))`` is its qualified name."""
    return _decl_scope(_root_of(parser_or_root), ann)


def _base_scope(root, ts):
    decl = ts.getTarget()
    st = decl.getSuper_t() if decl is not None else None
    return _resolve(root, st.getTarget()) if st is not None else None


def _is_parameter(c) -> bool:
    """A data field of the annotation; not a ``static const`` member."""
    if type(c).__name__ != "Field":
        return False
    import pssparser.ast as A
    attr = int(c.getAttr())
    return not attr & (int(A.FieldAttr.Static) | int(A.FieldAttr.Const))


def fields(parser_or_root, decl) -> Dict[str, Any]:
    """The data fields of an annotation type, by name, in declaration order:
    the base's first, then its own, then those of each ``extend annotation``.
    ``decl`` is the type's symbol scope."""
    root = _root_of(parser_or_root)
    chain, ts = [], decl
    while ts is not None and ts not in chain and len(chain) < 64:
        chain.append(ts)
        ts = _base_scope(root, ts)
    out: Dict[str, Any] = {}
    for ts in reversed(chain):
        for i in range(ts.numChildren()):
            c = ts.getChild(i)
            if _is_parameter(c):
                out[c.getName().getId()] = c
    return out


def effective(parser_or_root, ann) -> Dict[str, Value]:
    """Every field of ``ann``'s type with the value ``ann`` gives it.

    Keys are in declaration order (see ``fields``). A parameter naming no
    field is an error the linker reports, and is left out here. An annotation
    whose type did not resolve gives ``{}``.
    """
    root = _root_of(parser_or_root)
    ts = _decl_scope(root, ann)
    if ts is None:
        return {}
    flds = fields(root, ts)
    explicit = {}
    for i in range(ann.numParameters()):
        p = ann.getParameter(i)
        name = p.getName().getId().getId() if p.getName() is not None else None
        # The first one counts; a repeat is an error (PSS150).
        if name in flds and name not in explicit:
            explicit[name] = p

    out: Dict[str, Value] = {}
    for name, f in flds.items():
        p = explicit.get(name)
        if p is not None:
            expr, loc, is_default = p.getValue(), p.getLocation(), False
        else:
            expr = f.getInit()
            # An expression has no location of its own: the field's
            # declaration is where the default is written.
            loc = f.getLocation() if expr is not None else None
            is_default = True
        out[name] = Value(
            name=name, field=f, expr=expr,
            value=_coerce(root, f, fold(root, expr)) if expr is not None else None,
            is_default=is_default, location=loc)
    return out


# ---------------------------------------------------------------------------
# Folding
# ---------------------------------------------------------------------------

_MAX_DEPTH = 64


def fold(parser_or_root, expr, _depth=0):
    """``expr`` as a Python value, or ``None`` if it does not fold."""
    if expr is None or _depth > _MAX_DEPTH:
        return None
    root = _root_of(parser_or_root)
    kind = type(expr).__name__
    f = _FOLD.get(kind)
    if f is None:
        if hasattr(expr, "getTarget"):
            return _fold_ref(root, expr, _depth)
        return None
    return f(root, expr, _depth)


def _fold_ref(root, expr, depth):
    target = _resolve(root, expr.getTarget())
    kind = type(target).__name__
    if kind == "EnumItem":
        return _enum_value(root, target, depth)
    if kind == "Field":
        # A `static const`: its initializer is its value.
        return fold(root, target.getInit(), depth + 1)
    return None


def _enum_value(root, item, depth) -> EnumValue:
    scope = item.getUpper()
    if scope is None:
        # An item added by `extend enum` (its `upper` is not set): find
        # the enum whose scope holds it.
        scope = _enum_scope_of(root, item)
    enum = qualified_name(scope) if scope is not None else ""
    return EnumValue(enum, item.getName().getId(),
                     _enum_int(root, scope, item, depth), item)


def _enum_scope_of(root, item):
    stack = [root]
    while stack:
        s = stack.pop()
        if type(s).__name__ == "SymbolEnumScope":
            for i in range(s.numChildren()):
                if s.getChild(i) == item:
                    return s
            continue
        if hasattr(s, "numChildren") and hasattr(s, "getUpper"):
            for i in range(s.numChildren()):
                c = s.getChild(i)
                if hasattr(c, "getUpper"):
                    stack.append(c)
    return None


def _enum_int(root, scope, item, depth):
    """An item's value: its own, or one more than the item before it (7.5)."""
    if scope is None:
        v = item.getValue()
        return _as_int(fold(root, v, depth + 1)) if v is not None else None
    prev = -1
    for i in range(scope.numChildren()):
        c = scope.getChild(i)
        if type(c).__name__ != "EnumItem":
            continue
        v = c.getValue()
        cur = _as_int(fold(root, v, depth + 1)) if v is not None else (
            prev + 1 if prev is not None else None)
        if c == item:
            return cur
        prev = cur
    return None


def _as_int(v):
    if isinstance(v, EnumValue):
        return v.value
    if isinstance(v, bool):
        return int(v)
    return v if isinstance(v, int) else None


def _num(root, e, d):
    return e.getValue()


def _str(root, e, d):
    return e.getValue()


def _bool(root, e, d):
    return bool(e.getValue())


def _cond(root, e, d):
    c = fold(root, e.getCond_e(), d + 1)
    if c is None:
        return None
    return fold(root, e.getTrue_e() if c else e.getFalse_e(), d + 1)


def _unary(root, e, d):
    import pssparser.ast as A
    v = fold(root, e.getRhs(), d + 1)
    op = e.getOp()
    U = A.ExprUnaryOp
    if op == U.UnaryOp_LogNot:
        return None if v is None or isinstance(v, str) else not v
    v = _as_int(v)
    if v is None:
        return None
    if op == U.UnaryOp_Plus:
        return v
    if op == U.UnaryOp_Minus:
        return -v
    if op == U.UnaryOp_BitNeg:
        return ~v
    return None


def _div(a, b):
    # PSS (as C) truncates toward zero; Python's // floors.
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _mod(a, b):
    return a - _div(a, b) * b


def _bin(root, e, d):
    import pssparser.ast as A
    B = A.ExprBinOp
    op = e.getOp()
    lhs = fold(root, e.getLhs(), d + 1)
    rhs = fold(root, e.getRhs(), d + 1)
    if lhs is None or rhs is None:
        return None
    if op in (B.BinOp_Eq, B.BinOp_Ne):
        if isinstance(lhs, str) != isinstance(rhs, str):
            return None
        if not isinstance(lhs, str):
            lhs, rhs = _as_int(lhs), _as_int(rhs)
        return (lhs == rhs) if op == B.BinOp_Eq else (lhs != rhs)
    if isinstance(lhs, str) or isinstance(rhs, str):
        return None
    if op == B.BinOp_LogAnd:
        return bool(lhs) and bool(rhs)
    if op == B.BinOp_LogOr:
        return bool(lhs) or bool(rhs)
    a, b = _as_int(lhs), _as_int(rhs)
    if a is None or b is None:
        return None
    if op in (B.BinOp_Div, B.BinOp_Mod):
        if b == 0:
            return None
        return _div(a, b) if op == B.BinOp_Div else _mod(a, b)
    if op in (B.BinOp_Shl, B.BinOp_Shr) and b < 0:
        return None
    if op == B.BinOp_Exp and b < 0:
        return None
    f = {
        B.BinOp_Add: lambda: a + b, B.BinOp_Sub: lambda: a - b,
        B.BinOp_Mul: lambda: a * b, B.BinOp_Exp: lambda: a ** b,
        B.BinOp_Shl: lambda: a << b, B.BinOp_Shr: lambda: a >> b,
        B.BinOp_BitAnd: lambda: a & b, B.BinOp_BitOr: lambda: a | b,
        B.BinOp_BitXor: lambda: a ^ b,
        B.BinOp_Lt: lambda: a < b, B.BinOp_Le: lambda: a <= b,
        B.BinOp_Gt: lambda: a > b, B.BinOp_Ge: lambda: a >= b,
    }.get(op)
    return f() if f is not None else None


_FOLD = {
    "ExprUnsignedNumber": _num,
    "ExprSignedNumber": _num,
    "ExprString": _str,
    "ExprBool": _bool,
    "ExprCond": _cond,
    "ExprUnary": _unary,
    "ExprBin": _bin,
}


def _coerce(root, field, v):
    """An integer as the field's type holds it: ``~0`` in a ``bit[8]`` is
    255, and ``-1`` in an ``int[4]`` stays -1. Anything else is unchanged."""
    if not isinstance(v, int) or isinstance(v, bool):
        return v
    dt = field.getType()
    if type(dt).__name__ != "DataTypeInt":
        return v
    w = dt.getWidth()
    width = _as_int(fold(root, w)) if w is not None else (
        32 if dt.getIs_signed() else 1)
    if width is None or width <= 0:
        return v
    v &= (1 << width) - 1
    if dt.getIs_signed() and v >> (width - 1):
        v -= 1 << width
    return v
