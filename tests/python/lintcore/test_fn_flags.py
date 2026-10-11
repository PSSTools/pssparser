"""Flags (lint-core-plan.md C6.8; rule-authoring-requests-2026-10-10.md B1).

`has_flag(word, flag)`: whether every bit of `flag` is set in `word`. A flags
field (`Field.attr`) and a flags constant (`FieldAttr.Rand`) are ints the
checker tags with their enum, so it can refuse:

- a constant of a plain enum as the flag, or a plain enum's value as the word;
- a flags value used as a number -- `int()`, `string()`, arithmetic,
  ordering (linter-post-readiness-2026-10-11.md E4). Its bit values are the
  AST's, not the rule format's; `==` against a named flag stays legal.

`FieldAttr` is the schema's only flags enum, so "a flag of another flags
enum" has no case yet: the check is there (word and flag tagged with
different enums), untestable until a second flags enum exists.
"""
import pytest

_A = ("a.pss",
      "component pss_top {\n"                   # 1
      "  int plain;\n"                          # 2
      "  static const int sc = 1;\n"            # 3
      "  action A {\n"                          # 4
      "    rand int r;\n"                       # 5
      "    int n;\n"                            # 6
      "  }\n"                                   # 7
      "  struct S {\n"                          # 8
      "    private rand int p;\n"               # 9
      "    protected int q;\n"                  # 10
      "  }\n"                                   # 11
      "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([_A])
    root = p.link()
    (a,) = p.user_units()
    return root, a


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    return v.get("value")


def _check(hooks, model, expr):
    root, a = model
    return hooks.cel_check_node({"expr": expr}, a, model=root)


def _ev(hooks, model, expr):
    r = _check(hooks, model, expr)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _err(hooks, model, expr):
    r = _check(hooks, model, expr)
    assert len(r["errors"]) == 1, r["errors"]
    return r["errors"][0]


_FIELDS = "descendants(node).filter(d, type(d) == Field)"


@pytest.mark.parametrize("flag,want", [
    ("Rand", {"r", "p"}),
    ("Const", {"sc"}),
    ("Static", {"sc"}),
    ("Private", {"p"}),
    ("Protected", {"q"}),
    ("Mutable", set()),
])
def test_each_flag(hooks, model, flag, want):
    got = _ev(hooks, model, _FIELDS + ".filter(f, has_flag(f.attr, FieldAttr.%s))"
              ".map(f, f.name.id)" % flag)
    assert set(got) == want


def test_two_flags_on_one_field(hooks, model):
    # `static const` and `private rand` set two bits each.
    assert _ev(hooks, model, _FIELDS + ".filter(f, has_flag(f.attr, FieldAttr.Static)"
               " && has_flag(f.attr, FieldAttr.Const)).map(f, f.name.id)") == ["sc"]
    assert _ev(hooks, model, _FIELDS + ".filter(f, has_flag(f.attr, FieldAttr.Private)"
               " && has_flag(f.attr, FieldAttr.Rand)).map(f, f.name.id)") == ["p"]


def test_a_field_with_no_attributes(hooks, model):
    flags = ["Action", "Builtin", "Rand", "Const", "Static", "Instance", "Private",
             "Protected", "Mutable"]
    expr = ("%s.filter(f, f.name.id == 'plain').map(f, [%s])[0]"
            % (_FIELDS, ", ".join("has_flag(f.attr, FieldAttr.%s)" % x for x in flags)))
    assert _ev(hooks, model, expr) == [False] * len(flags)


def test_any_int_is_accepted(hooks, model):
    # has_flag(int, int): every bit of the second set in the first.
    assert _ev(hooks, model, "[has_flag(6, 2), has_flag(6, 1), has_flag(6, 6), "
               "has_flag(6, 7), has_flag(0, 0)]") == [True, False, True, False, True]


def test_a_plain_enum_constant_is_not_a_flag(hooks, model):
    e = _err(hooks, model, _FIELDS + ".all(f, has_flag(f.attr, ExprBinOp.BinOp_Eq))")
    assert e["message"] == ("ExprBinOp.BinOp_Eq is a member of enum 'ExprBinOp', which is "
                            "not a set of flags")
    assert e["offset"] == len(_FIELDS + ".all(f, has_flag(f.attr, ")


def test_a_plain_enum_value_is_not_a_flags_word(hooks, model):
    e = _err(hooks, model, "descendants(node).filter(d, type(d) == ExprBin)"
             ".all(b, has_flag(b.op, 1))")
    assert e["message"] == ("has_flag() tests a set of flags, and b.op is a 'ExprBinOp' "
                            "value, which is not one; compare it with == instead")


@pytest.mark.parametrize("expr,at", [
    ("int(f.attr) == 4", "f.attr"),
    ("string(f.attr) == '4'", "f.attr"),
    ("f.attr / 4 % 2 == 1", "f.attr"),
    ("(f.attr / FieldAttr.Rand) % 2 == 1", "f.attr"),
    ("f.attr > 3", "f.attr"),
    ("-f.attr < 0", "f.attr"),
    ("cel.bind(a, f.attr, a % 8 == 4)", "a"),
])
def test_a_flags_word_is_not_a_number(hooks, model, expr, at):
    # E4: the pre-C6.8 workarounds now fail to load, pointing at has_flag.
    e = _err(hooks, model, _FIELDS + ".all(f, %s)" % expr)
    assert e["message"] == ("%s is a set of 'FieldAttr' flags, not a number: test a flag with "
                            "has_flag(%s, FieldAttr.<flag>)" % (at, at))


def test_a_flag_constant_is_not_a_number(hooks, model):
    e = _err(hooks, model, "FieldAttr.Rand * 2 == 8")
    assert e["message"] == ("FieldAttr.Rand is a 'FieldAttr' flag, not a number: test a flag "
                            "with has_flag(x, FieldAttr.Rand)")


def test_equality_with_a_named_flag_stays(hooks, model):
    # == names the flag, so it does not depend on its bit value.
    assert _ev(hooks, model, _FIELDS + ".filter(f, f.attr == FieldAttr.Rand)"
               ".map(f, f.name.id)") == ["r"]


def test_plain_enum_arithmetic_is_unaffected(hooks, model):
    assert _ev(hooks, model, "ExprBinOp.BinOp_Eq + 1") == 18


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    f = fns["has_flag_int_int"]
    assert (f["group"], f["level"], f["scope"], f["cost"]) == (
        "Fields and types", "L0", "file", "constant"), f
