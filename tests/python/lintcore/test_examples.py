"""Rule examples run, natively (lint-core-plan.md C5.5; pss-rules-format §4).

Every example of every built-in rule, and of the rule files in
``tests/data/lint-examples/``, must pass. The harness itself
(``pssparser.lint.examples``) is tested on examples that fail in each way it
knows. ``--check-rules`` reports a failing example as ``PSSP222``, and
``pssparser.checkers.testing`` runs declarative rules on fixture files.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import pytest

from pssparser.cli.app import main
from pssparser.lint.examples import check_examples, compare, run_examples

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "tests" / "data" / "lint-examples"
RULE_FILES = sorted(EXAMPLES.glob("*.yaml"))


def _engine(*files):
    from pssparser.core import Factory
    e = Factory.inst().mkLintEngine()
    e.load_builtin_rules()
    for name, text in files:
        e.load_rules(name, text)
    assert [d for d in e.rule_diagnostics() if d["severity"] == "error"] == []
    return e


def _example_ids():
    e = _engine(*[(str(p.relative_to(ROOT)), p.read_text()) for p in RULE_FILES])
    return [(r["id"], x["name"]) for r in e.rules() for x in r["examples"]]


@pytest.fixture(scope="module")
def engine():
    return _engine(*[(str(p.relative_to(ROOT)), p.read_text()) for p in RULE_FILES])


# -- Every example passes -------------------------------------------------------

def test_builtin_examples_pass():
    e = _engine()
    builtin = {r["file"] for r in e.rules()}
    assert all(f.startswith("pssparser:rules/") for f in builtin)
    check_examples(e, files=builtin)


@pytest.mark.parametrize("rule,name", _example_ids(),
                         ids=["%s:%s" % i for i in _example_ids()])
def test_example_passes(engine, rule, name):
    (r,) = [r for r in run_examples(engine, rules=[rule]) if r.name == name]
    assert r.ok, r.describe()


def test_the_examples_cover_what_they_say(engine):
    # README.md promises these; a rule file edit must not drop one.
    text = "".join(p.read_text() for p in RULE_FILES)
    for feature in ("files:", "@ ", "/* expect:", "expect: none", "report:", "let:",
                    "define:", "inside:", "not_inside:", "options:"):
        assert feature in text, feature
    results = run_examples(engine)
    assert any(r.name == "example 1" for r in results)          # unnamed
    assert any(len(r.markers) >= 3 for r in results)            # several findings
    assert len(results) == len(_example_ids())


# -- What the harness reports ----------------------------------------------------

def _rule(examples, where="!node.name.id.matches('^[A-Z]')", rid="ACME001"):
    return (f"""\
pss-rules:
  rules:
    - id: {rid}
      name: r-{rid.lower()}
      tier: style
      summary: s
      message: "action '${{node.name.id}}'"
      match: {{ kind: Action }}
      where: "{where}"
      examples:
""" + examples)


def _one(examples, **kw):
    (r,) = run_examples(_engine(("acme.yaml", _rule(examples, **kw))), rules=["ACME001"])
    return r


def test_a_passing_example():
    r = _one("""\
        - name: fires
          code: |
            component pss_top {
              action b { }   // expect: ACME001
            }
""")
    assert r.ok and r.problems == []
    assert (r.rule, r.name, r.file, r.line, r.col) == ("ACME001", "fires", "acme.yaml", 11, 11)
    assert [(m["code"], m["file"], m["line"], m["col"]) for m in r.markers] == [
        ("ACME001", "example.pss", 2, 10)]


def test_missing_and_unexpected():
    r = _one("""\
        - name: wrong line
          code: |
            component pss_top {
              action c { }
              action D { }   // expect: ACME001
            }
""")
    assert r.problems == [
        "expected ACME001 at line 3, but it was not reported",
        "ACME001 was reported at 2:10, which the example does not expect"]
    assert r.describe() == (
        "acme.yaml:11:11: ACME001 example 'wrong line'\n"
        "  expected ACME001 at line 3, but it was not reported\n"
        "  ACME001 was reported at 2:10, which the example does not expect")


def test_a_near_miss_must_report_nothing():
    r = _one("""\
        - code: |
            component pss_top {
              action c { }
            }
""")
    assert r.name == "example 1"
    assert r.problems == ["ACME001 was reported at 2:10, which the example does not expect"]


def test_column_must_match_when_given():
    r = _one("""\
        - code: |
            component pss_top {
              action c { }   // expect: ACME001 @ 2:4
            }
""")
    assert r.problems == [
        "expected ACME001 at 2:4, but it was not reported",
        "ACME001 was reported at 2:10, which the example does not expect"]


def test_exact_expectations_are_matched_first():
    # Two findings on one line: the line-only expectation must not take the
    # finding at 2:28 that the exact one needs.
    assert compare("A", [("f", 2, 0), ("f", 2, 28)], [("f", 2, 28), ("f", 2, 3)]) == []
    assert compare("A", [("f", 2, 0), ("f", 2, 0)], [("f", 2, 3)]) == [
        "expected A at line 2, but it was not reported"]


def test_an_example_with_errors_fails():
    r = _one("""\
        - name: bad
          code: |
            component pss_top {
              action c : Missing { }   // expect: ACME001
            }
""")
    assert r.markers == []
    (p,) = r.problems
    assert p.startswith("the example has errors, so no rule ran: 2:14: ")
    assert "Missing" in p


def test_a_syntax_error_fails():
    r = _one("""\
        - code: |
            component pss_top {
              action c {
""")
    (p,) = r.problems
    assert p.startswith("the example has errors, so no rule ran: ")


def test_a_rule_failure_fails_the_example():
    r = _one("""\
        - code: |
            component pss_top {
              action c { }
            }
""", where="size(node.super_t.elems) > 0")
    (p,) = r.problems
    assert p.startswith("the rule failed at 2:3: rule ACME001 (r-acme001) failed in its where")


def test_several_files_name_the_file():
    r = _one("""\
        - files:
            a.pss: |
              component pss_top { }
            b.pss: |
              extend component pss_top {
                action q { }
                action r { }   // expect: ACME001
              }
""")
    assert r.problems == [
        "ACME001 was reported at b.pss:2:10, which the example does not expect"]


def test_options_are_at_their_defaults():
    rules = _rule("""\
        - code: |
            component pss_top {
              action Ab { }   // expect: ACME001
            }
""", where="node.name.id.size() < options.min")
    rules = rules.replace("      examples:\n",
                          "      options:\n"
                          "        min: { type: int, default: 3, help: h }\n"
                          "      examples:\n")
    (r,) = run_examples(_engine(("acme.yaml", rules)), rules=["ACME001"])
    assert r.ok, r.describe()


def test_only_its_own_rule_runs():
    two = _rule("""\
        - code: |
            component pss_top {
              action b { }   // expect: ACME001
            }
""") + _rule("", rid="ACME002").split("  rules:\n", 1)[1].rstrip() + " []\n"
    results = run_examples(_engine(("acme.yaml", two)), rules=["ACME001", "ACME002"])
    assert [r.rule for r in results] == ["ACME001"]
    assert results[0].ok and {m["code"] for m in results[0].markers} == {"ACME001"}


def test_check_examples_raises_with_every_failure():
    e = _engine(("acme.yaml", _rule("""\
        - name: one
          code: |
            component pss_top { action c { } }
        - name: two
          code: |
            component pss_top { action d { } }
""")))
    with pytest.raises(AssertionError) as exc:
        check_examples(e)
    assert "example 'one'" in str(exc.value) and "example 'two'" in str(exc.value)


def test_rules_json_gives_the_example_position(engine):
    (r,) = [r for r in engine.rules() if r["id"] == "ACME001"]
    assert [(x["name"], x["line"], x["col"]) for x in r["examples"]] == [
        ("lower-case name", 18, 11), ("UpperCamelCase is fine", 23, 11)]


# -- --check-rules ---------------------------------------------------------------

def _main(args):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(args)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def test_check_rules_runs_the_examples(tmp_path):
    f = tmp_path / "acme.yaml"
    f.write_text(_rule("""\
        - name: good
          code: |
            component pss_top { action b { } }   // expect: ACME001
        - name: wrong
          code: |
            component pss_top { action C { } }   // expect: ACME001
"""))
    rc, out, err = _main(["--check-rules", "--format", "json", str(f)])
    assert rc == 1
    diags = json.loads(out)["diagnostics"]
    assert [(d["code"], d["severity"], d["line"], d["col"], d["message"]) for d in diags] == [
        ("PSSP222", "error", 14, 11, "[PSSP222] example 'wrong' of ACME001: expected ACME001 "
         "at line 1, but it was not reported")]


def test_check_rules_text(tmp_path):
    f = tmp_path / "acme.yaml"
    f.write_text(_rule("""\
        - name: wrong
          code: |
            component pss_top { action C { } }   // expect: ACME001
"""))
    rc, out, err = _main(["--check-rules", str(f)])
    assert rc == 1
    assert ("acme.yaml:11:11: error: [PSSP222] example 'wrong' of ACME001: expected "
            "ACME001 at line 1, but it was not reported") in err


def test_check_rules_passes_good_examples():
    rc, out, err = _main(["--check-rules"] + [str(p) for p in RULE_FILES])
    assert rc == 0, err
    assert "0 errors" in err
    # The built-in rules are not counted: they are not loaded from a file.
    n = len([r for r in _engine(*[(str(p), p.read_text()) for p in RULE_FILES]).rules()
             if not r["file"].startswith("pssparser:")])
    assert "%d rules loaded from %d files" % (n, len(RULE_FILES)) in err


def test_check_rules_skips_a_refused_rule(tmp_path):
    # PSSP217: the second file's rule is refused, so its (failing) example
    # does not run.
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text(_rule("        - code: 'component pss_top { action b { } }  // expect: ACME001'\n"))
    b.write_text(_rule("        - code: 'component pss_top { action C { } }  // expect: ACME001'\n"))
    rc, out, err = _main(["--check-rules", "--format", "json", str(a), str(b)])
    codes = [d["code"] for d in json.loads(out)["diagnostics"]]
    assert "PSSP217" in codes and "PSSP222" not in codes


def _doc_rule_files(name):
    """Every ``.. code-block:: yaml`` in docs/<name> that is a whole rule file."""
    text = (ROOT / "docs" / name).read_text()
    out = []
    for m in re.finditer(r"^\.\. code-block:: yaml\n\n((?:   .*\n|\n)+)", text, re.M):
        body = "\n".join(l[3:] for l in m.group(1).splitlines()).strip("\n") + "\n"
        body = "\n".join(l for l in body.splitlines() if not l.startswith("# ")) + "\n"
        if body.lstrip().startswith("pss-rules:"):
            out.append(pytest.param(body, id="%s:%d" % (name, text.count("\n", 0, m.start()) + 1)))
    return out


_DOC_RULE_FILES = _doc_rule_files("lint-rule-authoring.rst")


@pytest.mark.parametrize("body", _DOC_RULE_FILES)
def test_the_authoring_guide_rule_files_pass(body, tmp_path):
    # B6: every rule file in the user doc loads, and its examples pass.
    f = tmp_path / "rules.yaml"
    f.write_text(body)
    rc, out, err = _main(["--check-rules", str(f)])
    assert rc == 0, out + err


def test_the_authoring_guide_has_rule_files():
    assert len(_DOC_RULE_FILES) >= 2


def test_pssp222_is_defined():
    from pssparser.checkers.core_checker import CoreChecker
    (d,) = [d for d in CoreChecker().marker_defs if d.id == "PSSP222"]
    assert (d.name, d.severity) == ("rule-example-failed", "error")


# -- Fixture files through pssparser.checkers.testing ----------------------------

def test_run_rules_runs_a_declarative_rule(tmp_path):
    from pssparser.checkers.testing import run_rules
    model = tmp_path / "m.pss"
    model.write_text("component pss_top {\n  action write_burst { }\n}\n")
    diags = run_rules([model], ["action-name-upper-camel"],
                      rule_files=[EXAMPLES / "naming.yaml"])
    assert [(d["code"], d["line"], d["col"]) for d in diags] == [("ACME001", 2, 10)]


def test_run_rules_runs_only_the_selected_rules(tmp_path):
    from pssparser.checkers.testing import run_rules
    model = tmp_path / "m.pss"
    model.write_text("component pss_top {\n  action Ab { }\n}\n")
    diags = run_rules([model], ["ACME001"], rule_files=[EXAMPLES])
    assert diags == []
    diags = run_rules([model], ["ACME003"], rule_files=[EXAMPLES])
    assert [d["code"] for d in diags] == ["ACME003"]


def test_check_fixture_dir_with_declarative_rules(tmp_path):
    from pssparser.checkers.testing import check_fixture_dir
    (tmp_path / "l1.pss").write_text(
        "component pss_top {\n"
        "  action A { rand bit[8] bad; }  // expect: ACME002 @ 2:26\n"
        "}\n")
    (tmp_path / "ok_1.pss").write_text("component pss_top {\n  action A { rand bit[8] m_ok; }\n}\n")
    results = check_fixture_dir(str(tmp_path), ["field-prefix"],
                                rule_files=[EXAMPLES / "naming.yaml"])
    assert all(r.ok for r in results) and len(results) == 2
    (tmp_path / "ok_2.pss").write_text("component pss_top {\n  action A { rand bit[8] x; }\n}\n")
    with pytest.raises(AssertionError, match=r"unexpected: ACME002 @ 2:26"):
        check_fixture_dir(str(tmp_path), ["field-prefix"],
                          rule_files=[EXAMPLES / "naming.yaml"])


def test_a_bad_rule_file_is_an_error(tmp_path):
    from pssparser.checkers.testing import run_rules
    bad = tmp_path / "bad.yaml"
    bad.write_text("pss-rules:\n  rules:\n    - id: ACME001\n")
    with pytest.raises(ValueError, match="bad.yaml:3"):
        run_rules([tmp_path / "m.pss"], [], rule_files=[bad])
