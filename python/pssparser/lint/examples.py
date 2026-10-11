"""Run the ``examples:`` of declarative rules (lint-core-plan C5.5;
pss-rules-format §4).

Each example is a small model whose ``// expect: ID`` comments mark where
its rule must report. An example runs on its own: its files are parsed and
linked by a fresh parser, and only its rule runs, with its options at their
defaults. It passes when the rule reports exactly the expected findings: an
expectation without ``@ line:col`` matches a finding anywhere on its line.
An example that does not parse or link, or on which the rule fails
(``PSSP220``, ``PSSP221``), fails.

``pssparser --check-rules`` runs them, as does the test suite for the
built-in rules. The WebAssembly build runs the same examples in
``ts/test/lint-parity.test.ts``, and must agree.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

#: (file name, line, col) of a finding or an expectation; col 0 is "any".
Where = Tuple[str, int, int]


@dataclass
class ExampleResult:
    """One example's outcome."""

    rule: str
    name: str
    #: Where the example is defined: the rule file and the position of its
    #: entry under ``examples:``.
    file: str
    line: int
    col: int
    #: What is wrong, one sentence each; empty when the example passes.
    problems: List[str] = field(default_factory=list)
    #: The run's markers, with ``file`` in place of ``fileid`` (empty when
    #: the example did not parse or link).
    markers: List[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def describe(self) -> str:
        head = f"{self.file}:{self.line}:{self.col}: {self.rule} example '{self.name}'"
        return "\n".join([head] + [f"  {p}" for p in self.problems])


def _at(where: Where, many: bool) -> str:
    name, line, col = where
    pos = f"{line}:{col}" if col else f"line {line}"
    return f"{name}:{pos}" if many else pos


def compare(rule: str, expect: Sequence[Where], found: Sequence[Where],
            many: bool = False) -> List[str]:
    """The differences between *expect* and *found*, as problem sentences.

    An exact expectation is matched first, so an anywhere-on-the-line one
    cannot take the finding an exact one needs. *many* names the file in
    each position (an example with ``files:``)."""
    left = list(found)
    missing = []
    for want in sorted(expect, key=lambda w: w[2] == 0):
        hit = next((g for g in left if g[:2] == want[:2] and want[2] in (0, g[2])), None)
        if hit is None:
            missing.append(want)
        else:
            left.remove(hit)
    return ([f"expected {rule} at {_at(w, many)}, but it was not reported"
             for w in missing]
            + [f"{rule} was reported at {_at(g, many)}, which the example does not expect"
               for g in left])


def run_example(engine, rule: dict, example: dict) -> ExampleResult:
    """Run one *example* of *rule* (both as :meth:`LintEngine.rules` gives
    them) in *engine*."""
    from pssparser.parser import ParseException, Parser

    rid = rule["id"]
    out = ExampleResult(rid, example["name"], rule["file"], example["line"],
                        example["col"])
    files = [(f["name"], f["text"]) for f in example["files"]]
    many = len(files) > 1
    parser = Parser()
    try:
        parser.parses(files)
        parser.link()
    except ParseException:
        pass
    errors = [m for m in parser.markers if m["severity"] == "error"]
    if errors:
        e = errors[0]
        where = f"{e['file']}:{e['line']}:{e['col']}" if many else f"{e['line']}:{e['col']}"
        out.problems.append(f"the example has errors, so no rule ran: {where}: "
                            f"{e['message']}")
        return out

    names = parser.file_map
    # The example's own file names, so file_of() sees them as written.
    result = engine.run(parser.user_units(),
                        {"enabled": [rid],
                         "files": {str(i): n for i, n in names.items()}},
                        model=parser._root)
    for m in result["markers"]:
        m = dict(m)
        m["file"] = names.get(m.pop("fileid"), "")
        out.markers.append(m)

    found = [(m["file"], m["line"], m["col"]) for m in out.markers if m["code"] == rid]
    expect = [(f["name"], e["line"], e["col"]) for f in example["files"]
              for e in f["expect"]]
    out.problems += compare(rid, expect, found, many)
    out.problems += [f"the rule failed at {_at((m['file'], m['line'], m['col']), many)}: "
                     f"{m['message']}"
                     for m in out.markers if m["code"] != rid]
    return out


def run_examples(engine, rules: Optional[Iterable[str]] = None,
                 files: Optional[Iterable[str]] = None,
                 skip: Iterable[str] = ()) -> List[ExampleResult]:
    """Run the examples of the rules loaded in *engine*: those whose ID is
    in *rules* and whose rule file is in *files* (``None``: any), except the
    IDs in *skip*. Results are in load order."""
    rules = None if rules is None else set(rules)
    files = None if files is None else set(files)
    skip = set(skip)
    out = []
    for r in engine.rules():
        if ((rules is not None and r["id"] not in rules)
                or (files is not None and r["file"] not in files) or r["id"] in skip):
            continue
        out += [run_example(engine, r, x) for x in r["examples"]]
    return out


def check_examples(engine, rules: Optional[Iterable[str]] = None,
                   files: Optional[Iterable[str]] = None) -> List[ExampleResult]:
    """:func:`run_examples`, raising ``AssertionError`` that lists every
    failing example, so it can be called directly from a test."""
    results = run_examples(engine, rules, files)
    failed = [r for r in results if not r.ok]
    if failed:
        raise AssertionError("\n".join(r.describe() for r in failed))
    return results
