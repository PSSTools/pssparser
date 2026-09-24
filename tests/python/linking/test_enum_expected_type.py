"""Unqualified enum items and the expected type (symbol-resolution plan 8.1, F22).

18.3 a: where an expression's expected type is an enumeration type, its items
are searched before any lexical scope. 8.4.3 says where an expression has one:
the left side of an assignment or initialization, a formal parameter, a return
type, the left side of `==`/`!=` and of `in`, a cast's target type, and a
`?:` (both arms). Plan 8.1 adds `match` choices and `dist` items, which test
their values against the left side as `in` does.

Decision Q2 reads `==`/`!=` both ways for an unqualified item, as Ex. 272's
prose does: `A == op.mode` is legal. Where both sides are bare names and each
would be read as an item of the other's type, the comparison is ambiguous
(PSS045). Where the item hides a field or variable the name also has, that is
a warning (PSS044).

Enum items found lexically, with no expected type, still resolve: retiring
that is 8.2.
"""
import pytest

import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m["severity"], m["message"]) for m in ms]


def errors(code):
    return [msg for sev, msg in markers(code) if sev == "error"]


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


# ---------------------------------------------------------------------------
# The LRM examples
# ---------------------------------------------------------------------------


def test_ex272_items_of_an_enum_declared_in_another_component():
    """Ex. 272: `mode_e` is not visible in `test`; its items are found
    through the type of `op.mode`."""
    code = """\
component my_ip_c {
  enum mode_e {A, B, C, D};
  action my_op { rand mode_e mode; }
}
component pss_top {
  my_ip_c my_ip;
  action test {
    my_ip_c::my_op op;
    constraint op.mode == my_ip_c::mode_e::A;
    constraint op.mode == A;
    constraint op.mode in [A, C, D];
    activity { op; }
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "A") == [(9, "EnumItem", 2), (10, "EnumItem", 2),
                                   (11, "EnumItem", 2)]


def test_ex37_the_legal_lines():
    assert errors("""
enum color_e {RED, GREEN, ORANGE};
function void print_color(color_e c);
function void print_num(int n);
component pss_top {
  enum fruit_e {APPLE, ORANGE};
  exec init_down {
    color_e c = ORANGE;
    print_color(RED);
    print_num((int)fruit_e::ORANGE);
  }
}
""") == []


def test_ex37_an_initializer_picks_the_expected_enum():
    """`ORANGE` is an item of both enums; the declared type decides."""
    code = """\
enum color_e {RED, GREEN, ORANGE};
component pss_top {
  enum fruit_e {APPLE, ORANGE};
  exec init_down {
    color_e c = ORANGE;
    fruit_e f = ORANGE;
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "ORANGE") == [(5, "EnumItem", 1), (6, "EnumItem", 3)]


# ---------------------------------------------------------------------------
# Each 8.4.3 context
# ---------------------------------------------------------------------------

REMOTE = """\
component c1 {
  enum mode_e {A, B, C};
  function mode_e get();
  function void set(mode_e m);
  action act { rand mode_e m; }
}
"""


@pytest.mark.parametrize("stmt", [
    "sub.set(A);",                          # a formal parameter
    "c1::mode_e m = A;",                    # an initialization
    "c1::mode_e m; m = B;",                 # an assignment
    "if (sub.get() == C) { }",              # == with a call on the left
    "if (sub.get() != C) { }",
    "if (A == sub.get()) { }",              # the other way round (Q2)
    "if (sub.get() in [A, B..C]) { }",      # in, with a range
    "c1::mode_e m = (c1::mode_e)B;",        # a cast
    "c1::mode_e m = (sub.get() == A) ? B : C;",  # ?: arms
    "match (sub.get()) { [A]: { } [B, C]: { } }",
    "mode_t m = C;",                        # through a typedef
])
def test_an_exec_context_gives_the_expected_type(stmt):
    assert errors(REMOTE + """
component pss_top {
  typedef c1::mode_e mode_t;
  c1 sub;
  exec init_down { %s }
}
""" % stmt) == []


def test_a_return_type_is_the_expected_type():
    assert errors("""
component pss_top {
  enum mode_e {A, B};
  function mode_e f() { return B; }
}
""") == []


def test_a_parameter_default_expects_its_type():
    assert errors(REMOTE + """
component pss_top {
  function void f(c1::mode_e m = A) { }
}
""") == []


def test_a_field_initializer_expects_its_type():
    assert errors(REMOTE + """
component pss_top {
  c1::mode_e m = B;
}
""") == []


def test_a_handle_initializer_expects_the_members_type():
    assert errors(REMOTE + """
component pss_top {
  c1 sub;
  action t {
    c1::act a;
    activity { a with { m == B; }; }
  }
}
""") == []


def test_dist_items_expect_the_left_sides_type():
    assert errors(REMOTE + """
component pss_top {
  c1 sub;
  action t {
    c1::act a;
    constraint { dist a.m in [A := 1, B..C := 2]; }
    activity { a; }
  }
}
""") == []


def test_an_activity_match_choice_expects_the_match_type():
    assert errors(REMOTE + """
component pss_top {
  c1 sub;
  action t {
    c1::act a;
    activity {
      a;
      match (a.m) { [A]: { } [B, C]: { } }
    }
  }
}
""") == []


def test_an_argument_through_a_member_call():
    """Report E, f22_func: the formal is declared in another component."""
    assert errors("""
component c1 { enum mode_e {A, B}; function void f(mode_e m); }
component pss_top {
  c1 sub;
  exec init_down { sub.f(A); }
}
""") == []


def test_the_expected_type_does_not_reach_inside_an_operand():
    """Only the operand itself expects the type: `A + 1` is arithmetic."""
    errs = errors(REMOTE + """
component pss_top {
  c1 sub;
  exec init_down { if (sub.get() == (A + 1)) { } }
}
""")
    assert len(errs) == 1 and errs[0].startswith("unknown identifier 'A'")


def test_an_int_parameter_expects_no_enum():
    """Ex. 37: `print_num(ORANGE)` has no enum expected, so an item that is
    not visible lexically is unknown."""
    errs = errors(REMOTE + """
function void print_num(int n);
component pss_top {
  exec init_down { print_num(A); }
}
""")
    assert len(errs) == 1 and errs[0].startswith("unknown identifier 'A'")


# ---------------------------------------------------------------------------
# Precedence: step a before the lexical steps
# ---------------------------------------------------------------------------


def test_the_item_hides_a_field_of_the_same_name():
    """Report E, f22_prec: 18.3 a picks the item, and warns."""
    code = """\
enum mode_e {A, B};
component pss_top {
  action T {
    rand mode_e m;
    rand bit[8] A;
    constraint m == A;
  }
}
"""
    assert markers(code) == [(
        "warning",
        "'A' is read as the enum item mode_e::A, which hides the field 'A' "
        "(18.3 a); qualify one of them")]
    assert bindings(code, "A") == [(6, "EnumItem", 1)]


def test_the_expected_enum_decides_between_two_enums():
    """Report E, f22_twoenums: both enums declare `A`."""
    code = """\
enum e1 {A, B};
enum e2 {A, C};
component pss_top {
  action T {
    rand e1 x; rand e2 y;
    constraint x == A;
    constraint y == A;
    constraint y == C;
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "A") == [(6, "EnumItem", 1), (7, "EnumItem", 2)]


def test_a_bare_name_on_the_left_expects_the_rights_type():
    code = """\
enum e1 {A, B};
enum e2 {A, C};
component pss_top {
  action T {
    rand e2 y;
    constraint A == y;
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "A") == [(6, "EnumItem", 2)]


def test_an_enum_in_the_base_component():
    """Report E, enum_base (N6)."""
    assert errors("""
component base_c { enum m_e {X1, X2}; }
component pss_top : base_c {
  action T { rand m_e m; constraint m == X1; }
}
""") == []


# ---------------------------------------------------------------------------
# Ambiguity (decision Q2)
# ---------------------------------------------------------------------------


def test_two_bare_names_each_an_item_of_the_others_type():
    """`A == B`: either `B` is e1::B (compared with the field `A`), or `A`
    is e2::A (compared with the field `B`)."""
    assert errors("""
enum e1 {X, B};
enum e2 {A, Y};
component pss_top {
  action T {
    rand e1 A;
    rand e2 B;
    constraint A == B;
  }
}
""") == [
        "ambiguous comparison of 'A' and 'B': either 'A' is e2::A or 'B' is "
        "e1::B; qualify the enum item (8.4.3, 18.3 a)"]


def test_two_fields_of_one_enum_are_not_ambiguous():
    assert errors("""
enum e1 {A, B};
component pss_top {
  action T {
    rand e1 x;
    rand e1 y;
    constraint x == y;
    constraint x == A;
    constraint A == B;
  }
}
""") == []
