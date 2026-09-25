"""
Declaration order (symbol-resolution plan WS9; LRM 18.2, 4.7.1.2).

9.1 -- inside blocks (18.2a/b, 4.7.1.2).

In an exec block, an activity block or a template string, a name is declared
from its declaration on. The symbol tables carry no position, so a use used to
bind to a local declared *after* it -- `x = 1; string x;` assigned the string,
not the field `x` that is in scope there (report G, o1_shadow).

A later declaration is now hidden, and the lookup carries on outward. When
nothing outer declares the name, the use is PSS002, "used before its
declaration". Type, package and global scopes are unaffected: a member may be
used before it is declared (Examples 261, 262).

9.2 -- constant initializers (18.2c/d) and type widths. Checked after
resolution, not at lookup: a type or package scope is not otherwise ordered,
and a qualified `p::C` never takes the lexical walk. PSS118 is an error; a
forward reference in a width is PSS119, a warning first (plan section 8).
Across files, the order the files are given in applies (decision Q8).
"""
import pytest

import pssparser
from pssparser import refs

from ..test_helpers import parse_collect, _assign_codes

from .test_activity_scopes import assert_links_and_binds


def errors(code):
    _, markers = parse_collect(code)
    return [(m["line"], m.get("code"), m["message"])
            for m in markers if m["severity"] == "error"]


def use_before_decl(code):
    """(line, name) of each use-before-declaration error."""
    ret = []
    for line, code_id, msg in errors(code):
        assert code_id == "PSS002", msg
        assert "used before its declaration" in msg, msg
        ret.append((line, msg.split("'")[1]))
    return ret


# ---------------------------------------------------------------------------
# Legal
# ---------------------------------------------------------------------------


def test_lrm_example_262_type_member_used_before_declaration(tmp_path):
    assert_links_and_binds(tmp_path, """
component pss_top {
    action entry {
        constraint val_c {
            val < 10;
        }
        rand bit[4] val;
    }
}
""")


def test_lrm_example_263_local_used_after_declaration(tmp_path):
    assert_links_and_binds(tmp_path, """
function int get_val();

component pss_top {
    exec init_up {
        int val;
        val = get_val();
    }
}
""")


@pytest.mark.parametrize("body", [
    # One declaration statement: `b` sees `a`.
    "int a = 1, b = a;",
    # A declaration sees its own name, as in C and SystemVerilog.
    "int y = y;",
    "int q; { q = 1; }",
    "{ int q; q = 1; } { int q; q = 2; }",
    "int i; repeat (i : 2) { int k = i; }",
])
def test_legal_orders_in_a_function(tmp_path, body):
    assert_links_and_binds(tmp_path, """
component pss_top {
    function void f() {
        %s
    }
}
""" % body)


def test_activity_handles_used_after_declaration(tmp_path):
    assert_links_and_binds(tmp_path, """
component pss_top {
    action B { rand int v; }
    action A {
        int arr[4];
        activity {
            B b1;
            b1 with { v < 3; };
            foreach (e : arr) { B b3; b3; }
            repeat (i : 3) { b1 with { v == i; }; }
            parallel { sequence { b1; } }
        }
    }
}
""")


# ---------------------------------------------------------------------------
# A later declaration is hidden; the lookup carries on outward
# ---------------------------------------------------------------------------


def test_use_binds_to_the_outer_field_not_the_later_local():
    """Report G o1_shadow: before `string x;`, `x` is the field."""
    p = pssparser.Parser()
    p.parses([("t.pss", """\
component pss_top {
  bit[8] x;
  exec init_up {
    x = 1;
    string x;
    x = "a";
  }
}
""")])
    p.link()
    uses = [o for o in refs.occurrences(p)
            if o.text == "x" and not o.is_declaration]
    assert [(o.line, type(o.decl).__name__, o.decl_location[1])
            for o in uses] == [
        (4, "Field", 2),
        (6, "ProceduralStmtDataDeclaration", 5),
    ]


def test_template_parameter_is_found_past_a_later_local():
    assert errors("""
component C<int W=2> {
    exec init_up { int h = W; int W; }
}
component pss_top { C<4> c; }
""") == []


# ---------------------------------------------------------------------------
# Illegal: 18.2a (procedural), 18.2b (activity), 4.7.1.2 (template)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("body,expect", [
    ("val = 1;\n        int val;", [(4, "val")]),
    # The use is in a nested block, the declaration after it outside.
    ("{ z = 1; }\n        int z;", [(4, "z")]),
    # A declaration in a sibling block is not in scope at all.
    ("w = 3;\n        { int w; }", []),
])
def test_procedural_use_before_declaration(body, expect):
    code = """
component pss_top {
    exec init_up {
        %s
    }
}
""" % body
    if expect:
        assert use_before_decl(code) == expect
    else:
        assert [m for _, _, m in errors(code)] == ["unknown identifier 'w'"]


def test_lrm_ch20_same_line():
    assert use_before_decl("""
component pss_top {
    exec init_up { x = 1; int x; }
}
""") == [(3, "x")]


def test_activity_handle_used_before_declaration():
    assert use_before_decl("""
component pss_top {
    action B { rand int v; }
    action A {
        activity {
            B b1;
            b2 with { v < b1.v; };
            B b2;
            parallel { sequence { b4; } }
            B b4;
        }
    }
}
""") == [(7, "b2"), (9, "b4")]


def test_monitor_handle_used_before_declaration():
    assert use_before_decl("""
component pss_top {
    monitor M { }
    monitor N {
        activity {
            m;
            M m;
        }
    }
}
""") == [(6, "m")]


def test_reported_once_for_a_generic_with_two_specializations():
    assert use_before_decl("""
component C<int W=2> {
    exec init_up { h = W; int h; }
}
component pss_top { C<4> c1; C<5> c2; }
""") == [(3, "h")]


def test_the_error_points_at_the_declaration():
    _, markers = parse_collect("""
component pss_top {
    exec init_up {
        val = 1;
        int val;
    }
}
""")
    assert [(m["line"], [(r["line"], r["label"]) for r in m["related"]])
            for m in markers] == [(4, [(5, "declared here")])]


# ===========================================================================
# 9.2 -- constant initializers and type widths
# ===========================================================================


def markers_of(files):
    """(file, line, code, message) of every marker, linking `files` in order."""
    p = pssparser.Parser()
    try:
        p.parses(files)
        p.link()
        markers = p.markers
    except Exception as e:
        markers = getattr(e, "markers", None)
        if markers is None:
            raise
    return [(m.get("file", ""), m["line"], m.get("code"), m["message"])
            for m in _assign_codes(markers)]


def codes(code):
    return [(line, c) for _, line, c, _ in markers_of([("t.pss", code)])]


def test_lrm_example_264():
    """`A = C` is an error; `B = A + 2` is legal."""
    m = markers_of([("t.pss", """
package my {
    const int A = C;
    const int B = A + 2;
    const int C = 3;
}
component pss_top { }
""")])
    assert [(line, c) for _, line, c, _ in m] == [(3, "PSS118")]
    assert m[0][3] == ("constant 'C' is used in the initializer of 'A' "
                       "before its declaration on line 5; declare it first (18.2)")


@pytest.mark.parametrize("decls,expect", [
    # Enum item declared later (CH17/p36b). An `int` initializer expects no
    # enumeration type, so the bare item is also PSS046 (8.2).
    ("const int A = E_X;\n enum e { E_X = 1 }", [(3, "PSS046"), (3, "PSS118")]),
    ("enum e { E_X = 1 }\n const int A = E_X;", [(4, "PSS046")]),
    # Qualified: the lexical walk is not involved.
    ("const int A = my::C;\n const int C = 3;", [(3, "PSS118")]),
    # Itself.
    ("const int A = A + 1;", [(3, "PSS118")]),
    # 4.7.2 Example 1: through a template string.
    ('const string S = """{{C}}""";\n const int C = 3;', [(3, "PSS118")]),
    ('const int C = 3;\n const string S = """{{C}}""";', []),
])
def test_package_constants(decls, expect):
    assert codes("""
package my {
    %s
}
component pss_top { }
""" % decls) == expect


def test_type_level_constants_are_ordered_too():
    """CH17/q09: 18.2c is about constants, not about the scope."""
    assert codes("""
component pss_top {
    static const int A = B;
    static const int B = 1;
}
""") == [(3, "PSS118")]


def test_type_level_constant_may_reference_a_package_constant():
    """CH17/p37b."""
    assert codes("""
package my { const int A = 3; }
component pss_top { static const int K = my::A + 1; }
""") == []


def test_package_constant_may_not_reference_a_type_constant():
    """CH17/p37, 18.2d."""
    m = markers_of([("t.pss", """
component C { static const int K = 3; }
package my {
    const int A = C::K;
}
component pss_top { }
""")])
    assert [(line, c) for _, line, c, _ in m] == [(4, "PSS118")]
    assert "'K' is declared in type 'C'" in m[0][3]


def test_non_constants_are_not_ordered():
    """A field used before its declaration in a type is fine (Example 262);
    only constants and enum items are ordered in an initializer."""
    assert codes("""
component pss_top {
    action A {
        rand int x;
        constraint c { x < y; }
        rand int y;
    }
}
""") == []


@pytest.mark.parametrize("order,expect", [
    (["def", "use"], []),
    (["use", "def"], [("use.pss", 1, "PSS118")]),
])
def test_file_order_applies_to_constants(order, expect):
    """Decision Q8: across files, the order the files are given in."""
    src = {
        "def": ("def.pss", "package d { const int C = 3; }\n"),
        "use": ("use.pss", "package u { const int A = d::C; }\n"
                           "component pss_top { }\n"),
    }
    m = markers_of([src[k] for k in order])
    assert [(f.split("/")[-1], line, c) for f, line, c, _ in m] == expect
    if expect:
        assert "in a file given later" in m[0][3]


def test_width_forward_reference_is_a_warning():
    """Report G o3_width; the prose under Example 264."""
    _, markers = parse_collect("""
package my {
    struct s { bit[W] f; }
    const int W = 4;
}
component pss_top { }
""")
    assert [(m["line"], m.get("code"), m["severity"]) for m in markers] == \
        [(3, "PSS119", "warning")]


def test_width_after_declaration_is_clean():
    assert codes("""
package my {
    const int W = 4;
    struct s { bit[W] f; }
}
component pss_top { }
""") == []
