"""
Built-in names that no scope declares (symbol-resolution-plan.md WS5).

`this` (5.2): the built-in handle to the context type (LRM 13.1.4, Example
143; design in symbol-resolution/B-builtins.md F10; known-issues.md R-THIS).

In a type body it is the enclosing type. In an inline `with` block it is the
*containing* action, not the traversed one: unqualified names search the
traversed action first, and `this.` is how a shadowed containing-action
field, or the containing action's `comp`, is reached.
"""
import pytest

import pssparser
from pssparser import ast, refs
from pssparser.refs import Resolution


def _link(src):
    p = pssparser.Parser()
    p.parses([("t.pss", src)])
    p.link()
    return refs.occurrences(p)


def _decl_line(occs, line, text, nth=0):
    """The line of the declaration the nth `text` on `line` binds to."""
    hits = [o for o in occs if o.line == line and o.text == text]
    assert len(hits) > nth, (line, text)
    assert hits[nth].resolution is Resolution.USER, hits[nth]
    return hits[nth].decl_location.line


def test_lrm_example_143():
    occs = _link("""\
component subc {
  action A {
    rand int f;
    rand int g;
  }
}
component top {
  subc sub1, sub2;
  action B {
    rand int f;
    rand int h;
    subc::A a;
    activity {
      a with {
        f < h;
        g == this.f;
        comp == this.comp.sub1;
      };
    }
  }
}
""")
    assert _decl_line(occs, 15, "f") == 3           # sub-action's f
    assert _decl_line(occs, 15, "h") == 11          # containing action's h
    assert _decl_line(occs, 16, "g") == 4
    assert _decl_line(occs, 16, "f") == 10          # this.f: containing f
    assert _decl_line(occs, 17, "sub1") == 8        # this.comp: B's component


def test_with_on_a_type_traversal_and_an_array_element():
    occs = _link("""\
component pss_top {
  action sub_a { rand int t; }
  action top_a {
    rand int t;
    sub_a s[4];
    activity {
      replicate (i:4) s[i] with { t == this.t; };
      parallel { do sub_a with { t == this.t + 1; }; }
    }
  }
}
""")
    for line in (7, 8):
        assert _decl_line(occs, line, "t", 0) == 2
        assert _decl_line(occs, line, "t", 1) == 4


@pytest.mark.parametrize("body,line", [
    ("constraint { this.x < 3; }", 3),
    ("exec post_solve { this.x = 2; }", 3),
    ("constraint { foreach (arr[i]) { arr[i] < this.x; } }", 3),
])
def test_type_body(body, line):
    occs = _link("struct s {\n  rand int x; rand int arr[4];\n  %s\n}\n" % body)
    assert _decl_line(occs, line, "x") == 2


def test_component_exec_function_and_template():
    occs = _link('''\
component pss_top {
  int x;
  function void f() { this.x = 2; }
  function void t();
  target ASM function void t() = """ mov {{this.x}} """;
  exec init_down { this.x = 1; f(); t(); }
}
''')
    for line in (3, 5, 6):
        assert _decl_line(occs, line, "x") == 2


def test_this_comp_from_an_action_body():
    occs = _link("""\
component pss_top {
  int n;
  action a {
    rand int v;
    constraint { v < this.comp.n; }
  }
}
""")
    assert _decl_line(occs, 5, "n") == 2


def test_outside_a_type_is_an_error():
    p = pssparser.Parser()
    p.parses([("t.pss", "package p { function void f() { int y = this.x; } }\n")])
    with pytest.raises(pssparser.ParseException):
        p.link()
    errs = [m["message"] for m in p.markers if m["severity"] == "error"]
    assert errs == ["'this' is only valid inside a type: an action, "
                    "component, struct or other type body"]


def test_path_marks_a_handle_not_a_type_name():
    """The recorded path leads to the context type and ends in ElemKind_This,
    so a consumer can tell `this.x` from a reference to the type by name. In
    a `with` block it leads to the containing action, not the traversed one."""
    p = pssparser.Parser()
    p.parses([("t.pss", """\
component pss_top {
  action sub_a { rand int f; }
  action top_a {
    rand int f;
    activity { do sub_a with { f == this.f; }; }
  }
}
""")])
    p.link()
    paths = []

    class V(ast.VisitorBase):
        def visitExprRefPathContext(self, i):
            if i.getHier_id().getElem(0).getId().getId() == "this":
                paths.append([(e.kind, e.idx) for e in i.getTarget().getPathList()])

    for u in p.user_units():
        u.accept(V())
    assert len(paths) == 1
    *to_type, last = paths[0]
    assert last[0] == ast.SymbolRefPathElemKind.ElemKind_This
    assert all(k == ast.SymbolRefPathElemKind.ElemKind_ChildIdx for k, _ in to_type)

    # The path's prefix is the path to top_a: the same one `top_a` resolves to.
    occs = refs.occurrences(p)
    this_f = [o for o in occs if o.line == 5 and o.text == "f"][1]
    assert this_f.decl_location[:3] == (1, 4, 14)


@pytest.mark.parametrize("src,line,col", [
    ("component pss_top { int this; }\n", 1, 25),
    ("component pss_top { action this { } }\n", 1, 28),
    ("struct this { }\n", 1, 8),
    ("component pss_top { function void f(int this) { } }\n", 1, 41),
    ("component pss_top { exec init_down { int this = 1; } }\n", 1, 42),
    ("component pss_top { int l[2]; exec init_down { foreach (this : l) { } } }\n", 1, 57),
    ("component pss_top { int l[2]; exec init_down { foreach (x : l) { int this = 1; } } }\n",
     1, 70),
    ("component pss_top { action a { activity { repeat (this : 2) { } } } }\n", 1, 51),
])
def test_this_cannot_be_declared(src, line, col):
    p = pssparser.Parser()
    p.parses([("t.pss", src)])
    with pytest.raises(pssparser.ParseException):
        p.link()
    errs = [(m["message"], m["line"], m["col"]) for m in p.markers
            if m["severity"] == "error"]
    assert errs == [("'this' is a keyword and cannot be used as a declared name",
                     line, col)]
