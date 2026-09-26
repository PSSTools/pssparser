"""A constraint `foreach` or `forall` iterator binds to its declaration
(known-issues SR-F1; symbol-resolution plan 8.8).

The lookup always found the iterator, but the path recorded for it did not
lead back there:
- a `foreach` was addressed as its body statements only, so the iterator's
  index landed on a body statement (`refs` reported the use as BUILTIN);
- an `if` branch, an implication and a `with` block pushed no frame, so a
  `foreach` in one was indexed against the enclosing list, and in a `with`
  block or a `randomize` the iterator was "left unbound ... a pssparser
  defect";
- `refs` keyed the `foreach` statement itself (and anything around it) by the
  iterator's name, and the `forall` iterator had no location.

A `foreach` is now addressed as "body statements, then iterators", and each
node that holds a constraint set is a step of the path (ConstraintScopes).
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


H = "import std_pkg::*;\n"


def markers(code):
    _, ms = parse_collect(H + code)
    return [(m["severity"], m["line"], m["message"]) for m in ms]


def bindings(code, *names):
    """(name, line of use, kind of declaration, line of declaration) for each
    use of one of `names`. Lines count from the first line of `code`."""
    p = pssparser.Parser()
    p.parses([("t.pss", H + code)])
    p.link()
    return [(o.text, o.line - 1, type(o.decl).__name__.lstrip("I"),
             o.decl_location.line - 1 if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text in names and not o.is_declaration]


def check(code, *names):
    assert markers(code) == []
    b = bindings(code, *names)
    assert b, "no uses of %s" % (names,)
    assert {k for (_, _, k, _) in b} == {"ConstraintStmtField"}, b
    return b


def test_the_sr_f1_repro():
    code = """\
struct S {
  rand bit[8] arr[4];
  constraint { foreach (e : arr) { arr[0] < 2; e < 10; } }
}
"""
    assert check(code, "e") == [("e", 3, "ConstraintStmtField", 3)]


def test_the_index_form():
    code = """\
struct S {
  rand bit[8] arr[4];
  constraint { foreach (arr[i]) { arr[0] < 2; arr[i] < i; } }
}
"""
    check(code, "i")


def test_both_iterators():
    code = """\
struct S {
  rand bit[8] arr[4];
  constraint { foreach (e : arr[i]) { e < i; } }
}
"""
    assert {n for (n, *_) in check(code, "e", "i")} == {"e", "i"}


def test_nested_foreach():
    code = """\
struct S {
  rand bit[8] a[4]; rand bit[8] b[4];
  constraint {
    foreach (e : a) {
      b[0] < 2;
      foreach (f : b) { f < e; }
    }
  }
}
"""
    assert check(code, "e", "f") == [
        ("f", 6, "ConstraintStmtField", 6), ("e", 6, "ConstraintStmtField", 4)]


def test_in_if_and_else_branches():
    code = """\
struct S {
  rand bit[8] x; rand bit[8] arr[4];
  constraint {
    x < 3;
    if (x > 1) { x < 2; foreach (e : arr) { x < 1; e < 10; } }
    else { foreach (g : arr) { g > 1; } }
  }
}
"""
    check(code, "e", "g")


def test_in_an_implication():
    code = """\
struct S {
  rand bit[8] x; rand bit[8] arr[4];
  constraint { x < 3; x > 1 -> { x < 2; foreach (e : arr) { e < 10; } } }
}
"""
    check(code, "e")


def test_in_a_named_dynamic_and_extension_constraint():
    code = """\
struct S {
  rand bit[8] x; rand bit[8] arr[4];
  constraint c { x < 3; foreach (e : arr) { e < 10; } }
  dynamic constraint d { foreach (e : arr) { e < x; } }
}
extend struct S {
  constraint { x < 3; foreach (e : arr) { x < 1; e < 10; } }
}
"""
    check(code, "e")


def test_in_a_generic_constraint():
    """With its parameters, in and under nested scopes (8.7)."""
    code = """\
struct S {
  rand bit[8] x; rand bit[8] arr[4];
  constraint g(bit[8] v, bit[8] w) {
    if (v > 1) { v < 9; foreach (e : arr) { e < v; } } else { w < 2; }
    v > 0 -> { w < v; }
  }
  constraint { g(x, x); }
}
"""
    assert markers(code) == []
    kinds = {(n, k) for (n, _, k, _) in bindings(code, "e", "v", "w")}
    assert kinds == {("e", "ConstraintStmtField"),
                     ("v", "GenericConstraintParam"),
                     ("w", "GenericConstraintParam")}


def test_forall():
    code = """\
struct T { rand bit[8] y; }
component pss_top {
  action A { rand T t1; constraint { forall (it: T) { it.y < 3; } } }
}
"""
    # The use binds to the iterator, which is declared where it is written.
    assert check(code, "it") == [("it", 3, "ConstraintStmtField", 3)]


def test_in_a_traversal_with_block():
    code = """\
component pss_top {
  action B { rand bit[8] x; rand list<bit[8]> l; }
  action A {
    activity {
      do B with { x < 2; foreach (e : l) { x < 1; e < 3; } };
      do B with foreach (e : l) { e < 4; };
    }
  }
}
"""
    check(code, "e")


def test_in_an_activity_constraint():
    code = """\
component pss_top {
  action A {
    rand bit[8] arr[4];
    activity { constraint { foreach (e : arr) { e < 3; } } }
  }
}
"""
    check(code, "e")


def test_in_a_randomize_with_block():
    code = """\
struct S1 { rand list<bit[8]> l; rand bit[8] x; }
component pss_top {
  action A {
    rand list<bit[8]> l;
    S1 s;
    exec post_solve {
      randomize s with { x < 4; foreach (e : l) { x < 3; e < 3; } }
      randomize l with { foreach (f : l) { f < 3; } }
    }
  }
}
"""
    check(code, "e", "f")


def test_in_a_monitor_activity_constraint():
    code = """\
component pss_top {
  action A { rand bit[8] arr[4]; }
  monitor M { A a; activity { a; constraint { foreach (e : a.arr) { e < 3; } } } }
}
"""
    check(code, "e")
