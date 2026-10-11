"""Types (lint-core-plan.md C6.8; rule-authoring-requests-2026-10-10.md B2, B3).

- `type_decl(DataType | TypeIdentifier)`: the declaration a type names,
  through typedefs; a template use gives its specialization.
- `type_named(string)`: the type a PSS name names, typedefs followed;
  `optional.none()`, and one PSSP223 note per rule, when there is none. A
  literal name is checked when the rule loads.
- `derives_from(node, string)`: the type itself, or a base through `super_t`;
  a generic's name matches every specialization.

The claim rule these exist for runs in tests/data/lint-examples/fn-types.yaml.
"""
import pytest

_A = ("a.pss",
      "import addr_reg_pkg::*;\n"                           # 1
      "package p {\n"                                       # 2
      "  struct ps { }\n"                                   # 3
      "}\n"                                                 # 4
      "struct g_s { }\n"                                    # 5
      "enum color_e { RED, GREEN }\n"                       # 6
      "struct base_s { }\n"                                 # 7
      "struct mid_s : base_s { }\n"                         # 8
      "struct leaf_s : mid_s { }\n"                         # 9
      "struct other_s { }\n"                                # 10
      "extend struct other_s { rand int x; }\n"             # 11
      "typedef leaf_s leaf_t;\n"                            # 12
      "typedef leaf_t leaf2_t;\n"                           # 13
      "struct T<int W = 4> : base_s { rand bit[W] v; }\n"   # 14
      "component pss_top {\n"                               # 15
      "  p::ps f_q;\n"                                      # 16
      "  g_s f_g;\n"                                        # 17
      "  leaf2_t f_td;\n"                                   # 18
      "  T<> f_t4;\n"                                       # 19
      "  T<8> f_t8;\n"                                      # 20
      "  T<8> f_t8b;\n"                                     # 21
      "  int f_int;\n"                                      # 22
      "  bit[8] f_bit;\n"                                   # 23
      "  color_e f_enum;\n"                                 # 24
      "  transparent_addr_claim_s<> f_claim;\n"             # 25
      "  action A { leaf_s f_a; }\n"                        # 26
      "  struct S { mid_s f_s; }\n"                         # 27
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
    if v["type"] in ("list",):
        return [_py(e) for e in v["value"]]
    if v["type"] == "optional_type":
        return None if v["value"] is None else _py(v["value"])
    return v.get("value")


def _check(hooks, model, expr, linked=True):
    root, a = model
    return hooks.cel_check_node({"expr": expr}, a, model=root if linked else None)


def _ev(hooks, model, expr):
    r = _check(hooks, model, expr)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _field(name):
    return "descendants(node).filter(d, type(d) == Field && d.name.id == '%s')[0]" % name


def _decl(name):
    """type_decl of field `name`'s type."""
    return "type_decl(%s.type)" % _field(name)


# The path of what type_decl() gives: a type's or enum's, or '-' for none.
_NAME = ("cel.bind(t, %s, !t.hasValue() ? '-' : t.value().isa(TypeScope) || "
         "t.value().isa(EnumDecl) ? decl_path(t.value()) : 'other')")


@pytest.mark.parametrize("field,want", [
    ("f_g", "g_s"),
    ("f_q", "p::ps"),
    ("f_td", "leaf_s"),                     # two typedef hops
    ("f_enum", "color_e"),
    ("f_a", "leaf_s"),                      # a field in an action
    ("f_s", "mid_s"),                       # ... and in a struct
    ("f_int", "-"),
    ("f_bit", "-"),
])
def test_type_decl(hooks, model, field, want):
    assert _ev(hooks, model, _NAME % _decl(field)) == want


def test_a_specialization_is_not_the_generic(hooks, model):
    # T<> and T<8> are two specializations; two T<8> uses are one. Neither is
    # the generic resolves_to() gives, and neither is in a file.
    assert _ev(hooks, model, "[%s == %s, %s == %s, %s == type_named('T'), is_owned(%s.value())]"
               % (_decl("f_t4"), _decl("f_t8"), _decl("f_t8"), _decl("f_t8b"), _decl("f_t8"),
                  _decl("f_t8"))) == [False, True, False, False]
    assert _ev(hooks, model, "decl_path(%s.value())" % _decl("f_t8")) == ""
    assert _ev(hooks, model, "resolves_to(%s.type) == type_named('T').value()"
               % _field("f_t8")) is True


def test_const_int_of_a_bound_parameter(hooks, model):
    # The case C6.4 could not test: a specialization's `W` is bound.
    width = ("children(%s.value()).filter(c, type(c) == Field)"
             ".map(v, type(v.type) == DataTypeInt ? const_int(v.type.width) : optional.none())")
    assert _ev(hooks, model, "[%s, %s]" % (width % _decl("f_t4"), width % _decl("f_t8"))) == [
        [4], [8]]
    # In the generic, W is not a value.
    assert _ev(hooks, model, width % "type_named('T')") == [None]


def test_a_core_library_type(hooks, model):
    assert _ev(hooks, model, "[%s.hasValue(), in_library(%s.value())]" % (
        _decl("f_claim"), _decl("f_claim"))) == [True, False]


def test_type_decl_of_a_type_identifier(hooks, model):
    # A base type is a TypeIdentifier: node.super_t.
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == Struct && "
               "has(d.super_t)).map(s, [s.name.id, decl_path(type_decl(s.super_t).value())])") == [
        ["mid_s", "base_s"], ["leaf_s", "mid_s"], ["T", "base_s"]]


def test_type_decl_of_null_and_other_nodes(hooks, model):
    assert _ev(hooks, model, "[type_decl(%s.super_t).hasValue()]" % (
        "descendants(node).filter(d, type(d) == Struct && d.name.id == 'g_s')[0]")) == [False]


def test_type_named(hooks, model):
    names = ["g_s", "::g_s", "p::ps", "color_e", "leaf2_t", "pss_top::S", "addr_reg_pkg::addr_claim_s",
             "nope_s", "p::nope", "p", "pss_top::f_g"]
    got = _ev(hooks, model, "[%s]" % ", ".join(_NAME % ("type_named('%s')" % n) for n in names))
    assert dict(zip(names, got)) == {
        "g_s": "g_s", "::g_s": "g_s", "p::ps": "p::ps", "color_e": "color_e",
        "leaf2_t": "leaf_s",                # typedefs followed
        "pss_top::S": "pss_top::S",
        "addr_reg_pkg::addr_claim_s": "addr_reg_pkg::addr_claim_s",
        "nope_s": "-", "p::nope": "-",
        "p": "-",                           # a package is not a type
        "pss_top::f_g": "-",                # nor is a field
    }


def test_type_named_compares_with_type_decl(hooks, model):
    assert _ev(hooks, model, "[%s == type_named('leaf_s'), %s == type_named('leaf2_t'), "
               "%s == type_named('mid_s')]" % (_decl("f_td"), _decl("f_a"), _decl("f_a"))) == [
        True, True, False]


@pytest.mark.parametrize("ty,base,want", [
    ("type_named('mid_s')", "base_s", True),        # direct
    ("type_named('leaf_s')", "base_s", True),       # two levels
    ("type_named('leaf_s')", "mid_s", True),
    ("type_named('leaf_s')", "leaf_s", True),       # itself
    ("type_named('leaf_s')", "leaf2_t", True),      # the name may be a typedef
    ("type_named('mid_s')", "leaf_s", False),       # not downwards
    ("type_named('other_s')", "base_s", False),     # unrelated; extend adds no base
    ("type_named('g_s')", "::g_s", True),
    (_decl("f_t8"), "base_s", True),                # a specialization's base
    (_decl("f_t8"), "T", True),                     # the generic matches it
    (_decl("f_t4"), "T", True),
    (_decl("f_claim"), "addr_reg_pkg::transparent_addr_claim_s", True),
    (_decl("f_claim"), "addr_reg_pkg::addr_claim_s", True),       # a specialized base
    (_decl("f_claim"), "addr_reg_pkg::addr_claim_base_s", True),  # ... and its base
    (_decl("f_claim"), "executor_pkg::executor_claim_s", False),
    (_decl("f_enum"), "color_e", True),
    (_decl("f_g"), "nope_s", False),                # unknown: false (and a note)
])
def test_derives_from(hooks, model, ty, base, want):
    assert _ev(hooks, model, "derives_from(%s.value(), '%s')" % (ty, base)) is want


def test_derives_from_null_and_non_types(hooks, model):
    assert _ev(hooks, model, "[derives_from(null, 'g_s'), derives_from(%s, 'g_s')]"
               % _field("f_g")) == [False, False]


@pytest.mark.parametrize("path,why", [
    ("a.b", "write it as 'pkg::name', or '::name' for the global package"),
    ("", "write it as 'pkg::name', or '::name' for the global package"),
    ("p::", "write it as 'pkg::name', or '::name' for the global package"),
    ("p ::s", "write it as 'pkg::name', or '::name' for the global package"),
    ("1s", "write it as 'pkg::name', or '::name' for the global package"),
    ("T<4>", "write the generic's name without template arguments; it matches every "
             "specialization"),
])
def test_a_malformed_literal_name_is_a_check_error(hooks, model, path, why):
    for expr, at in (("type_named('%s')" % path, 11),
                     ("derives_from(node, '%s')" % path, 19)):
        r = _check(hooks, model, expr)
        assert [(e["offset"], e["message"]) for e in r["errors"]] == [
            (at, "'%s' is not a PSS type name: %s" % (path, why))]


def test_a_malformed_computed_name_is_a_run_time_error(hooks, model):
    r = _check(hooks, model, "type_named('a' + '.b')")
    assert r["errors"] == []
    assert r["values"]["expr"]["value"] == (
        "type_named(): 'a.b' is not a PSS type name: write it as 'pkg::name', or '::name' "
        "for the global package")


def test_needs_a_linked_model(hooks, model):
    for expr in ("type_decl(%s.type)" % _field("f_g"), "type_named('g_s')",
                 "derives_from(node, 'g_s')"):
        r = _check(hooks, model, expr, linked=False)
        assert "needs a linked model" in r["values"]["expr"]["value"], expr


# ------------------------------------------------------------- end to end ----

def _rules(where):
    return ("pss-rules:\n"
            "  version: 1\n"
            "  rules:\n"
            "    - id: ACME001\n"
            "      name: r1\n"
            "      tier: suspicious\n"
            "      summary: s\n"
            "      message: m\n"
            "      match: { kind: Field }\n"
            "      where: %s\n"
            "    - id: ACME002\n"
            "      name: r2\n"
            "      tier: suspicious\n"
            "      summary: s\n"
            "      message: m\n"
            "      match: { kind: Field }\n"
            "      where: %s\n" % (where, where))


def test_an_unknown_name_is_noted_once_per_rule(hooks, model):
    root, a = model
    r = hooks.lint_run("r.yaml", _rules(
        "\"type_decl(node.type).hasValue() && (derives_from(type_decl(node.type).value(),"
        " 'acme::nope_s') || type_named('acme::gone_s').hasValue())\""), [a], model=root)
    assert r["loaded"] and r["diagnostics"] == [], r["diagnostics"]
    assert r["findings"] == [] and r["failures"] == []
    # Each rule, each name, once; at the first field the rule asked for it.
    assert [(n["id"], n["rule"], n["path"], n["severity"], n["line"]) for n in r["notes"]] == [
        ("PSSP223", "ACME001", "acme::nope_s", "info", 16),
        ("PSSP223", "ACME001", "acme::gone_s", "info", 16),
        ("PSSP223", "ACME002", "acme::nope_s", "info", 16),
        ("PSSP223", "ACME002", "acme::gone_s", "info", 16),
    ]
    assert r["notes"][0]["msg"] == (
        "rule ACME001 (r1) names the type 'acme::nope_s', which the model does not have: "
        "type_named() gives none for it, and derives_from() false")


def test_engine_reports_the_note(factory, model):
    root, a = model
    e = factory.mkLintEngine()
    assert e.load_rules("r.yaml", _rules("\"derives_from(node, 'acme::nope_s')\""))
    assert e.rule_diagnostics() == []
    r = e.run([a], {}, model=root)
    assert sorted({(m["code"], m["severity"]) for m in r["markers"]}) == [("PSSP223", "info")]
    assert len(r["markers"]) == 2


def test_a_malformed_name_fails_to_load(factory):
    e = factory.mkLintEngine()
    assert not e.load_rules("r.yaml", _rules("\"derives_from(node, 'acme.nope_s')\"")) or \
        e.rule_diagnostics()
    d = e.rule_diagnostics()
    assert {x["code"] for x in d} == {"PSSP215"}
    assert d[0]["line"] == 10


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    for oid, cost in (("type_decl_DataType", "constant"), ("type_decl_TypeIdentifier", "constant"),
                      ("type_named_string", "constant"), ("derives_from_node_string", "custom")):
        f = fns[oid]
        assert (f["group"], f["level"], f["scope"], f["cost"]) == (
            "Fields and types", "L1", "file", cost), f
