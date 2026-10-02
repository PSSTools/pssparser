"""Comments on activity statements (sphinx-pss request, 2026-09-29: AC1-AC5).

`docs/comments.rst` promises comments on every ScopeChild, but no activity
statement carried any: procedural statements are built through mkExecStmt,
which attaches them, and activity statements through mkActivityStmt, which did
not. sphinx-pss reads `/// Step:` markers from activities to label regions
of its activity diagrams.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import pssparser.ast as pss_ast  # noqa: E402
from pssparser import Parser  # noqa: E402
from activity_walk import activity_nodes  # noqa: E402

LEADING = pss_ast.CommentPlacement.CommentPlacement_Leading
TRAILING = pss_ast.CommentPlacement.CommentPlacement_Trailing

_LIVE = []


def _activity(src, collect=True):
    """The first ActivityDecl in `src`, parsed and linked."""
    p = Parser(collect_docstrings=collect, collect_comments=collect)
    p.parses([("t.pss", src)])
    root = p.link()
    _LIVE.append((p, root))

    def find(n):
        if type(n).__name__ == "ActivityDecl":
            return n
        if hasattr(n, "numChildren"):
            for i in range(n.numChildren()):
                r = find(n.getChild(i))
                if r is not None:
                    return r
        if type(n).__name__ == "SymbolTypeScope":
            return find(n.getTarget())
        return None

    act = find(root)
    assert act is not None
    return act


def _wrap(body, fields="A a1, a2; B b1; rand int c; rand int arr[4];"):
    return ("component C {\n"
            "    action A { rand int x; }\n"
            "    action B { rand int y; }\n"
            "    action Top {\n"
            f"        {fields}\n"
            "        activity {\n"
            f"{body}\n"
            "        }\n"
            "    }\n"
            "}\n")


def _comments(node, placement=None):
    return [c.getText().strip() for c in node.getComments()
            if placement is None or c.getPlacement() == placement]


def _at(act, line, kind=None):
    """The activity node on `line` (the first, or the first of `kind`)."""
    for n in activity_nodes(act):
        if n.getLocation().lineno == line and (kind is None or type(n).__name__ == kind):
            return n
    raise AssertionError(f"no {kind or 'node'} on line {line}")


# The request's fixture (sphinx-pss-requests-2026-09-29.md, section 1), plus
# a do-while for AC5.
FIXTURE = """package p {
  component C {
    action A { rand int x; }
    action B { rand int y; }
    action Top {
      A a1, a2;
      B b1;
      rand int c;
      rand int arr[4];
      activity {
        /// Step: Configure the channel
        /// More detail on configuring.
        lbl_seq: sequence {
          /// Step: first
          a1;
          b1; /// Step: trailing
        }
        /// Step: Pick a path
        if (c > 1) {
          /// Step: then-branch
          a1;
        } else { b1; }
        /** Step: Run both */
        parallel join_first (1) { a1; b1; }
        select {
          /// Step: branch one
          (c > 2) [3]: a1;
          b1;
        }
        match (c) {
          /// Step: small
          [0..3]: a1;
          default: b1;
        }
        repeat (c) { /// Step: in loop
          a1; }
        // A plain comment
        do A with { x == 1; };
        /// Step: bind them
        bind a1.x a2.x;
        repeat {
          a1;
        } while (c > 0); /// Step: after
        /// Step: closing
      }
    }
  }
}
"""


# --------------------------------------------------------------------------
# AC1: statement comments

@pytest.mark.parametrize("line,kind,text,placement", [
    (13, "ActivitySequence", "Step: Configure the channel", LEADING),
    (15, "ActivityActionHandleTraversal", "Step: first", LEADING),
    (16, "ActivityActionHandleTraversal", "Step: trailing", TRAILING),
    (19, "ActivityIfElse", "Step: Pick a path", LEADING),
    (21, "ActivityActionHandleTraversal", "Step: then-branch", LEADING),
    (24, "ActivityParallel", "Step: Run both", LEADING),
    (35, "ActivityRepeatCount", "Step: in loop", TRAILING),
    (38, "ActivityActionTypeTraversal", "A plain comment", LEADING),
    (40, "ActivityBindStmt", "Step: bind them", LEADING),
])
def test_each_statement_carries_its_comment(line, kind, text, placement):
    n = _at(_activity(FIXTURE), line, kind)
    got = _comments(n, placement)
    assert any(text in t for t in got), (kind, _comments(n))


def test_a_triple_slash_run_is_one_comment_per_line():
    seq = _at(_activity(FIXTURE), 13, "ActivitySequence")
    got = _comments(seq, LEADING)
    assert len(got) == 2 and "Configure" in got[0] and "More detail" in got[1], got


def test_a_doc_comment_fills_doc_raw():
    seq = _at(_activity(FIXTURE), 13, "ActivitySequence")
    assert "Step: Configure the channel" in seq.getDocRaw()


def test_a_comment_above_an_annotated_statement_lands_on_the_statement():
    act = _activity("annotation a { }\n" + _wrap(
        "            /// Step: x\n"
        "            @a\n"
        "            a1;\n"
        "            b1;"))
    stmts = [n for n in activity_nodes(act)
             if type(n).__name__ == "ActivityActionHandleTraversal"]
    assert any("Step: x" in t for t in _comments(stmts[0])), _comments(stmts[0])
    assert not _comments(stmts[1])


def test_each_comment_is_attached_once():
    act = _activity(FIXTURE)
    seen = []
    for n in [act] + activity_nodes(act):
        seen += _comments(n)
        if hasattr(n, "getTrailing_comments"):
            seen += [c.getText().strip() for c in n.getTrailing_comments()]
    dups = sorted({t for t in seen if seen.count(t) > 1})
    assert not dups, dups


def test_nothing_is_attached_when_collection_is_off():
    act = _activity(FIXTURE, collect=False)
    assert all(not _comments(n) for n in activity_nodes(act))


# --------------------------------------------------------------------------
# AC2: closing comments

def test_the_activity_closing_comment_lands_on_the_activity():
    act = _activity(FIXTURE)
    closing = [c.getText().strip() for c in act.getTrailing_comments()]
    assert any("Step: closing" in t for t in closing), closing
    assert not any("Step: closing" in t
                   for n in activity_nodes(act) for t in _comments(n))


@pytest.mark.parametrize("block,kind", [
    ("sequence {\n                a1;\n                /// end\n            }", "ActivitySequence"),
    ("{\n                a1;\n                /// end\n            }", "ActivitySequence"),
    ("parallel {\n                a1;\n                /// end\n            }", "ActivityParallel"),
    ("schedule {\n                a1;\n                /// end\n            }", "ActivitySchedule"),
    ("select {\n                a1;\n                b1;\n                /// end\n            }", "ActivitySelect"),
    ("match (c) {\n                [0]: a1;\n                default: b1;\n                /// end\n            }",
     "ActivityMatch"),
])
def test_a_closing_comment_lands_on_its_block(block, kind):
    act = _activity(_wrap("            " + block))
    n = [x for x in activity_nodes(act) if type(x).__name__ == kind][0]
    assert any("end" in c.getText() for c in n.getTrailing_comments()), kind
    assert not any("end" in t for x in activity_nodes(act) for t in _comments(x))


def test_a_closing_comment_in_atomic_lands_on_its_body():
    act = _activity(_wrap("            atomic {\n"
                          "                a1;\n"
                          "                /// end\n"
                          "            }"))
    atomic = [x for x in activity_nodes(act) if type(x).__name__ == "ActivityAtomicBlock"][0]
    assert any("end" in c.getText() for c in atomic.getBody().getTrailing_comments())


def test_a_comment_on_the_last_statements_line_stays_on_the_statement():
    act = _activity(_wrap("            sequence {\n"
                          "                a1; // mine\n"
                          "            }"))
    seq = [x for x in activity_nodes(act) if type(x).__name__ == "ActivitySequence"][0]
    a1 = [x for x in activity_nodes(seq)][0]
    assert _comments(a1, TRAILING) == ["mine"]
    assert not list(seq.getTrailing_comments())


# --------------------------------------------------------------------------
# AC3: select branches and match choices

@pytest.mark.parametrize("branch", [
    "(c > 2) [3]: a1;",
    "[3]: a1;",
    "a1;",
])
def test_a_comment_above_a_select_branch_lands_on_its_body(branch):
    act = _activity(_wrap("            select {\n"
                          "                /// Step: this one\n"
                          f"                {branch}\n"
                          "                b1;\n"
                          "            }"))
    sel = [x for x in activity_nodes(act) if type(x).__name__ == "ActivitySelect"][0]
    body = sel.getBranche(0).getBody()
    assert any("this one" in t for t in _comments(body)), _comments(body)
    assert not _comments(sel.getBranche(1).getBody())


@pytest.mark.parametrize("choice,idx", [("[0..3]: a1;", 0), ("default: b1;", 1)])
def test_a_comment_above_a_match_choice_lands_on_its_body(choice, idx):
    other = "default: b1;" if idx == 0 else "[0..3]: a1;"
    lines = [other, "/// Step: this one\n                " + choice]
    if idx == 0:
        lines.reverse()
    act = _activity(_wrap("            match (c) {\n"
                          + "".join(f"                {l}\n" for l in lines)
                          + "            }"))
    m = [x for x in activity_nodes(act) if type(x).__name__ == "ActivityMatch"][0]
    body = m.getChoice(idx).getBody()
    assert any("this one" in t for t in _comments(body)), _comments(body)


def test_a_trailing_comment_on_a_branch_stays_trailing():
    act = _activity(_wrap("            select {\n"
                          "                (c > 2): a1; // note\n"
                          "                b1;\n"
                          "            }"))
    sel = [x for x in activity_nodes(act) if type(x).__name__ == "ActivitySelect"][0]
    assert _comments(sel.getBranche(0).getBody(), TRAILING) == ["note"]


# --------------------------------------------------------------------------
# Geometry parity, and AC5

def _procedural(body):
    p = Parser(collect_docstrings=True, collect_comments=True)
    p.parses([("t.pss", "function void w(int i);\n"
                        "function void f(int c) {\n" + body + "\n}\n")])
    root = p.link()
    _LIVE.append((p, root))
    def first(n):
        name = type(n).__name__
        if name.startswith("ProceduralStmt") and name != "ProceduralStmtDataDeclaration":
            return n
        kids = [n.getChild(i) for i in range(n.numChildren())] if hasattr(n, "numChildren") else []
        for k in kids:
            r = first(k)
            if r is not None:
                return r
        return None

    for i in range(root.numChildren()):
        s = root.getChild(i)
        if type(s).__name__ == "SymbolFunctionScope" and s.getName() == "f":
            stmt = first(s.getBody())
            assert stmt is not None
            return stmt
    raise AssertionError("f not found")


def test_a_comment_after_a_repeat_brace_lands_alike_in_both():
    proc = _procedural("    repeat (c) { // note\n        w(1); }")
    act = _activity(_wrap("            repeat (c) { // note\n                a1; }"))
    rep = [x for x in activity_nodes(act) if type(x).__name__ == "ActivityRepeatCount"][0]
    assert _comments(proc, TRAILING) == _comments(rep, TRAILING) == ["note"]
    assert not _comments(rep.getBody())


def test_ac5_a_do_while_trailing_comment_procedural():
    stmt = _procedural("    repeat {\n        w(1);\n    } while (c > 0); // after")
    assert type(stmt).__name__ == "ProceduralStmtRepeatWhile"
    assert _comments(stmt, TRAILING) == ["after"]


def test_ac5_a_do_while_trailing_comment_activity():
    rep = _at(_activity(FIXTURE), 41, "ActivityRepeatWhile")
    assert any("Step: after" in t for t in _comments(rep, TRAILING)), _comments(rep)


def test_ac5_a_multi_line_call_keeps_its_trailing_comment():
    stmt = _procedural("    w(\n        1); // split")
    assert _comments(stmt, TRAILING) == ["split"]
