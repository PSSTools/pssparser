"""Test harness for lint rules and checkers (lint-framework L9).

Shipped in the wheel, so an extension's own test suite can use it:

* :func:`run_rules` -- parse, link, run only the named rules, return
  diagnostics.  Python checkers and declarative rules (``pss-rules``
  files: the built-in ones, and any named with ``rule_files``) alike.
* :func:`check_fixture_dir` -- run every fixture in a directory against its
  ``// expect:`` comments, exactly.
* :func:`check_examples` -- run every ``MarkerDef.examples`` entry, so the
  documented examples cannot drift from behaviour.
* :func:`check_messages` -- the message-quality rules core diagnostics are
  held to.

Fixture files
=============

A fixture is a ``.pss`` file whose expected findings are written in it::

    // expect: PRC001 @ 3:11, PRC002 @ 7:5
    component bad_name { ... }

* ``// expect: ID @ L:C[, ID @ L:C ...]`` -- findings that must be reported,
  each at an exact line and column.  May be repeated.
* ``// expect: none`` -- the rule must report nothing.
* ``// expect-fix: other.fixed.pss`` -- reserved for rule fixes.

Matching is exact: a missing finding fails, and so does an unexpected one.
Only the IDs of the rules under test are compared, so a fixture is not broken
by an unrelated core warning.  Files are picked up by name: ``l*.pss``
(lint cases), ``ok_*.pss`` (must be clean) and ``fix_*.pss``.

pytest
======

``pytest -p pssparser.checkers.testing`` adds a ``lint_fixture`` fixture
that checks one fixture directory::

    def test_rules(lint_fixture):
        lint_fixture("tests/lint/component-naming", rules=["PRC001"])
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from . import taxonomy

_EXPECT_RE = re.compile(r"//\s*expect:\s*(.*?)\s*$")
_EXPECT_FIX_RE = re.compile(r"//\s*expect-fix:\s*(\S+)")
_ITEM_RE = re.compile(
    r"^(" + taxonomy.NAMESPACE_PATTERN + r"[0-9]{3})\s*@\s*(\d+)\s*:\s*(\d+)$")

#: Fixture file-name patterns.
_FIXTURE_GLOBS = ("l*.pss", "ok_*.pss", "fix_*.pss")


class FixtureError(ValueError):
    """A malformed ``// expect:`` line; the message names file and line."""


@dataclass
class Expectations:
    findings: List[Tuple[str, int, int]] = field(default_factory=list)
    none: bool = False
    fix: Optional[str] = None


@dataclass
class FixtureResult:
    path: str
    missing: List[Tuple[str, int, int]]
    unexpected: List[Tuple[str, int, int]]
    #: Errors the fixture does not expect. Rules never run on a model with
    #: an error, so such a fixture would pass without testing anything.
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.unexpected and not self.errors

    def describe(self) -> str:
        lines = [f"{self.path}:"]
        lines += [f"  missing:    {c} @ {l}:{col}" for c, l, col in self.missing]
        lines += [f"  unexpected: {c} @ {l}:{col}" for c, l, col in self.unexpected]
        lines += [f"  error:      {e}" for e in self.errors]
        return "\n".join(lines)


def parse_expectations(text: str, path: str = "<fixture>") -> Expectations:
    """Read the ``// expect:`` comments in *text*."""
    exp = Expectations()
    for lineno, line in enumerate(text.splitlines(), start=1):
        fix = _EXPECT_FIX_RE.search(line)
        if fix:
            exp.fix = fix.group(1)
            continue
        m = _EXPECT_RE.search(line)
        if m is None:
            continue
        body = m.group(1)
        if body == "none":
            exp.none = True
            continue
        for item in body.split(","):
            im = _ITEM_RE.match(item.strip())
            if im is None:
                raise FixtureError(
                    f"{path}:{lineno}: malformed expectation {item.strip()!r}; "
                    f"write 'ID @ LINE:COL', e.g. 'PRC001 @ 3:11', or 'none'")
            exp.findings.append((im.group(1), int(im.group(2)), int(im.group(3))))
    if exp.none and exp.findings:
        raise FixtureError(f"{path}: 'expect: none' alongside expected findings")
    return exp


def run_rules(
    paths: Sequence[str],
    rules: Sequence[str] = (),
    *,
    checkers: Sequence[type] = (),
    config_text: str = "",
    rule_files: Sequence[str] = (),
) -> list:
    """Parse and link *paths*, run the lint/checker phase, return diagnostics.

    *rules* are selectors (IDs, names, tiers ...) to enable on top of profile
    ``none``, so only the rules under test report -- plus every non-lint
    diagnostic (LRM errors, checker markers).  *checkers* are extra checker
    classes to register, for testing a checker that is not installed.
    *config_text* is an optional ``.pssparser.toml`` body.  *rule_files*
    are ``pss-rules`` files or directories to load after the built-in ones,
    as ``--rules`` does; a problem in one raises ``ValueError``.

    The selected declarative rules run even under ``PSSPARSER_NO_LINT``,
    which keeps lint out of unrelated tests, not out of a rule's own.
    """
    import io
    import json
    import tempfile

    from pssparser.cli import config as config_mod
    from pssparser.cli.commands import cmd_parse
    from pssparser.lint import NO_LINT_ENV

    manager = _manager(checkers, rule_files)

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / ".pssparser.toml"
        cfg_path.write_text(config_text)

        class _Args:
            config = str(cfg_path)
            no_config = False
            checkers = None
            no_checkers = None
            load_checkers = None
            warning_policy = None
            no_warnings = False
            no_extensions = False
            lint_profile = None
            no_lint = False
            show_hints = False

        cfg = config_mod.resolve(_Args())
        if cfg.lint_profile is None:
            cfg.lint_profile = "none"
        cfg.lint_select = list(cfg.lint_select) + list(rules)
        config_mod.validate_against_registry(cfg, manager)

        out = io.StringIO()
        no_lint = os.environ.pop(NO_LINT_ENV, None)
        try:
            cmd_parse([str(p) for p in paths], output_format="json", stdout=out,
                      stderr=io.StringIO(), manager=manager, config=cfg)
        finally:
            if no_lint is not None:
                os.environ[NO_LINT_ENV] = no_lint
    return json.loads(out.getvalue())["diagnostics"]


def _manager(checkers: Sequence[type] = (), rule_files: Sequence[str] = ()):
    """A checker manager with the installed extensions, *checkers*, and the
    rules of the built-in rule files and *rule_files*."""
    from pssparser.checkers import CheckerManager
    from pssparser.lint import rulefiles, ruleview

    manager = CheckerManager()
    manager.discover()
    for cls in checkers:
        manager._accept_checker(cls, "(test)", None, bundled=True)
    load = rulefiles.load([rulefiles.RulePath(str(p), "rule_files") for p in rule_files],
                          manager.all_marker_defs(), manager.owner_of)
    errors = [d for d in load.diagnostics if d["severity"] == "error"]
    if errors:
        raise ValueError("\n".join(f"{d['file']}:{d['line']}:{d['col']}: {d['message']}"
                                    for d in errors))
    manager.add_rule_view(ruleview.marker_defs(load.engine.rules(), load.refused),
                          engine=load.engine)
    return manager


def check_fixture(path: str, rules: Sequence[str] = (), *,
                  checkers: Sequence[type] = (), config_text: str = "",
                  rule_files: Sequence[str] = ()) -> FixtureResult:
    """Run one fixture file and compare against its expectations exactly."""
    text = Path(path).read_text()
    exp = parse_expectations(text, path)
    diags = run_rules([path], rules, checkers=checkers, config_text=config_text,
                      rule_files=rule_files)
    real = os.path.realpath(path)
    ids = {f[0] for f in exp.findings} | _ids_for(rules, checkers, rule_files)
    got = sorted(
        (d["code"], d["line"], d["col"]) for d in diags
        if d.get("code") in ids and os.path.realpath(d["file"]) == real
    )
    want = sorted(exp.findings)
    expected_ids = {f[0] for f in exp.findings}
    errors = [f"{d.get('line')}:{d.get('col')}: {d.get('message')}" for d in diags
              if d.get("severity") == "error" and d.get("code") not in expected_ids]
    return FixtureResult(
        path=str(path),
        missing=[f for f in want if f not in got],
        unexpected=[f for f in got if f not in want],
        errors=errors,
    )


def _ids_for(rules: Sequence[str], checkers: Sequence[type],
             rule_files: Sequence[str] = ()) -> set:
    """The concrete IDs that *rules* and *checkers* stand for."""
    from pssparser.checkers.selectors import RuleSet

    manager = _manager(checkers, rule_files)
    defs = manager.all_marker_defs()
    ruleset = RuleSet(defs)
    ruleset.aliases = manager.alias_map()
    ids = set(ruleset.expand(rules, include_core_errors=True)) if rules else set()
    for cls in checkers:
        ids |= {md.id for md in cls().marker_defs}
    return ids


def fixture_files(directory: str) -> List[Path]:
    root = Path(directory)
    found = set()
    for pattern in _FIXTURE_GLOBS:
        found.update(root.glob(pattern))
    return sorted(found)


def check_fixture_dir(directory: str, rules: Sequence[str] = (), *,
                      checkers: Sequence[type] = (),
                      config_text: str = "",
                      rule_files: Sequence[str] = ()) -> List[FixtureResult]:
    """Run every fixture in *directory*; return one result per file.

    Raises ``AssertionError`` listing every failing file, so it can be
    called directly from a test.  An empty directory is an error too: a
    rule with no fixtures is untested.
    """
    files = fixture_files(directory)
    if not files:
        raise AssertionError(f"{directory}: no fixture files (l*.pss, ok_*.pss)")
    results = [check_fixture(str(f), rules, checkers=checkers,
                             config_text=config_text, rule_files=rule_files)
               for f in files]
    failed = [r for r in results if not r.ok]
    if failed:
        raise AssertionError("\n".join(r.describe() for r in failed))
    return results


def check_examples(checker_cls: type, *, rules: Sequence[str] = ()) -> None:
    """Run every ``MarkerDef.examples`` entry of *checker_cls*.

    A "bad" example must report its ID at exactly its ``expect`` positions;
    a "good" one must report nothing for that ID.
    """
    import tempfile

    problems = []
    for md in checker_cls().marker_defs:
        for n, ex in enumerate(md.examples):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / f"{md.id.lower()}_{n}.pss"
                path.write_text(ex.code)
                diags = run_rules([str(path)], [md.id, *rules],
                                  checkers=[checker_cls])
            got = sorted((d["line"], d["col"]) for d in diags
                         if d.get("code") == md.id)
            want = sorted(tuple(e) for e in ex.expect)
            if got != want:
                problems.append(f"{md.id} example {n}: expected {want}, got {got}")
    if problems:
        raise AssertionError("\n".join(problems))


def check_messages(diags: Iterable) -> List[str]:
    """Return message-quality problems in *diags* (dicts or ``Diagnostic``).

    Uses the error suite's rules when ``pss_errsuite`` is importable, and
    otherwise the same core checks: one line, at most 120 characters, a
    code, and no grammar jargon.
    """
    try:
        from pss_errsuite.lint import lint_message
    except ImportError:  # pragma: no cover - depends on the environment
        lint_message = None

    problems = []
    for d in diags:
        message = d["message"] if isinstance(d, dict) else d.message
        code = d.get("code") if isinstance(d, dict) else d.code
        text = re.sub(r"^\[" + taxonomy.NAMESPACE_PATTERN + r"[0-9]{3}\]\s*", "", message)
        if lint_message is not None:
            found = lint_message(text, has_code=bool(code))
        else:
            found = []
            if "\n" in text or len(text) > 120:
                found.append("one-short-line")
            if not code:
                found.append("has-a-code")
            if "mismatched input" in text or "extraneous input" in text:
                found.append("jargon")
        problems += [f"{code or '<uncoded>'}: {p}: {text}" for p in found]
    return problems


# -- pytest plugin ---------------------------------------------------------------

try:  # pragma: no cover - only when pytest is importable
    import pytest

    @pytest.fixture
    def lint_fixture():
        """``lint_fixture(directory, rules=[...], checkers=[...])``."""
        return check_fixture_dir
except ImportError:  # pragma: no cover
    pass
