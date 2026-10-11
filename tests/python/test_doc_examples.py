"""The Python examples in the hand-written AST guides run.

Those pages once described an API that did not exist (``expr.lhs`` for
``expr.getLhs()``, ``node.children`` for ``node.getChildren()``, fields such
as ``ActivityDecl.activity`` that the schema never had) -- known issue AS-11.
This runs every ``.. code-block:: python`` of each page, in page order and in
one namespace, against a small model, with the names the prose assumes
(``action``, ``ast_root``, ``elem``, ...) bound to real nodes. A block that
raises fails the test.

Where a field is spelled in each API is generated from ast/*.yaml in the AST
model reference (docs/ast/); these pages are the narrative around it.
"""
from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest

import pssparser.ast as ast
from pssparser import Parser

ROOT = Path(__file__).resolve().parents[2]

PAGES = ["ast_usage_guide.rst", "ast_class_hierarchy.rst", "pss30_api.rst"]

SAMPLE = """\
import std_pkg::*;
component pss_top {
    action sub_a { rand bit[8] v; }
    action my_action {
        rand bit[8] value;
        rand bit[8] arr[4];
        int count;
        sub_a a1, a2;
        constraint c1 {
            value >= 10;
            value + 0 < 200;
            foreach (arr[i]) { arr[i] < 5; }
            if (value > 3) { count == 1; }
        }
        activity {
            a1;
            parallel { a2; }
            repeat (2) { a1; }
            atomic { a2; }
        }
    }
    monitor m1 {
        sub_a x;
        activity { concat { x; x; } }
    }
    exec init_down {
        string s = "hello";
        int n = s.size();
        int k;
        randomize k with { k < 3; };
    }
}
"""


def _find(node, cls):
    out = []

    def walk(n):
        if isinstance(n, cls):
            out.append(n)
        if hasattr(n, "getChildren"):
            for c in n.getChildren():
                walk(c)

    walk(node)
    return out


class _Collect(ast.VisitorBase):
    """Binds the names the fragments assume to a node of each kind."""

    def __init__(self):
        super().__init__()
        self.names = {}

    def visitExprMemberPathElem(self, i):
        self.names.setdefault("elem", i)
        super().visitExprMemberPathElem(i)

    def visitProceduralStmtRandomize(self, i):
        self.names["stmt"] = i
        super().visitProceduralStmtRandomize(i)

    def visitActivityAtomicBlock(self, i):
        self.names["atomic"] = i
        super().visitActivityAtomicBlock(i)


def _blocks(page):
    text = (ROOT / "docs" / page).read_text()
    for m in re.finditer(r"\.\. code-block:: python\n\n((?:(?:    .*)?\n)+)", text):
        code = "\n".join(l[4:] for l in m.group(1).split("\n"))
        yield text[:m.start()].count("\n") + 1, code


@pytest.mark.parametrize("page", PAGES)
def test_python_examples_run(page):
    p = Parser()
    p.parses([("sample.pss", SAMPLE)])
    root = p.link()
    (unit,) = p.user_units()
    action = next(a for a in _find(unit, ast.Action) if a.getName().getId() == "my_action")
    collect = _Collect()
    unit.accept(collect)
    context = dict(collect.names, action=action, monitor=_find(unit, ast.Monitor)[0],
                   content1="component pss_top { }", content2="component pss_top { }")
    ns = dict(context, ast=ast, ast_root=unit, root=root, parser=p, Parser=Parser)

    blocks = list(_blocks(page))
    assert blocks, "no python examples found in %s" % page
    failures = []
    for line, code in blocks:
        ns.update(context)          # a block may reuse one of the names
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(code, "docs/%s:%d" % (page, line), "exec"), ns)
        except Exception as e:      # noqa: BLE001 -- report every block
            failures.append("docs/%s:%d: %s: %s" % (page, line, type(e).__name__, e))
    assert not failures, "\n".join(failures)
