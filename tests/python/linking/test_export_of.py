"""PP-5: ``refs.exports`` / ``refs.export_of`` -- which ``export`` statements
name a function (20.4.2), from the linker's binding of each export."""
from pssparser import Parser, refs

_LIVE = []

SRC = """
package p {
    function void pf();
    export target function pf;
}
component pss_top {
    function void f() {}
    static function void g() {}
    function void h() {}
    export target function f;
    export target function g;
    export target function g;
}
"""


def _link(src=SRC):
    p = Parser()
    _LIVE.append(p)
    p.parses([("t.pss", src)])
    root = p.link()
    return p, root


def _scope(root, *path):
    s = root
    for name in path:
        s = [s.getChild(i) for i in range(s.numChildren())
             if getattr(s.getChild(i), "getName", None)
             and s.getChild(i).getName() == name][0]
    return s


def test_export_of_a_component_function():
    p, root = _link()
    f = _scope(root, "pss_top", "f")
    exps = refs.export_of(p, f)
    assert len(exps) == 1
    assert exps[0].getLocation().lineno == 10


def test_export_of_takes_the_definition_too():
    p, root = _link()
    f = _scope(root, "pss_top", "f")
    assert len(refs.export_of(root, f.getTarget())) == 1


def test_export_of_a_package_function_by_prototype():
    p, root = _link()
    pf = _scope(root, "p", "pf")
    assert len(refs.export_of(p, pf)) == 1
    assert len(refs.export_of(p, pf.getPrototype(0))) == 1


def test_a_function_exported_twice_has_both_in_source_order():
    p, root = _link()
    exps = refs.export_of(p, _scope(root, "pss_top", "g"))
    assert [e.getLocation().lineno for e in exps] == [11, 12]


def test_a_function_not_exported_has_none():
    p, root = _link()
    assert refs.export_of(p, _scope(root, "pss_top", "h")) == []


def test_exports_is_keyed_by_the_bound_function():
    p, root = _link()
    table = refs.exports(p)
    names = sorted((fn.getName(), len(v)) for fn, v in table.items())
    assert names == [("f", 1), ("g", 2), ("pf", 1)]


def test_export_in_an_extension_is_found():
    p, root = _link("""
    component pss_top {
        function void f() {}
    }
    extend component pss_top {
        export target function f;
    }
    """)
    assert len(refs.export_of(p, _scope(root, "pss_top", "f"))) == 1
