"""
The pss-rules loader (lint-core-plan.md C4.1; pss-rules-format.md §2-§6).

Every diagnostic of format §6.3 has a fixture in tests/data/pss-rules/,
whose trailing `# expect:` comments give the exact code, severity, line,
column and message (see that directory's README). The tests here add what a
fixture cannot state: what a loaded rule looks like (defaults applied, node
and finding types, typed options, message pieces, parsed examples, level and
scope), and the public engine API.
"""

import glob
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FIXTURES = os.path.join(ROOT, "tests", "data", "pss-rules")
BLESS = os.environ.get("PSS_RULES_BLESS") == "1"


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


def _fixture_files():
    return sorted(f for f in glob.glob(os.path.join(FIXTURES, "*"))
                  if not f.endswith((".expect", ".md")))


def _render(r):
    out = ["# expect: %s %s @ %d:%d %s" % (d["code"], d["severity"], d["line"], d["col"],
                                          d["message"])
           for d in r["diagnostics"]]
    if r["loaded"]:
        out.append("# loads: " + (", ".join(x["id"] for x in r["rules"]) or "none"))
    else:
        out.append("# refused")
    return out


def _expected(path, text):
    lines = open(path + ".expect").read() if os.path.exists(path + ".expect") else text
    return [l for l in lines.split("\n")
            if l.startswith("# expect:") or l.startswith("# loads:") or l == "# refused"]


def _load(hooks, name, builtin=False):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fp:
        return hooks.rule_load(name, fp.read(), builtin)


def _rule(hooks, name, rid):
    for r in _load(hooks, name)["rules"]:
        if r["id"] == rid:
            return r
    raise AssertionError("%s did not load %s" % (name, rid))


@pytest.mark.parametrize("path", _fixture_files(), ids=os.path.basename)
def test_fixture(hooks, path):
    with open(path, encoding="utf-8") as fp:
        text = fp.read()
    name = os.path.basename(path)
    got = _render(hooks.rule_load(name, text, text.startswith("# builtin")))
    want = _expected(path, text)
    if BLESS and got != want:
        if os.path.exists(path + ".expect") or path.endswith(".json"):
            with open(path + ".expect", "w", encoding="utf-8") as fp:
                fp.write("\n".join(got) + "\n")
        else:
            body = "\n".join(l for l in text.split("\n") if l not in want).rstrip("\n")
            with open(path, "w", encoding="utf-8") as fp:
                fp.write(body + "\n\n" + "\n".join(got) + "\n")
        pytest.skip("blessed %s; re-run to check positions" % name)
    assert got == want


def test_every_diagnostic_has_a_fixture(hooks):
    """Format §6.3: one fixture per diagnostic."""
    codes = set()
    for path in _fixture_files():
        with open(path, encoding="utf-8") as fp:
            text = fp.read()
        for l in _expected(path, text):
            if l.startswith("# expect:"):
                codes.add(l.split()[2])
    assert codes == {"PSSP210", "PSSP211", "PSSP212", "PSSP213", "PSSP214", "PSSP215",
                     "PSSP216", "PSSP217", "PSSP218", "PSSP219"}


# ----------------------------------------------------------- file level ---

def test_version_2_names_both_versions(hooks):
    r = _load(hooks, "structure-version-2.yaml")
    assert not r["loaded"] and r["rules"] == []
    [d] = r["diagnostics"]
    assert "version 2" in d["message"] and "version 1" in d["message"]


def test_key_beside_root_is_an_error_but_the_rules_load(hooks):
    r = _load(hooks, "keys-beside-root.yaml")
    assert [d["code"] for d in r["diagnostics"]] == ["PSSP211"]
    assert [x["id"] for x in r["rules"]] == ["ACME001"]


def test_good_rules_load_beside_a_bad_one(hooks):
    r = _load(hooks, "good-next-to-bad.yaml")
    assert [x["id"] for x in r["rules"]] == ["ACME001", "ACME003"]
    assert {d["rule"] for d in r["diagnostics"]} == {"ACME002"}


def test_json_rule_file(hooks):
    text = '{"pss-rules": {"rules": [{"id": "ACME001", "name": "j", "tier": "style", ' \
           '"summary": "s", "message": "m", "match": {"kind": "ExprBin"}}]}}'
    r = hooks.rule_load("r.json", text)
    assert r["diagnostics"] == [] and [x["id"] for x in r["rules"]] == ["ACME001"]


def test_yaml_on_is_a_string(hooks):
    """The YAML 1.1 trap (format §6.1): `on`/`yes` are strings, so they cannot
    silently become a bool."""
    r = _load(hooks, "fields-types.yaml")
    [d] = [d for d in r["diagnostics"] if d["rule"] == "ACME003"]
    assert "the string 'yes'" in d["message"]


# ------------------------------------------------------------- defaults ---

def test_defaults_apply_and_a_rule_value_wins(hooks):
    a = _rule(hooks, "defaults.yaml", "ACME001")
    b = _rule(hooks, "defaults.yaml", "ACME002")
    assert (a["tier"], a["severity"], a["since"]) == ("nursery", "hint", "2026.1")
    assert (b["tier"], b["severity"], b["since"]) == ("style", "warning", "2026.1")


def test_a_bad_default_is_reported_once(hooks):
    """The rule that relies on it does not load, and is not reported again."""
    r = _load(hooks, "defaults-bad.yaml")
    assert len(r["diagnostics"]) == 1 and r["diagnostics"][0]["rule"] == ""
    assert [x["id"] for x in r["rules"]] == ["ACME002"]


# ----------------------------------------------------------------- rule ---

def test_rule_metadata(hooks):
    r = _rule(hooks, "keys-beside-root.yaml", "ACME001")
    assert r["name"] == "still-loads" and r["summary"] == "The rules still load"
    assert (r["status"], r["default_enabled"], r["family"]) == ("active", True, "")
    assert (r["file"], r["line"], r["col"]) == ("keys-beside-root.yaml", 3, 7)


def test_node_type_is_the_common_base_of_the_kinds(hooks):
    r = _rule(hooks, "kinds-unknown.yaml", "ACME005")
    assert r["node_type"] == "Expr"
    assert r["match"] == {"kind": ["ExprBin", "ExprUnary"], "inside": None,
                          "not_inside": {"kind": ["Struct"], "stop": []}}


def test_finding_is_typed_by_report(hooks):
    r = _rule(hooks, "report.yaml", "ACME001")
    assert (r["node_type"], r["finding_type"], r["report"]) == ("ExprBin", "Expr", True)
    assert r["message_parts"] == [
        {"text": "operand "}, {"expr": "finding", "type": "Expr"},
        {"text": " of "}, {"expr": "node", "type": "ExprBin"}]


def test_let_in_order(hooks):
    r = _rule(hooks, "let.yaml", "ACME001")
    assert r["let"] == [{"name": "a", "type": "int"}, {"name": "b", "type": "int"}]
    assert r["where"] is True


def test_options_are_typed(hooks):
    r = _rule(hooks, "options.yaml", "ACME001")
    assert [(o["name"], o["type"], o["default"]) for o in r["options"]] == [
        ("limit", "int", 3), ("pattern", "string", "^[a-z]+$"), ("strict", "bool", False),
        ("names", "string-list", ["a", "b"]), ("mode", "string", "fast")]
    assert r["options"][0]["help"] == "The limit"
    assert r["options"][4]["choices"] == ["fast", "slow"]
    assert [p.get("type") for p in r["message_parts"]] == [None, "int", None, "string"]


def test_message_literal_dollar_brace(hooks):
    text = """pss-rules:
  rules:
    - id: ACME001
      name: dollar
      tier: style
      summary: s
      message: "write $${x} for ${'a' + \\"}\\"}"
      match: { kind: ExprBin }
"""
    r = hooks.rule_load("m.yaml", text)
    assert r["diagnostics"] == []
    assert r["rules"][0]["message_parts"] == [
        {"text": "write ${x} for "}, {"expr": "'a' + \"}\"", "type": "string"}]


def test_examples_are_parsed(hooks):
    r = _rule(hooks, "examples.yaml", "ACME001")
    first, two, none = r["examples"]
    assert first["name"] == "line comment, block comment, positions"
    assert first["files"][0]["name"] == "example.pss"
    assert first["files"][0]["expect"] == [
        {"id": "ACME001", "line": 3, "col": 5},
        {"id": "ACME001", "line": 2, "col": 0},
        {"id": "ACME001", "line": 3, "col": 0}]
    assert [(f["name"], len(f["expect"])) for f in two["files"]] == [("a.pss", 1), ("b.pss", 0)]
    assert none["files"][0]["expect"] == []


def test_unnamed_examples_are_numbered(hooks):
    r = _load(hooks, "builtin-requirements.yaml", builtin=True)
    assert [x["name"] for x in r["rules"][0]["examples"]] == ["fires", "near miss"]
    r = _rule(hooks, "fields-missing.yaml", "ACME005")
    assert r["examples"] == []


def test_builtin_requirements_apply_only_to_builtin_files(hooks):
    # As a site file, the same rules in a site namespace.
    with open(os.path.join(FIXTURES, "builtin-requirements.yaml"), encoding="utf-8") as fp:
        text = fp.read().replace("LINT9", "ACME9")
    r = hooks.rule_load("site.yaml", text)
    assert r["diagnostics"] == []
    assert [x["id"] for x in r["rules"]] == ["ACME901", "ACME902", "ACME903"]


def test_shadowing_a_file_helper_is_a_note(hooks):
    r = _load(hooks, "helpers.yaml")
    [d] = [d for d in r["diagnostics"] if d["code"] == "PSSP219"]
    assert d["severity"] == "info" and d["rule"] == "ACME002"
    assert "ACME002" in [x["id"] for x in r["rules"]]


def test_a_bad_file_helper_is_reported_once(hooks):
    """Its users do not load, and are not reported again (as an unknown function)."""
    r = _load(hooks, "helpers.yaml")
    ids = [x["id"] for x in r["rules"]]
    assert "ACME003" not in ids and "ACME004" not in ids
    assert not [d for d in r["diagnostics"] if d["rule"] in ("ACME003", "ACME004")]


# ------------------------------------------------------- level and scope ---

def test_level_and_scope_of_a_standard_library_rule(hooks):
    """Every function so far is L0, file scope; C6's library functions raise
    them (format §3.1), and C6 tests that on the worked examples of format §7."""
    r = _rule(hooks, "options.yaml", "ACME001")
    assert (r["level"], r["scope"]) == ("L0", "file")
    assert r["calls"] == ["logical_and", "logical_not", "equals", "greater_int64", "list_size",
                          "matches_string"]


def test_calls_include_helpers_and_messages(hooks):
    text = """pss-rules:
  define:
    sz(l): l.size()
  rules:
    - id: ACME001
      name: calls
      tier: style
      summary: s
      message: "${string(sz([1]))}"
      match: { kind: ExprBin }
"""
    r = hooks.rule_load("c.yaml", text)
    assert r["diagnostics"] == []
    assert r["rules"][0]["calls"] == ["list_size", "int64_to_string"]


# ----------------------------------------------------------- engine API ---

def test_engine_loads_and_accumulates(factory):
    e = factory.mkLintEngine()
    assert e.rule_format_version == 1
    with open(os.path.join(FIXTURES, "good-next-to-bad.yaml"), encoding="utf-8") as fp:
        assert e.load_rules("a.yaml", fp.read())
    with open(os.path.join(FIXTURES, "structure-version-2.yaml"), encoding="utf-8") as fp:
        assert not e.load_rules("b.yaml", fp.read())
    with open(os.path.join(FIXTURES, "report.yaml"), encoding="utf-8") as fp:
        assert e.load_rules("c.yaml", fp.read())
    assert e.num_rule_sets() == 2
    # c.yaml's ACME001 clashes with a.yaml's (format §5).
    assert [(r["file"], r["id"]) for r in e.rules()] == [
        ("a.yaml", "ACME001"), ("a.yaml", "ACME003")]
    assert [(d["file"], d["code"]) for d in e.rule_diagnostics()] == [
        ("a.yaml", "PSSP215"), ("b.yaml", "PSSP210"), ("c.yaml", "PSSP217")]


def test_engine_builtin_flag(factory):
    e = factory.mkLintEngine()
    with open(os.path.join(FIXTURES, "builtin-requirements.yaml"), encoding="utf-8") as fp:
        text = fp.read()
    assert e.load_rules("b.yaml", text, builtin=True)
    assert [r["id"] for r in e.rules()] == ["LINT903"]
    assert len(e.rule_diagnostics()) == 4


_ONE = """pss-rules:
  rules:
    - id: %s
      name: %s
      tier: style
      summary: s
      message: m
      match: { kind: ExprBin }
"""


def test_a_clash_across_files_names_both(factory):
    """Format §5: IDs and names are unique across every loaded file."""
    e = factory.mkLintEngine()
    assert e.load_rules("team-a.yaml", _ONE % ("ACME-NET001", "wide-bus"))
    assert e.load_rules("team-b.yaml", _ONE % ("ACME-NET001", "narrow-bus"))
    assert e.load_rules("team-c.yaml", _ONE % ("ACME-DMA001", "wide-bus"))
    assert e.load_rules("team-d.yaml", _ONE % ("ACME-DMA001", "dma-bus"))
    assert [r["id"] for r in e.rules()] == ["ACME-NET001", "ACME-DMA001"]
    d1, d2 = e.rule_diagnostics()
    assert (d1["code"], d1["file"], d1["line"], d1["col"]) == ("PSSP217", "team-b.yaml", 3, 11)
    assert d1["message"] == ("rule ID 'ACME-NET001' is already the ID of a rule, "
                             "at team-a.yaml:3:11")
    assert d1["related"] == {"file": "team-a.yaml", "line": 3, "col": 11}
    assert d2["file"] == "team-c.yaml" and d2["related"]["file"] == "team-a.yaml"
    assert "name 'wide-bus' is already the name of rule 'ACME-NET001'" in d2["message"]


def test_builtin_and_site_files_share_one_claim_table(factory):
    e = factory.mkLintEngine()
    text = open(os.path.join(FIXTURES, "ids-builtin.yaml"), encoding="utf-8").read()
    assert e.load_rules("builtin.yaml", text, builtin=True)
    assert e.load_rules("site.yaml", _ONE % ("ACME001", "plain-lint"))
    assert [r["id"] for r in e.rules()] == ["LINT950"]
    [d] = e.rule_diagnostics()[2:]
    assert d["code"] == "PSSP217" and d["related"]["file"] == "builtin.yaml"
