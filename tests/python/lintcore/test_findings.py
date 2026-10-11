"""Rule evaluation and findings (lint-core-plan.md C5.2; pss-rules-format.md §3.1, §3.4).

`lint_run` loads a rule file and runs it over the given GlobalScopes: per
match, `let:` in order, then `where:`, then `report:`; each reported node is a
finding with the rule's ID, its tier's severity and the rendered message.
"""
import pytest

_MODEL = (
    "component pss_top {\n"                 # 1
    "  int cf;\n"                           # 2
    "  action A {\n"                        # 3
    "    rand int a;\n"                     # 4
    "    rand int b;\n"                     # 5
    "    constraint c { a > 0; }\n"         # 6
    "  }\n"                                 # 7
    "  action B : A { }\n"                  # 8
    "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def unit():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", _MODEL)])
    return p, p._files[-1]


def _q(s):
    """A YAML double-quoted scalar."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _rule(rid="ACME001", match="{ kind: Action }", message="m", tier="style", extra=()):
    out = ["    - id: %s" % rid,
           "      name: rule-%s" % rid.lower(),
           "      tier: %s" % tier,
           "      summary: s",
           "      message: %s" % _q(message),
           "      match: %s" % match]
    return out + ["      " + e for e in extra]


def _file(*rules):
    out = ["pss-rules:", "  version: 1", "  rules:"]
    for r in rules:
        out += r
    return "\n".join(out) + "\n"


def _run(hooks, unit, *rules, roots=None):
    r = hooks.lint_run("r.yaml", _file(*rules), roots or [unit[1]])
    assert r["loaded"] and r["diagnostics"] == [], r["diagnostics"]
    return r


def _found(r):
    return [(f["id"], f["line"], f["msg"]) for f in r["findings"]]


def test_default_report_is_the_node(hooks, unit):
    # A declaration renders as its declaration path (format §3.4, C6.2).
    r = _run(hooks, unit, _rule(message="action ${node}"))
    assert _found(r) == [("ACME001", 3, "action pss_top::A"), ("ACME001", 8, "action pss_top::B")]
    assert {f["severity"] for f in r["findings"]} == {"hint"}


def test_where_filters(hooks, unit):
    r = _run(hooks, unit, _rule(message="${node}", extra=["where: has(node.super_t)"]))
    assert _found(r) == [("ACME001", 8, "pss_top::B")]
    (s,) = r["stats"]
    assert (s["matches"], s["findings"], s["errors"]) == (2, 1, 0)


def test_report_several_findings(hooks, unit):
    r = _run(hooks, unit, _rule(
        message="field ${finding} of ${node}",
        extra=["report: node.children.filter(c, type(c) == Field)"]))
    assert _found(r) == [("ACME001", 4, "field pss_top::A::a of pss_top::A"),
                         ("ACME001", 5, "field pss_top::A::b of pss_top::A")]
    assert [f["kind"] for f in r["findings"]] == ["Field", "Field"]


def test_report_empty_list_is_no_finding(hooks, unit):
    r = _run(hooks, unit, _rule(extra=["report: '[]'"]))
    assert r["findings"] == []
    assert r["stats"][0]["matches"] == 2


def test_report_skips_unset(hooks, unit):
    # A's super_t is unset (null); B's is set.
    r = _run(hooks, unit, _rule(message="${finding}", extra=["report: '[node.super_t]'"]))
    assert [f["kind"] for f in r["findings"]] == ["TypeIdentifier"]
    assert r["stats"][0]["errors"] == 0


def test_let_order(hooks, unit):
    r = _run(hooks, unit, _rule(message="${b}", extra=[
        "let:",
        "  a: node.name.id",
        "  b: a + '/' + a",
        "  c: b + '!'",
        "where: c.endsWith('A!')"]))
    assert _found(r) == [("ACME001", 3, "A/A")]


def test_interpolation_kinds(hooks, unit):
    r = _run(hooks, unit, _rule(
        match="{ kind: Field }",
        message="s=${node.name.id} n=${node} i=${size(node.name.id) + 1} "
                "d=${1.5} b=${has(node.init)}",
        extra=["where: node.name.id == 'a'"]))
    assert _found(r) == [("ACME001", 4, "s=a n=pss_top::A::a i=2 d=1.5 b=false")]


def test_dollar_dollar_brace_is_literal(hooks, unit):
    r = _run(hooks, unit, _rule(message="use $${x} for ${node}", extra=["where: \"node.name.id == 'A'\""]))
    assert _found(r) == [("ACME001", 3, "use ${x} for pss_top::A")]


def test_options_are_bound(hooks, unit):
    r = _run(hooks, unit, _rule(message="${options.prefix}${node}", extra=[
        "options:",
        "  prefix: { type: string, default: 'act_', help: h }",
        "where: \"!node.name.id.startsWith(options.prefix)\""]))
    assert _found(r) == [("ACME001", 3, "act_pss_top::A"), ("ACME001", 8, "act_pss_top::B")]


def test_severity_from_tier_and_override(hooks, unit):
    r = _run(hooks, unit,
             _rule("ACME001", tier="correctness"),
             _rule("ACME002", tier="simplify"),
             _rule("ACME003", tier="style"),
             _rule("ACME004", tier="style", extra=["severity: error"]))
    sev = {f["id"]: f["severity"] for f in r["findings"]}
    assert sev == {"ACME001": "warning", "ACME002": "info", "ACME003": "hint",
                   "ACME004": "error"}


def test_order_is_walk_then_rule_then_report(hooks, unit):
    r = _run(hooks, unit,
             _rule("ACME002", match="{ kind: Field }"),
             _rule("ACME001", match="{ kind: [Action, Field] }"))
    assert [(f["id"], f["line"]) for f in r["findings"]] == [
        ("ACME002", 2), ("ACME001", 2),
        ("ACME001", 3),
        ("ACME002", 4), ("ACME001", 4),
        ("ACME002", 5), ("ACME001", 5),
        ("ACME001", 8)]


def test_node_reported_twice_is_one_finding(hooks, unit):
    # Action A reports its fields, then each field's own match reports it
    # again: one finding per node, from the first match. Within one report
    # list too.
    r = _run(hooks, unit,
             _rule(match="{ kind: [Action, Field] }", message="${finding} via ${node}",
                   extra=["report: \"type(node) == Action ? "
                          "node.children.filter(c, type(c) == Field) : [node]\""]),
             _rule("ACME002", match="{ kind: Field }", message="${finding}",
                   extra=["report: '[node, node]'"]))
    assert [f["msg"] for f in r["findings"] if f["id"] == "ACME001"] == [
        "pss_top::cf via pss_top::cf", "pss_top::A::a via pss_top::A",
        "pss_top::A::b via pss_top::A"]
    assert [f["msg"] for f in r["findings"] if f["id"] == "ACME002"] == [
        "pss_top::cf", "pss_top::A::a", "pss_top::A::b"]


def test_expression_location_falls_back_to_its_first_identifier(hooks, unit):
    # ExprBin has no location of its own: `a` in `a > 0` does.
    r = _run(hooks, unit, _rule(match="{ kind: ExprBin }", message="${node}"))
    (f,) = r["findings"]
    assert (f["line"], f["col"]) == (6, 20)
    assert f["msg"] == "ExprBin at 6:20"


def test_where_error_is_not_a_finding(hooks, unit):
    # A's super_t is unset: navigating through it is an error (D-C6). Since
    # C5.3 that fails the rule for the rest of the file, so B is not
    # evaluated (test_failures.py).
    r = _run(hooks, unit, _rule(extra=["where: size(node.super_t.elems) > 0"]))
    assert r["findings"] == []
    (s,) = r["stats"]
    assert (s["matches"], s["errors"], s["error_in"]) == (1, 1, "where")
    assert "super_t" in s["error"]


def test_message_error_keeps_the_finding(hooks, unit):
    r = _run(hooks, unit, _rule(message="base ${size(node.super_t.elems) > 0}",
                                extra=["where: \"node.name.id == 'A'\""]))
    assert _found(r) == [("ACME001", 3, "base ?")]
    assert r["stats"][0]["error_in"] == "message"


def test_steps_are_counted(hooks, unit):
    r = _run(hooks, unit, _rule(extra=["where: node.children.size() > 100"]))
    assert r["stats"][0]["steps"] > 0


def test_deep_chain_every_link_reported(hooks):
    from pssparser.parser import Parser
    p = Parser()
    chain = " + ".join(["x"] * 3000)
    p.parses([("deep.pss", "component pss_top { int x; int y = %s; }\n" % chain)])
    r = hooks.lint_run("r.yaml", _file(_rule(match="{ kind: ExprBin }", message="${node}")),
                       [p._files[-1]])
    assert len(r["findings"]) == 2999
    # Every link starts at the chain's first `x`.
    assert {(f["line"], f["col"]) for f in r["findings"]} == {(1, 36)}


_NAMED = (
    "component dma { action Xfer { rand S_t f_one; } }\n"   # 1
    "struct S_t { int x; }\n"                                 # 2
    "enum E_t { A, B }\n"                                     # 3
    "function void fn_a() { }\n"                              # 4
    "package a::bb { }\n")                                    # 5


@pytest.fixture(scope="module")
def named_unit():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("named.pss", _NAMED)])
    root = p.link()
    return root, p.user_units()[-1]


def _run_named(hooks, named_unit, *rules):
    root, unit = named_unit
    r = hooks.lint_run("r.yaml", _file(*rules), [unit], model=root)
    assert r["loaded"] and r["diagnostics"] == [], r["diagnostics"]
    return r


def _spans(r):
    return [(f["kind"], f["line"], f["col"], f["extent"]) for f in r["findings"]]


def test_a_named_declaration_is_reported_at_its_name(hooks, named_unit):
    # linter-post-readiness E1: the name's span, not the declaration's body.
    r = _run_named(hooks, named_unit, _rule(
        match="{ kind: [Component, Action, Struct, Field, EnumDecl, EnumItem,"
              " FunctionPrototype, PackageScope] }"))
    assert _spans(r) == [
        ("Component", 1, 11, 3),
        ("Action", 1, 24, 4),
        ("Field", 1, 40, 5),
        ("Struct", 2, 8, 3),
        ("Field", 2, 18, 1),
        ("EnumDecl", 3, 6, 3),
        ("EnumItem", 3, 12, 1),
        ("EnumItem", 3, 15, 1),
        ("FunctionPrototype", 4, 15, 4),
        ("PackageScope", 5, 9, 5),      # a::bb, first segment to last
    ]


def test_explicit_report_of_the_node_is_its_name_too(hooks, named_unit):
    r = _run_named(hooks, named_unit, _rule(match="{ kind: Action }", extra=['report: "[node]"']))
    assert _spans(r) == [("Action", 1, 24, 4)]


def test_a_reported_declaration_lands_on_its_name(hooks, named_unit):
    r = _run_named(hooks, named_unit, _rule(match="{ kind: Field }", extra=[
        "report: >-",
        "  type(node.type) == DataTypeUserDefined",
        "    ? [resolves_to(node.type.type_id)] : []"]))
    assert _spans(r) == [("Struct", 2, 8, 3)]


def test_a_node_without_a_name_keeps_its_own_extent(hooks, named_unit):
    # FunctionDefinition holds its name in its prototype: reported where it starts.
    r = _run_named(hooks, named_unit, _rule(match="{ kind: FunctionDefinition }"))
    assert [(f["line"], f["col"]) for f in r["findings"]] == [(4, 1)]
