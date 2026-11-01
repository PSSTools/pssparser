"""
Tests for PSS access modifiers (LRM §20.4): public, protected, private.

Covers: per-field modifiers, modifier blocks, mixed modifiers in
structs and actions, linkage, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_public_field(parser):
    """public modifier on a struct field"""
    code = """
struct s {
    public rand bit[8] x;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "x")

    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_protected_field(parser):
    """protected modifier on a struct field"""
    code = """
struct s {
    protected rand int y;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "y")


def test_private_field(parser):
    """private modifier on a struct field"""
    code = """
struct s {
    private string name;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "name")


def test_mixed_modifiers_in_action(parser):
    """Multiple access modifiers in an action"""
    code = """
component pss_top {
    action Secured {
        public rand int addr;
        protected rand int data;
        private int internal_state;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "Secured")
    assert action is not None
    for name in ("addr", "data", "internal_state"):
        assert has_symbol(action, name), f"field {name} not found"


def test_access_modifier_block(parser):
    """Access modifier block syntax: 'protected:' applies to following fields"""
    code = """
struct base_s {
    public:
        rand int visible;
    protected:
        rand int inherited_only;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "base_s")
    assert sym is not None
    assert has_symbol(sym, "visible")
    assert has_symbol(sym, "inherited_only")


# ---------------------------------------------------------------------------
# Function access protection (pssparser extension of LRM 17.4)
# ---------------------------------------------------------------------------
# LRM 17.4 gives access protection to attributes only. pssparser also accepts
# it on functions -- an `access_modifier` prefix on `function_decl`, and the
# `attr_group` label in force -- and records it on the FunctionPrototype as
# `getAccess()` -> FunctionAccess. A FunctionDefinition carries it on its
# prototype (`getProto().getAccess()`).

def _linked_unit(parser, code):
    parser.parses([("m.pss", code)])
    root = parser.link()
    unit = next(
        root.getUnit(i) for i in range(root.numUnits())
        if root.getUnit(i) is not None and root.getUnit(i).getFileid() == 1)
    return root, unit


def _functions(scope):
    """name -> FunctionPrototype for the functions declared directly in scope."""
    out = {}
    for c in scope.getChildren():
        kind = type(c).__name__
        if kind == "FunctionDefinition":
            proto = c.getProto()
        elif kind == "FunctionPrototype":
            proto = c
        else:
            continue
        out[proto.getName().getId()] = proto
    return out


def _named_child(scope, name):
    for c in scope.getChildren():
        if type(c).__name__ == "PackageScope":
            if c.numId() and c.getId(c.numId() - 1).getId() == name:
                return c
            continue
        if hasattr(c, "getName") and c.getName() is not None \
                and c.getName().getId() == name:
            return c
    raise AssertionError("no child named %s" % name)


FUNC_ACCESS_PREFIX_SRC = """
component pss_top {
    private target function void t_priv();
    protected target function void t_prot();
    public target function void t_pub();
    private solve function int s_priv() { return 1; }
    protected solve function int s_prot() { return 2; }
    public solve function int s_pub() { return 3; }
    private function void f_priv() { }
    protected function void f_prot();
    public function void f_pub();
    private target solve function void ts_priv();
    private pure function int p_priv(int a) { return a; }
    protected static function void st_prot();
    function void f_default();
    target function void t_default() { }
}
"""


def test_function_access_prefix(parser):
    from pssparser.ast import FunctionAccess as FA
    root, unit = _linked_unit(parser, FUNC_ACCESS_PREFIX_SRC)
    fns = _functions(_named_child(unit, "pss_top"))
    expect = {
        "t_priv": FA.FunctionAccess_Private,
        "t_prot": FA.FunctionAccess_Protected,
        "t_pub": FA.FunctionAccess_Public,
        "s_priv": FA.FunctionAccess_Private,
        "s_prot": FA.FunctionAccess_Protected,
        "s_pub": FA.FunctionAccess_Public,
        "f_priv": FA.FunctionAccess_Private,
        "f_prot": FA.FunctionAccess_Protected,
        "f_pub": FA.FunctionAccess_Public,
        "ts_priv": FA.FunctionAccess_Private,
        "p_priv": FA.FunctionAccess_Private,
        "st_prot": FA.FunctionAccess_Protected,
        "f_default": FA.FunctionAccess_Public,
        "t_default": FA.FunctionAccess_Public,
    }
    for name, acc in expect.items():
        assert fns[name].getAccess() == acc, name
    # The other qualifiers are still recorded alongside the prefix.
    assert fns["t_priv"].getIs_target() and not fns["t_priv"].getIs_solve()
    assert fns["s_prot"].getIs_solve()
    assert fns["ts_priv"].getIs_target() and fns["ts_priv"].getIs_solve()
    assert fns["p_priv"].getIs_pure()
    assert fns["st_prot"].getIs_static()


def test_function_access_group_applies_to_functions_and_fields(parser):
    from pssparser.ast import FunctionAccess as FA, FieldAttr
    root, unit = _linked_unit(parser, """
component pss_top {
    function void before();
    int f_before;
    private:
    int f_after;
    target function void after();
    solve function int after_def() { return 0; }
    public target function void overridden();
    protected function void overridden_prot();
    function void still_private();
    protected:
    function void now_protected();
    public:
    function void back_to_public();
}
""")
    comp = _named_child(unit, "pss_top")
    fns = _functions(comp)
    assert fns["before"].getAccess() == FA.FunctionAccess_Public
    assert fns["after"].getAccess() == FA.FunctionAccess_Private
    assert fns["after_def"].getAccess() == FA.FunctionAccess_Private
    assert fns["overridden"].getAccess() == FA.FunctionAccess_Public
    assert fns["overridden_prot"].getAccess() == FA.FunctionAccess_Protected
    assert fns["still_private"].getAccess() == FA.FunctionAccess_Private
    assert fns["now_protected"].getAccess() == FA.FunctionAccess_Protected
    assert fns["back_to_public"].getAccess() == FA.FunctionAccess_Public
    # The same label applies to fields, as before.
    assert int(_named_child(comp, "f_before").getAttr()) & int(FieldAttr.Private) == 0
    assert int(_named_child(comp, "f_after").getAttr()) & int(FieldAttr.Private)


def test_function_access_group_does_not_leak(parser):
    """A label in one component does not reach a package or another component."""
    from pssparser.ast import FunctionAccess as FA
    root, unit = _linked_unit(parser, """
package p {
    function void pkg_fn();
    private function void pkg_priv();
}
component c1 {
    private:
    function void c1_fn();
}
component pss_top {
    function void top_fn();
}
""")
    assert _functions(_named_child(unit, "p"))["pkg_fn"].getAccess() == FA.FunctionAccess_Public
    assert _functions(_named_child(unit, "p"))["pkg_priv"].getAccess() == FA.FunctionAccess_Private
    assert _functions(_named_child(unit, "c1"))["c1_fn"].getAccess() == FA.FunctionAccess_Private
    assert _functions(_named_child(unit, "pss_top"))["top_fn"].getAccess() == FA.FunctionAccess_Public


def test_function_access_prefix_keeps_neighbouring_syntax(parser):
    """Items that also start with an access modifier still parse as before."""
    from pssparser.ast import FunctionAccess as FA, FieldAttr
    root, unit = _linked_unit(parser, """
component sub { }
component pss_top {
    private static const int K = 1;
    protected int data;
    public mutable int m;
    private instance ref sub inst;
    private:
    static function void sf();
    pure function int pf(int a) { return a; }
    static const int K2 = 2;
    public:
    target solve function void tsf();
    action A {
        private rand int x;
        protected:
        rand int y;
    }
}
""")
    comp = _named_child(unit, "pss_top")
    assert int(_named_child(comp, "K").getAttr()) & int(FieldAttr.Private)
    assert int(_named_child(comp, "K").getAttr()) & int(FieldAttr.Static)
    assert int(_named_child(comp, "data").getAttr()) & int(FieldAttr.Protected)
    assert int(_named_child(comp, "m").getAttr()) & int(FieldAttr.Mutable)
    assert int(_named_child(comp, "inst").getAttr()) & int(FieldAttr.Private)
    assert int(_named_child(comp, "K2").getAttr()) & int(FieldAttr.Private)
    fns = _functions(comp)
    assert fns["sf"].getIs_static() and fns["sf"].getAccess() == FA.FunctionAccess_Private
    assert fns["pf"].getIs_pure() and fns["pf"].getAccess() == FA.FunctionAccess_Private
    assert fns["tsf"].getAccess() == FA.FunctionAccess_Public
    act = _named_child(comp, "A")
    assert int(_named_child(act, "x").getAttr()) & int(FieldAttr.Private)
    assert int(_named_child(act, "y").getAttr()) & int(FieldAttr.Protected)
