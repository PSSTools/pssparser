"""
`in` is at relational precedence (Table 11): `a in l && b in m` is two
membership tests joined by `&&`. The collection form used to take a whole
`expression` as its collection, so it parsed as `a in (l && (b in m))`.
"""
import pssparser
from pssparser import ast


class _Inits(ast.VisitorBase):
    def __init__(self):
        super().__init__()
        self.inits = {}

    def visitProceduralStmtDataDeclaration(self, i):
        self.inits[i.getName().getId()] = i.getInit()
        super().visitProceduralStmtDataDeclaration(i)


_KEEP = []     # the parsers own the trees the returned nodes live in


def _init(src, name):
    p = pssparser.Parser()
    _KEEP.append(p)
    p.parses([("t.pss", src)])
    root = p.link()
    v = _Inits()
    for k in range(root.numUnits()):
        root.getUnit(k).accept(v)
    return v.inits[name]


SRC = """
component pss_top {
  target function void run() {
    list<int> l; map<int, int> m;
    bool b = 2 in l && 3 in m.keys();
    bool c = 1 in [1..2] || 4 in l;
  }
}
"""


def test_a_collection_in_stops_at_and():
    e = _init(SRC, "b")
    assert isinstance(e, ast.ExprBin) and e.getOp() == ast.ExprBinOp.BinOp_LogAnd
    assert isinstance(e.getLhs(), ast.ExprIn) and isinstance(e.getRhs(), ast.ExprIn)
    assert e.getLhs().getCollection() is not None


def test_a_range_in_then_a_collection_in():
    e = _init(SRC, "c")
    assert isinstance(e, ast.ExprBin) and e.getOp() == ast.ExprBinOp.BinOp_LogOr
    assert isinstance(e.getLhs(), ast.ExprIn) and isinstance(e.getRhs(), ast.ExprIn)
