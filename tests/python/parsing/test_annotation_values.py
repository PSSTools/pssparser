"""PP-1: ``pssparser.annotations`` -- the effective values of an annotation.

Every value an annotation gives is either written in its parameter list or
taken from the field's initializer, and the fields include those a base
annotation declares and those ``extend annotation`` adds.
"""
import pytest

from pssparser import Parser, annotations
from pssparser.annotations import EnumValue

_LIVE = []

HAL = """
package gen_pkg {
    enum mode_e { M0, M1 = 5, M2 };
    static const int K = 3;
    annotation base_s { string name; int n = K + 1; }
    annotation block_s : base_s {
        string header;
        string prefix = "";
        mode_e mode = mode_e::M1;
        bool   en = true;
        bit[8] mask = ~0;
        int    neg = -7 / 2;
        static const int VERSION = 2;
    }
    annotation other_s { string name; }
}
extend annotation gen_pkg::block_s { int extra = gen_pkg::K * 2; }
"""


def _link(src):
    p = Parser()
    _LIVE.append(p)
    p.parses([("t.pss", src)])
    root = p.link()
    errs = [m for m in p.markers if m["severity"] == "error"]
    assert not errs, errs
    return p, root


def _find_scope(root, name, kind=None):
    stack = [root]
    while stack:
        s = stack.pop()
        if (s.getName() if hasattr(s, "getName") and isinstance(
                s.getName(), str) else None) == name and (
                    kind is None or type(s).__name__ == kind):
            return s
        if hasattr(s, "numChildren") and hasattr(s, "getUpper"):
            stack.extend(s.getChild(i) for i in range(s.numChildren()))
    raise KeyError(name)


def _comp(body, pre=HAL):
    p, root = _link(pre + "component c { %s }" % body)
    return p, root, _find_scope(root, "c", "SymbolTypeScope")


def _fn(comp, name):
    for i in range(comp.numChildren()):
        c = comp.getChild(i)
        if type(c).__name__ == "SymbolFunctionScope" and c.getName() == name:
            return c
    raise KeyError(name)


def test_explicit_default_inherited_and_extended_values():
    p, root, c = _comp(
        '@gen_pkg::block_s {.name = "UART", .header = "uart.h"} '
        'function void f() {}')
    anns = annotations.find(root, _fn(c, "f"), "gen_pkg::block_s")
    assert len(anns) == 1
    v = annotations.effective(root, anns[0])
    # Declaration order: the base's fields, the type's own, then the extension's.
    assert list(v) == ["name", "n", "header", "prefix", "mode", "en", "mask",
                       "neg", "extra"]
    assert (v["name"].value, v["name"].is_default) == ("UART", False)
    assert (v["header"].value, v["header"].is_default) == ("uart.h", False)
    assert (v["prefix"].value, v["prefix"].is_default) == ("", True)
    assert v["n"].value == 4                      # K + 1, through a static const
    assert v["mode"].value == EnumValue("gen_pkg::mode_e", "M1", 5)
    assert v["en"].value is True
    assert v["mask"].value == 0xFF                # ~0 in a bit[8]
    assert v["neg"].value == -3                   # truncates toward zero
    assert v["extra"].value == 6                  # added by `extend annotation`
    assert "VERSION" not in v                     # a static const is no parameter


def test_value_carries_expression_field_and_location():
    p, root, c = _comp(
        '@gen_pkg::block_s {.name = "X", .header = "h"} function void f() {}')
    v = annotations.effective(
        root, annotations.find(root, _fn(c, "f"), "gen_pkg::block_s")[0])
    name, prefix = v["name"], v["prefix"]
    assert type(name.expr).__name__ == "ExprString"
    assert name.field.getName().getId() == "name"
    assert name.location.lineno == HAL.count("\n") + 1
    # A default's location is its field's, in the declaration.
    assert prefix.location.lineno == 8


def test_enum_item_value_follows_the_previous_item():
    p, root, c = _comp(
        '@gen_pkg::block_s {.name = "X", .header = "h", .mode = gen_pkg::mode_e::M2} '
        'function void f() {}')
    v = annotations.effective(
        root, annotations.find(root, _fn(c, "f"), "gen_pkg::block_s")[0])
    assert v["mode"].value == EnumValue("gen_pkg::mode_e", "M2", 6)
    assert v["mode"].value.item is not None


def test_unset_field_without_default_is_present_with_no_value():
    p, root, c = _comp('@gen_pkg::block_s {.name = "X"} function void f() {}')
    v = annotations.effective(
        root, annotations.find(root, _fn(c, "f"), "gen_pkg::block_s")[0])
    h = v["header"]
    assert (h.expr, h.value, h.is_default, h.location) == (None, None, True, None)


def test_find_by_name_and_by_declaration_and_not_by_spelling():
    p, root, c = _comp(
        'import gen_pkg::*; '
        '@block_s {.name = "a", .header = "h"} '
        '@other_s {.name = "b"} '
        '@gen_pkg::block_s {.name = "c", .header = "h"} '
        'function void f() {}')
    f = _fn(c, "f")
    by_name = annotations.find(root, f, "gen_pkg::block_s")
    # `@block_s` under an import is the same annotation as `@gen_pkg::block_s`.
    assert [annotations.effective(root, a)["name"].value
            for a in by_name] == ["a", "c"]
    decl = _find_scope(root, "block_s", "SymbolTypeScope")
    assert len(annotations.find(root, f, decl)) == 2
    assert len(annotations.find(root, f, decl.getTarget())) == 2
    assert len(annotations.find(p, f, "::gen_pkg::block_s")) == 2
    assert annotations.find(root, f, "block_s") == []
    assert len(annotations.find(root, f, "gen_pkg::other_s")) == 1


def test_find_on_component_struct_field_and_enum():
    src = HAL + """
    @gen_pkg::other_s {.name = "comp"}
    component c {
        @gen_pkg::other_s {.name = "fld"} int a;
    }
    @gen_pkg::other_s {.name = "st"} struct s { }
    @gen_pkg::other_s {.name = "en"} enum e { A };
    """
    p, root = _link(src)

    def name_of(node):
        anns = annotations.find(root, node, "gen_pkg::other_s")
        assert len(anns) == 1
        return annotations.effective(root, anns[0])["name"].value

    c = _find_scope(root, "c", "SymbolTypeScope")
    assert name_of(c) == "comp"
    assert name_of(c.getTarget()) == "comp"
    fld = [c.getChild(i) for i in range(c.numChildren())
           if type(c.getChild(i)).__name__ == "Field"
           and c.getChild(i).getName().getId() == "a"][0]
    assert name_of(fld) == "fld"
    assert name_of(_find_scope(root, "s", "SymbolTypeScope")) == "st"
    assert name_of(_find_scope(root, "e", "SymbolEnumScope")) == "en"


def test_value_that_does_not_fold_is_none():
    src = """
    annotation a_s { int n; string s; }
    component c {
        @a_s {.n = (bit[4])5, .s = "x"} function void f() {}
    }
    """
    p, root = _link(src)
    c = _find_scope(root, "c", "SymbolTypeScope")
    v = annotations.effective(root, annotations.find(root, _fn(c, "f"), "a_s")[0])
    assert v["n"].value is None
    assert type(v["n"].expr).__name__ == "ExprCast"  # not folded (yet)
    assert v["s"].value == "x"


def test_unresolved_annotation_type_matches_nothing():
    p = Parser()
    _LIVE.append(p)
    p.parses([("t.pss", "component c { @nosuch_s {.x = 1} function void f() {} }")])
    root = p.link()
    c = _find_scope(root, "c", "SymbolTypeScope")
    f = _fn(c, "f")
    assert annotations.find(root, f, "nosuch_s") == []


@pytest.mark.parametrize("expr, value", [
    ("1 + 2 * 3", 7),
    ("(1 << 4) | 1", 17),
    ("10 % 3", 1),
    ("-10 % 3", -1),
    ("2 ** 10", 1024),
    ("3 > 2 ? 5 : 6", 5),
    ("0x10", 16),
    ("8'hFF", 255),
])
def test_integer_folding(expr, value):
    src = "annotation a_s { int n; }\ncomponent c { @a_s {.n = %s} function void f() {} }" % expr
    p, root = _link(src)
    c = _find_scope(root, "c", "SymbolTypeScope")
    v = annotations.effective(root, annotations.find(root, _fn(c, "f"), "a_s")[0])
    assert v["n"].value == value


def test_on_lists_every_resolved_annotation_and_standalone_the_scope_s():
    src = HAL + """
    component c {
        @gen_pkg::other_s {.name = "a"} @nosuch_s @gen_pkg::other_s {.name = "b"}
        function void f() {}
        @gen_pkg::other_s {.name = "scope"};
    }
    """
    p, root = _link(src)
    c = _find_scope(root, "c", "SymbolTypeScope")
    on = annotations.on(root, _fn(c, "f"))
    assert [annotations.effective(root, a)["name"].value for a in on] == ["a", "b"]
    assert annotations.qualified_name(annotations.type_of(root, on[0])) \
        == "gen_pkg::other_s"
    st = annotations.standalone(root, c)
    assert [annotations.effective(root, a)["name"].value for a in st] == ["scope"]
    assert annotations.standalone(root, c.getTarget())[0].getIs_standalone()
    assert annotations.on(root, c) == []
