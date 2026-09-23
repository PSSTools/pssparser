"""
An exception raised in a Python ``VisitorBase`` override must reach the
caller unchanged, and the traversal must stop there (pss-scrambler BUG-001).

The generated C++ ``PyBaseVisitor::visitX`` used to ignore the result of the
Python callback, so a raising override left the error indicator set and the
C++ walk carried on. The original exception was then replaced by whatever
broke next: ``SystemError: ... returned a result with an exception set``, or
an ``AttributeError`` naming a ``visit...`` method that plainly exists.

The fix is in pyastbuilder (pyext_gen_visitor.py): a NULL callback result
throws a C++ marker exception, and the entry points (``accept``,
``py_visitXBase``) are declared ``except +``, which re-raises the pending
Python error rather than inventing a new one.
"""
import pytest

import pssparser.ast as A
from pssparser import Parser

_LIVE = []

# The request's reproducer (two execs, two statements), plus a target-template
# exec followed by another exec -- the three variants it tabulates.
MODELS = {
    "one_ref": """
component pss_top {
  int a;
  exec init_down { a = 1; }
}
""",
    "two_execs": """
component pss_top {
  int a;
  exec init_down { a = 1; }
  exec init_up { a = 2; }
}
""",
    "template_then_exec": """
component pss_top {
  int a;
  exec body C = \"\"\" x({{a}}); \"\"\";
  exec init_up { a = 2; }
}
""",
}


def _units(code):
    p = Parser()
    p.parses([("repro.pss", code)])
    root = p.link()
    _LIVE.append((p, root))
    return p.user_units()


def _walk(visitor, code):
    for u in _units(code):
        u.accept(visitor)


@pytest.mark.parametrize("model", sorted(MODELS))
@pytest.mark.parametrize("exc", [ValueError, AttributeError, SystemExit,
                                 KeyboardInterrupt])
def test_exception_propagates_unchanged(model, exc):
    marker = exc("raised from visitExprRefPathContext")

    class V(A.VisitorBase):
        def visitExprRefPathContext(self, r):
            raise marker

    with pytest.raises(exc) as info:
        _walk(V(), MODELS[model])
    assert info.value is marker


@pytest.mark.parametrize("model", sorted(MODELS))
def test_traversal_stops_after_raise(model):
    calls = []

    class V(A.VisitorBase):
        def visitExprRefPathContext(self, r):
            calls.append("ref")
            raise ValueError("stop")

        def visitExprId(self, i):
            calls.append("id")
            super().visitExprId(i)

    with pytest.raises(ValueError):
        _walk(V(), MODELS[model])
    assert calls.count("ref") == 1
    assert calls[-1] == "ref"


def test_exception_raised_below_super_call():
    # The raise happens in a callback reached through super().visitX(), i.e.
    # through py_visitXBase, and must come out of the outer override too.
    seen = []

    class V(A.VisitorBase):
        def visitExecBlock(self, b):
            seen.append("exec")
            super().visitExecBlock(b)
            seen.append("after-super")  # must not run

        def visitExprRefPathContext(self, r):
            raise KeyError("inner")

    with pytest.raises(KeyError, match="inner"):
        _walk(V(), MODELS["two_execs"])
    assert seen == ["exec"]


def test_exception_caught_inside_override_does_not_leak():
    # Catching around super() is legitimate; the walk must then continue
    # normally, with no stale error left behind.
    refs = []

    class V(A.VisitorBase):
        def visitExecBlock(self, b):
            try:
                super().visitExecBlock(b)
            except ValueError:
                pass

        def visitExprRefPathContext(self, r):
            refs.append(r)
            raise ValueError("caught above")

    _walk(V(), MODELS["two_execs"])
    assert len(refs) == 2


def test_non_raising_visitor_walks_everything():
    ids = []

    class V(A.VisitorBase):
        def visitExprRefPathContext(self, r):
            ids.append(r)
            super().visitExprRefPathContext(r)

    for m in MODELS.values():
        _walk(V(), m)
    assert len(ids) >= 4
