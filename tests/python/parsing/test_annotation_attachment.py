"""Where an element annotation attaches, and that it is checked there.

LRM 7.13: an element annotation "is attached to the next PSS model element
declared in the scope. It is an error if no subsequent element is present in
the scope."  Source waivers (docs/design/source-waivers.md W2) attach to these
nodes, so each annotatable statement must own its annotation and carry a
location.  These are lint-framework-plan F2.0, source-waivers W0-a/b/c:

* W0-a: an annotation on an activity statement attached to the enclosing
  ``ActivityDecl``; one on a procedural statement attached to the enclosing
  function; one on a compound constraint (``if``, ``foreach``, ``->``) to the
  first item in its body.
* W0-b: a ``constraint c { ... }`` block, a function definition, a
  procedural statement, an ``import`` and an action handle had no end
  location; a waiver on one covered nothing past its first token.
* W0-c: an annotation on ``import`` linked with PSS042 ("left unbound ... a
  pssparser defect"), and a standalone annotation counted as the first
  declaration for the import-order warning (LINT402).

Also pinned: an annotation left at the end of a statement body is reported
(it used to slide onto the next statement, or onto the enclosing
declaration), and an annotation on a compound procedural statement is
resolved (it was never visited: PSS042).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pssparser import Parser, ParseException  # noqa: E402
from test_helpers import parse_collect  # noqa: E402

PRE = 'import std_pkg::*;\nannotation note_s { string text; }\n'
ANN = '@note_s {.text = "x"}'

def _annotated(parser):
    """(class name, source text of the node's extent) for every annotated node.

    A visitor that overrides every ``visitX``: dispatch calls the most-derived
    method first, then chains up to the base classes, so the first ``visitX``
    to see an annotated node names its class. Nodes are keyed by location
    (each accessor returns a fresh wrapper, so ``id()`` is no key).
    """
    import pssparser.ast as A
    src = parser._test_src.split("\n")
    out, seen = [], set()

    def text(n):
        b, e = n.getLocation(), n.getEndLocation()
        if b.lineno < 1:
            return "<no location>"
        if e.lineno == b.lineno and e.linepos > 0:
            return src[b.lineno - 1][b.linepos - 1:e.linepos].strip()
        return src[b.lineno - 1][b.linepos - 1:].strip()

    class V(A.VisitorBase):
        pass

    def make(name):
        def f(self, i):
            anns = getattr(i, "getAnnotations", None)
            if anns is not None and list(anns()):
                b, e = i.getLocation(), i.getEndLocation()
                key = (b.lineno, b.linepos, e.lineno, e.linepos)
                if key not in seen:
                    seen.add(key)
                    out.append((name[5:], text(i)))
            return getattr(A.VisitorBase, name)(self, i)
        return f

    for name in dir(A.VisitorBase):
        if name.startswith("visit"):
            setattr(V, name, make(name))

    v = V()
    for unit in parser.user_units():
        unit.accept(v)
    return out


def _parse(body):
    src = PRE + body.replace("@A", ANN)
    p = Parser()
    p._test_src = src
    p.parses([("t.pss", src)])
    return p


def _link_clean(body):
    p = _parse(body)
    p.link()
    msgs = [m for m in p.markers if m["severity"] in ("error", "warning")]
    assert not msgs, msgs
    return p


# ---------------------------------------------------------------------------
# W0-a: statements own their annotations
# ---------------------------------------------------------------------------

ATTACH = {
    # Activity statements
    "activity_traversal": (
        "component C { action A {} action B { activity { @A do A; } } }",
        ("ActivityActionTypeTraversal", "do A;")),
    "activity_labeled": (
        "component C { action A {} action B { activity { @A L: do A; } } }",
        ("ActivityActionTypeTraversal", "do A;")),
    "activity_sequence": (
        "component C { action A {} action B { activity { @A sequence { do A; } } } }",
        ("ActivitySequence", "sequence { do A; }")),
    "activity_nested": (
        "component C { action A {} action B { activity { sequence { @A do A; do A; } } } }",
        ("ActivityActionTypeTraversal", "do A;")),
    "activity_repeat": (
        "component C { action A {} action B { activity { @A repeat (2) { do A; } } } }",
        ("ActivityRepeatCount", "repeat (2) { do A; }")),
    "activity_handle_traversal": (
        "component C { action A {} action B { A a; activity { @A a; } } }",
        ("ActivityActionHandleTraversal", "a;")),
    "activity_whole": (
        "component C { action A {} action B { @A activity { do A; } } }",
        ("ActivityDecl", "activity { do A; }")),
    # Procedural statements (21.6.1, Example 323)
    "proc_call": (
        "component C { function void g() {} function void f() { @A g(); } }",
        ("ProceduralStmtExpr", "g();")),
    "proc_assignment": (
        "component C { function void f() { int a; @A a = 1; } }",
        ("ProceduralStmtAssignment", "a = 1;")),
    "proc_data_declaration": (
        "component C { function void f() { @A int a, b; } }",
        ("ProceduralStmtDataDeclaration", "int a, b;")),
    "proc_if": (
        "component C { function void f() { int a; @A if (a > 0) { a = 1; } } }",
        ("ProceduralStmtIfElse", "if (a > 0) { a = 1; }")),
    "proc_nested": (
        "component C { function void f() { int a; repeat (2) { @A a = 1; } } }",
        ("ProceduralStmtAssignment", "a = 1;")),
    "proc_exec_body": (
        "component C { action A { int a; exec post_solve { @A a = 1; } } }",
        ("ProceduralStmtAssignment", "a = 1;")),
    "function_whole": (
        "component C { @A function void f() { int a; a = 1; } }",
        ("FunctionDefinition", "function void f() { int a; a = 1; }")),
    "exec_whole": (
        "component C { action A { int a; @A exec post_solve { a = 1; } } }",
        ("ExecBlock", "exec post_solve { a = 1; }")),
    # Constraint items
    "constraint_if": (
        "struct S { int a; constraint c { @A if (a > 0) { a < 5; } } }",
        ("ConstraintStmtIf", "if (a > 0) { a < 5; }")),
    "constraint_foreach": (
        "struct S { int a[2]; constraint c { @A foreach (a[i]) { a[i] > 0; } } }",
        ("ConstraintStmtForeach", "foreach (a[i]) { a[i] > 0; }")),
    "constraint_implication": (
        "struct S { int a; constraint c { @A a > 0 -> a < 5; } }",
        ("ConstraintStmtImplication", "a > 0 -> a < 5;")),
    "constraint_expr": (
        "struct S { int a; constraint c { @A a > 0; } }",
        ("ConstraintStmtExpr", "a > 0;")),
}


@pytest.mark.parametrize("case", sorted(ATTACH))
def test_annotation_attaches_to_the_element_that_follows(case):
    body, expected = ATTACH[case]
    p = _link_clean(body)
    assert _annotated(p) == [expected]


# ---------------------------------------------------------------------------
# W0-b: a constraint block has an extent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("decl", [
    "constraint c { a > 0; a < 9; }",
    "dynamic constraint c { a > 0; }",
])
def test_constraint_block_has_an_end_location(decl):
    p = _link_clean("struct S { int a; @A %s }" % decl)
    assert _annotated(p) == [("ConstraintBlock", decl)]


# ---------------------------------------------------------------------------
# An annotation with nothing after it in a body is an error (7.13)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body", [
    "component C { action A {} action B { activity { do A; @A } } }",
    "component C { action A {} action B { activity { sequence { do A; @A } do A; } } }",
    "component C { function void f() { int a; a = 1; @A } }",
    "component C { function void f() { int a; repeat (2) { a = 1; @A } a = 2; } }",
    "component C { action A { int a; exec post_solve { a = 1; @A } } }",
    "struct S { int a; constraint c { if (a > 0) { a < 5; @A } a > 1; } }",
    "struct S { int a; constraint c { a > 1; @A } }",
], ids=["activity", "sequence", "function", "repeat", "exec", "constraint_if",
        "constraint_block"])
def test_annotation_at_the_end_of_a_body_is_reported(body):
    with pytest.raises(ParseException) as exc:
        _parse(body)
    assert "has no subsequent element in this scope" in str(exc.value)


# ---------------------------------------------------------------------------
# Annotations on statements are resolved, and reported once
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stmt", [
    "if (a > 0) { a = 1; }",
    "repeat (2) { a = 1; }",
    "while (a > 0) { a = 1; }",
    "{ a = 1; }",
    "match (a) { [0]: { a = 1; } }",
])
def test_annotation_on_a_compound_procedural_statement_is_resolved(stmt):
    _link_clean("component C { function void f() { int a; @A %s } }" % stmt)


@pytest.mark.parametrize("stmt", ["a = 1;", "if (a > 0) { a = 1; }"])
def test_bad_annotation_parameter_on_a_statement_is_reported_once(stmt):
    _, markers = parse_collect(PRE + "component C { function void f() { int a; "
                               "@note_s {.nosuch = \"x\"} %s } }" % stmt)
    errs = [m for m in markers if m["severity"] == "error"]
    assert [(m.get("code"), m["message"]) for m in errs] == [
        ("PSS002", "unknown identifier 'nosuch' in annotation type 'note_s'")]


# ---------------------------------------------------------------------------
# W0-c: imports
# ---------------------------------------------------------------------------

def test_annotation_on_an_import_is_resolved():
    p = _link_clean("package lib { struct s {} }\n"
                    "package p { @A import lib::*; struct t {} }")
    assert _annotated(p) == [("PackageImportStmt", "import lib::*;")]


def _warnings(body):
    _, markers = parse_collect(PRE + body.replace("@A", ANN))
    return [m.get("code") for m in markers if m["severity"] == "warning"]


def test_unknown_annotation_on_an_import_is_disregarded_with_a_warning():
    assert _warnings("package lib { struct s {} }\n"
                     "package p { @nosuch_s {.t = 1} import lib::*; struct t {} }") == ["LINT403"]


def test_standalone_annotation_before_an_import_is_not_a_declaration():
    _link_clean("package lib { struct s {} }\n"
                "package p { @A; import lib::*; struct t {} }")


def test_a_declaration_before_an_import_still_warns():
    assert _warnings("package lib { struct s {} }\n"
                     "package p { @A; struct t {} import lib::*; }") == ["LINT402"]
