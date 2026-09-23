"""
The generated ``pssparser/ast.pyi`` must be valid Python and must match the
compiled module (pss-scrambler BUG-002).

It once had 77 list accessors emitted as ``def x(self) -> ListUtil...``, which
is a syntax error, so no type checker could load the stub. It also declared
``SymbolRefPath.getPath`` twice, with the zero-argument copy shadowing the
real one, and 21 enum-field setters that the extension did not have.
"""
import ast as pyast
import collections
import re
from pathlib import Path

import pytest

import pssparser.ast as A

STUB = Path(A.__file__).with_name("ast.pyi")


def _stub_defs():
    cls, defs = None, collections.defaultdict(list)
    for n, line in enumerate(STUB.read_text().splitlines(), 1):
        m = re.match(r"class (\w+)", line)
        if m:
            cls = m.group(1)
            continue
        m = re.match(r"\s+def (\w+)\(", line)
        if m and cls:
            defs[cls].append((m.group(1), n))
    return defs


def test_stub_parses():
    pyast.parse(STUB.read_text(), filename=str(STUB))


def test_stub_has_no_duplicate_members():
    dups = []
    for cls, ds in _stub_defs().items():
        names = [d[0] for d in ds]
        dups += ["%s.%s" % (cls, n) for n in sorted({x for x in names
                                                      if names.count(x) > 1})]
    assert dups == []


def test_stub_members_exist_at_runtime():
    missing = []
    for cls, ds in _stub_defs().items():
        rt = getattr(A, cls, None)
        for name, n in ds:
            if rt is None or not hasattr(rt, name):
                missing.append("%s.%s (line %d)" % (cls, name, n))
    assert missing == []


def test_list_accessor_is_a_sized_indexable_listutil():
    from pssparser import Parser
    p = Parser()
    p.parses([("t.pss", "import std_pkg::*;\ncomponent pss_top { int a; }\n")])
    root = p.link()
    u = p.user_units()[0]
    lu = u.children()
    assert isinstance(lu, A.ListUtil)
    assert len(lu) == u.numChildren() == len(list(lu))
    assert lu[0] == u.getChild(0)
    assert lu[-1] == u.getChild(u.numChildren() - 1)
    with pytest.raises(IndexError):
        lu[len(lu)]
    del root


def test_enum_setter_round_trips():
    from pssparser import Parser
    p = Parser()
    p.parses([("t.pss", "component pss_top { int a = 1 + 2; }\n")])
    root = p.link()
    found = []

    class V(A.VisitorBase):
        def visitExprBin(self, e):
            found.append(e)

    p.user_units()[0].accept(V())
    (e,) = found
    assert e.getOp() == A.ExprBinOp.BinOp_Add
    e.setOp(A.ExprBinOp.BinOp_Sub)
    assert e.getOp() == A.ExprBinOp.BinOp_Sub
    del root
