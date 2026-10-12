"""The built-in rules meet the rule definition of done (lint-framework-plan F3.5).

Every rule in ``rules/*.yaml``:

1. has a ``doc``, a ``since`` and a ``family``, and examples that both fire
   and stay clean (the examples themselves run in
   ``tests/python/lintcore/test_examples.py``);
2. has a fixture directory ``tests/lint/<name>/`` with at least three
   ``l*`` files and three ``ok_*`` files (they run in
   ``test_rule_fixtures.py``);
3. reports messages that pass ``check_messages``: one line, at most 120
   characters, no grammar jargon.
"""
from pathlib import Path

import pytest

from pssparser.checkers.testing import check_messages, fixture_files, run_rules

LINT_DIR = Path(__file__).resolve().parents[2] / "lint"


def _builtin_rules():
    from pssparser.core import Factory
    e = Factory.inst().mkLintEngine()
    e.load_builtin_rules()
    return [r for r in e.rules() if r["file"].startswith("pssparser:rules/")]


RULES = _builtin_rules()


def test_there_are_builtin_rules():
    assert len(RULES) >= 16


@pytest.mark.parametrize("rule", RULES, ids=[r["name"] for r in RULES])
def test_metadata(rule):
    assert rule["doc"].strip() and rule["since"] and rule["family"], rule["id"]
    expects = [bool(f["expect"]) for x in rule["examples"] for f in x["files"]]
    assert True in expects and False in expects, \
        "%s needs an example that fires and one that does not" % rule["id"]


@pytest.mark.parametrize("rule", RULES, ids=[r["name"] for r in RULES])
def test_fixture_directory(rule):
    d = LINT_DIR / rule["name"]
    names = [p.name for p in fixture_files(str(d))] if d.is_dir() else []
    assert len([n for n in names if n.startswith("l")]) >= 3, "%s: fewer than 3 l*.pss" % d
    assert len([n for n in names if n.startswith("ok_")]) >= 3, "%s: fewer than 3 ok_*.pss" % d


@pytest.mark.parametrize("rule", RULES, ids=[r["name"] for r in RULES])
def test_messages(rule):
    d = LINT_DIR / rule["name"]
    paths = [str(p) for p in fixture_files(str(d)) if p.name.startswith("l")]
    diags = []
    for p in paths:
        diags += [x for x in run_rules([p], [rule["name"]]) if x.get("code") == rule["id"]]
    assert diags, "%s: no fixture reports it" % rule["id"]
    assert check_messages(diags) == []
