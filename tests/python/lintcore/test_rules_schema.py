"""The JSON Schema of a rule file (lint-core-plan.md C4.4; pss-rules-format.md §6.4).

The schema is written by the C++ loader from its own field table, so the two
describe the same fields. These tests check that they agree on files: what
the loader accepts, the schema accepts, and a file with a shape error (a
missing or unknown key, a value of the wrong type, a bad ID or node kind)
is rejected by both. CEL, cross-file IDs and the built-in requirements are
beyond a schema; those files are only required to pass it.

If the freshness test fails, the loader's fields or ast/*.yaml have moved on
without the published schema -- rebuild, run
``python3 scripts/gen_rules_schema.py`` and commit the result.
"""
import glob
import sys
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "data" / "pss-rules"
sys.path.insert(0, str(ROOT / "scripts"))

from gen_rules_schema import OUTPUT_PATH, render  # noqa: E402

#: Loader diagnostics a schema can also find: file structure, unknown keys,
#: invalid field values, unknown node kinds.
SHAPE_CODES = {"PSSP210", "PSSP211", "PSSP212", "PSSP213"}

#: Fixtures with a shape error the schema cannot see, and why.
SCHEMA_BLIND = {
    # What a built-in rule must also have (family, doc, examples): the
    # schema describes any rule file, and cannot tell a built-in one.
    "builtin-requirements.yaml",
}


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def validator(hooks):
    schema = hooks.rules_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def _fixtures():
    return sorted(Path(p).name for p in glob.glob(str(FIXTURES / "*"))
                  if p.endswith((".yaml", ".yml", ".json")))


def _errors(validator, text):
    return [e.message for e in validator.iter_errors(yaml.safe_load(text))]


def test_schema_json_is_up_to_date(hooks):
    assert OUTPUT_PATH.read_text() == render(hooks.rules_schema()), (
        "docs/_static/pss-rules.schema.json is stale -- run "
        "`python3 scripts/gen_rules_schema.py` and commit the result")


@pytest.mark.parametrize("name", _fixtures())
def test_schema_agrees_with_loader_on_fixture(hooks, validator, name):
    text = (FIXTURES / name).read_text(encoding="utf-8")
    loaded = hooks.rule_load(name, text, text.startswith("# builtin"))
    codes = {d["code"] for d in loaded["diagnostics"] if d["severity"] == "error"}
    if "PSSP218" in codes:
        pytest.skip("a YAML error: PyYAML reads the text differently from the loader")
    errors = _errors(validator, text)
    if codes & SHAPE_CODES and name not in SCHEMA_BLIND:
        assert errors, "%s has shape errors %s, but the schema accepts it" % (
            name, sorted(codes & SHAPE_CODES))
    else:
        assert not errors, "the loader finds no shape error in %s, but the schema " \
            "rejects it: %s" % (name, errors)


def test_blind_list_is_current(hooks, validator):
    for name in SCHEMA_BLIND:
        text = (FIXTURES / name).read_text(encoding="utf-8")
        loaded = hooks.rule_load(name, text, text.startswith("# builtin"))
        assert {d["code"] for d in loaded["diagnostics"]} & SHAPE_CODES, name
        assert not _errors(validator, text), name


_GOOD = """\
pss-rules:
  version: 1
  x-owner: lint team
  defaults:
    tier: style
    since: "2026.1"
  define:
    twice(x): x + x
  rules:
    - id: ACME-NET001
      name: no-plus
      x-ticket: NET-12
      summary: An addition
      message: "addition in ${node}"
      lrm: ["9.1"]
      aliases: [ACME009]
      options:
        limit: { type: int, default: 3, help: The limit }
        names: { type: string-list, default: [a] }
        mode: { default: fast, choices: [fast, slow] }
      match:
        kind: [ExprBin]
        inside: { kind: Action, stop: Component }
        x-note: anything
      let:
        n: twice(options.limit)
      where: n > 1
      examples:
        - name: fires
          code: |
            component pss_top { int x = 1 + 2; }   // expect: ACME-NET001
        - files:
            a.pss: "component pss_top { }"
"""


#: Each is rejected by the loader with a shape error, and by the schema.
_BAD = {
    "unknown rule key": _GOOD.replace("      where: n > 1", "      wher: n > 1"),
    "tier not in the enum": _GOOD.replace("    tier: style", "    tier: stlye"),
    "summary with ${": _GOOD.replace("summary: An addition", "summary: An ${node}"),
    "since not YYYY.N": _GOOD.replace('since: "2026.1"', 'since: "26.1"'),
    "int option with a string default":
        _GOOD.replace("type: int, default: 3", "type: int, default: three"),
    "string option with a list default":
        _GOOD.replace("{ default: fast,", "{ default: [fast],"),
    "option with no default": _GOOD.replace("type: string-list, default: [a]",
                                            "type: string-list"),
    "unknown node kind": _GOOD.replace("kind: [ExprBin]", "kind: [ExprBinn]"),
    "empty kind list": _GOOD.replace("kind: [ExprBin]", "kind: []"),
    "ancestor with no kind": _GOOD.replace("{ kind: Action, stop: Component }",
                                           "{ stop: Component }"),
    "example with code and files": _GOOD.replace(
        "        - files:", "        - code: x\n          files:"),
    "let shadowing node": _GOOD.replace("        n: twice(options.limit)",
                                        "        node: twice(1)"),
    "fix is reserved": _GOOD.replace("      where: n > 1", "      where: n > 1\n      fix: x"),
    "key beside pss-rules": _GOOD + "extra: 1\n",
    "lower-case ID": _GOOD.replace("aliases: [ACME009]", "aliases: [acme009]"),
}


def test_good_file_passes_both(hooks, validator):
    loaded = hooks.rule_load("good.yaml", _GOOD, False)
    assert [d for d in loaded["diagnostics"] if d["severity"] == "error"] == []
    assert [r["id"] for r in loaded["rules"]] == ["ACME-NET001"]
    assert _errors(validator, _GOOD) == []


@pytest.mark.parametrize("what", sorted(_BAD))
def test_shape_error_fails_both(hooks, validator, what):
    text = _BAD[what]
    loaded = hooks.rule_load("bad.yaml", text, False)
    codes = {d["code"] for d in loaded["diagnostics"] if d["severity"] == "error"}
    assert codes & SHAPE_CODES, (what, loaded["diagnostics"])
    assert _errors(validator, text), what


def test_every_loader_field_is_in_the_schema(hooks, validator):
    # A rule's JSON from the engine names the authored fields first; every
    # one of them must be a property of the schema's rule.
    props = set(validator.schema["$defs"]["rule"]["properties"])
    loaded = hooks.rule_load("good.yaml", _GOOD, False)["rules"][0]
    computed = {"level", "scope", "calls", "node_type", "finding_type", "message_parts",
                "file", "line", "col"}
    assert set(loaded) - computed <= props


def test_node_kinds_come_from_reflection(hooks, validator):
    kinds = validator.schema["$defs"]["kind"]["enum"]
    names = [c["name"] for c in hooks.reflect_schema()["classes"][1:]]
    assert kinds == names
