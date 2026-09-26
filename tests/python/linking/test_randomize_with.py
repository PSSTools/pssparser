"""`randomize x with { ... }` (13.4.6; symbol-resolution plan 8.8, F15 and O-4).

The `with` block of a single struct-typed target resolves as an inline `with`
does: the target type's members first, then the enclosing scope (Ex. 161). It
used to resolve lexically only, so Ex. 161's `soft x` was "unknown
identifier". With several targets, or a target that is not a struct, the block
resolves lexically (Ex. 177). Every target is kept and resolved; only the
first used to be.
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m["severity"], m["line"], m["message"]) for m in ms]


def bindings(code, name):
    """(line of use, kind of declaration, line of declaration) for each use
    of `name`."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.line, type(o.decl).__name__.lstrip("I"),
             o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text == name and not o.is_declaration]


S = """\
struct S1 { rand bit[32] x; constraint soft x > 10; }
struct S2 : S1 { constraint soft x in [5..9]; }
"""


def test_example_161_the_targets_members_first():
    code = S + """\
component pss_top {
  action Entry {
    rand S1 f1;
    rand S2 f2;
    exec post_solve {
      randomize f2 with {
        soft x in [10, 20, 30];
        soft x < f1.x;
      }
    }
  }
}
"""
    assert markers(code) == []
    # `x` is f2's (inherited from S1); `f1` is the action's field.
    assert bindings(code, "x") == [
        (1, "Field", 1), (2, "Field", 1),
        (9, "Field", 1), (10, "Field", 1), (10, "Field", 1)]
    assert bindings(code, "f1") == [(10, "Field", 5)]


def test_example_177_several_targets():
    code = """\
struct S1 { rand bit[8] a, b; }
struct S2 { rand S1 f1; S1 f2; constraint f1.a < f2.a; }
component pss_top {
  action A {
    exec post_solve {
      S2 v1;
      bit[4] v2;
      v1.f2.a = 100;
      randomize v1, v2 with {v1.f1.a < v2;}
    }
  }
}
"""
    assert markers(code) == []
    # Both targets are resolved; the second used to be dropped.
    assert bindings(code, "v2") == [(9, "ProceduralStmtDataDeclaration", 7),
                                    (9, "ProceduralStmtDataDeclaration", 7)]


def test_an_unknown_name_in_the_with_block():
    code = S + """\
component pss_top {
  action A {
    rand S2 f2;
    exec post_solve { randomize f2 with { nosuch < 3; } }
  }
}
"""
    assert markers(code) == [("error", 6, "unknown identifier 'nosuch'")]


def test_an_unknown_second_target():
    code = """\
struct S1 { rand bit[8] a; }
component pss_top {
  action A {
    exec post_solve { S1 v1; randomize v1, zz with { v1.a < 3; } }
  }
}
"""
    assert markers(code) == [
        ("error", 4, "unknown identifier 'zz'; did you mean 'S1'?")]


def test_several_targets_do_not_open_a_members_scope():
    """With two targets `a` would be ambiguous: it is not looked up in
    either."""
    code = """\
struct S1 { rand bit[8] a; }
component pss_top {
  action A {
    exec post_solve { S1 v1; S1 v2; randomize v1, v2 with { a < 3; } }
  }
}
"""
    assert markers(code) == [
        ("error", 4, "unknown identifier 'a'; did you mean 'S1'?")]


def test_a_scalar_target():
    code = """\
component pss_top {
  action A {
    exec post_solve { bit[8] idx; randomize idx with { idx in [1..4]; } }
  }
}
"""
    assert markers(code) == []


def test_an_element_target():
    code = """\
struct S1 { rand bit[8] a; }
component pss_top {
  action A {
    S1 arr[4];
    exec post_solve { randomize arr[1] with { a < 3; } }
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "a") == [(5, "Field", 1)]


def test_a_member_target():
    code = """\
struct S1 { rand bit[8] a; }
struct S2 { rand S1 f1; }
component pss_top {
  action A {
    S2 s;
    exec post_solve { randomize s.f1 with { a < 3; } }
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "a") == [(6, "Field", 1)]


def test_a_function_parameter_target():
    code = """\
struct S1 { rand bit[8] a; }
function void f(S1 p) { randomize p with { a < 3; } }
"""
    assert markers(code) == []
    assert bindings(code, "a") == [(2, "Field", 1)]

