#!/usr/bin/env python3
"""Record what the native lint runner reports, for the TS tests.

    cd .. && PYTHONPATH=python packages/python/bin/python \\
        ts/scripts/gen-lint-parity-fixture.py -o ts/test/fixtures/lint-parity.json

Two kinds of case (lint-core-plan.md C5.5):

* ``example``: every example of every built-in rule and of the rule files in
  tests/data/lint-examples/, run by ``pssparser.lint.examples`` (each example
  parsed and linked on its own, only its rule enabled). The case records
  whether it passed and the markers the rule gave.
* ``run``: rule files and a model, run with a request (enabled rules,
  options, a step budget), as ``LintEngine.run`` and ``Parser.runLint`` do.
  The case records the markers, the per-rule statistics (without the time)
  and the request problems.

`ts/test/lint-parity.test.ts` runs the same inputs through the WebAssembly
build and must get the same results. Rule files are named by repository
path and read by the test; models and inline rule files are stored whole.
Markers are compared in a normal form: the file's name in place of its id,
sorted by file, line, column, code and message.

Re-run it when a rule file under tests/data/lint-examples/, a built-in rule
file, or the runner's output changes; the diff is then a record of what
changed.
"""

import argparse
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

#: The rule files whose examples run, and which the run cases load.
EXAMPLE_FILES = sorted(
    os.path.relpath(p, ROOT).replace(os.sep, "/")
    for p in glob.glob(os.path.join(ROOT, "tests", "data", "lint-examples", "*.yaml")))

NO_FILE = "<pssparser>"

MODEL = """\
component pss_top {
  int count;
  action write_burst {
    rand bit[8] m_len;
    rand bit[8] len;
    constraint { len == 2; }
    exec post_solve {
      if (len == 3) { }
    }
  }
  action Ab : write_burst { }
  struct Xy { }
}
"""

FAILING = """\
pss-rules:
  rules:
    - id: ACME009
      name: base-elems
      tier: suspicious
      summary: s
      message: m
      match: { kind: Action }
      where: size(node.super_t.elems) > 0
"""

#: (id, rule files by path, inline rule files, sources, request)
RUNS = [
    ("all-rules", EXAMPLE_FILES, [], [("m.pss", MODEL)], {}),
    ("enabled-and-options", EXAMPLE_FILES, [], [("m.pss", MODEL)],
     {"enabled": ["ACME002", "ACME003"],
      "options": {"ACME002": {"prefix": "le"}, "ACME003": {"min": 12}}}),
    ("request-problems", EXAMPLE_FILES, [], [("m.pss", MODEL)],
     {"enabled": ["NOPE", "ACME001"],
      "options": {"ACME001": {"x": 1}, "ACME002": {"prefix": 1}}}),
    ("two-files", EXAMPLE_FILES, [],
     [("types.pss", "package p {\n  struct Pq { }\n}\n"),
      ("top.pss", "import p::*;\ncomponent pss_top {\n  abstract action q_a { }\n"
                  "  action b : q_a { Pq s; }\n}\n")],
     {}),
    ("budget", EXAMPLE_FILES, [], [("m.pss", MODEL)],
     {"enabled": ["ACME002"], "maxSteps": 5}),
    ("failure", [], [("failing.yaml", FAILING)], [("m.pss", MODEL)], {}),
    ("gate", EXAMPLE_FILES, [],
     [("bad.pss", "component pss_top { action b : Missing { } }\n")], {}),
    ("gate-nothing-enabled", EXAMPLE_FILES, [],
     [("bad.pss", "component pss_top { action b : Missing { } }\n")], {"enabled": []}),
]


def named(markers, names):
    """The core's markers with `file` (from *names*, by `fileid`) in place
    of `fileid`; a marker with no location gets NO_FILE, line 0."""
    out = []
    for m in markers:
        m = dict(m)
        fileid = m.pop("fileid")
        if fileid < 0 or m["line"] < 1:
            m.update(file=NO_FILE, line=0, col=0, extent=0)
        else:
            m["file"] = names.get(fileid, "")
        out.append(m)
    return out


def normal(markers):
    """Named markers in the compared form, sorted."""
    keys = ("code", "severity", "message", "file", "line", "col", "extent")
    out = [{k: m[k] for k in keys} for m in markers]
    out.sort(key=lambda m: (m["file"], m["line"], m["col"], m["code"], m["message"]))
    return out


def native_request(req, errors):
    out = {"gate_errors": req.get("gateErrors", errors)}
    for ts, py in (("enabled", "enabled"), ("options", "options"), ("maxSteps", "max_steps")):
        if ts in req:
            out[py] = req[ts]
    return out


def engine_for(paths, inline):
    from pssparser.core import Factory
    e = Factory.inst().mkLintEngine()
    e.load_builtin_rules()
    for p in paths:
        with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
            e.load_rules(p, fh.read())
    for name, text in inline:
        e.load_rules(name, text)
    errors = [d for d in e.rule_diagnostics() if d["severity"] == "error"]
    if errors:
        sys.exit("rule files have errors: %s" % errors)
    return e


def run_case(cid, paths, inline, sources, req):
    from pssparser.parser import ParseException, Parser
    e = engine_for(paths, inline)
    p = Parser()
    try:
        p.parses(sources)
        p.link()
    except ParseException:
        pass
    errors = sum(1 for m in p.markers if m["severity"] == "error")
    r = e.run(p.user_units(), native_request(req, errors))
    assert r["ok"], r
    return {
        "id": "run:" + cid,
        "kind": "run",
        "ruleFiles": list(paths),
        "ruleTexts": [{"name": n, "text": t} for n, t in inline],
        "sources": [{"name": n, "text": t} for n, t in sources],
        "request": req,
        "markers": normal(named(r["markers"], p.file_map)),
        "stats": [{k: v for k, v in s.items() if k != "ns"} for s in r["stats"]],
        "problems": r["problems"],
    }


def example_cases():
    from pssparser.lint.examples import run_examples
    e = engine_for(EXAMPLE_FILES, [])
    out = []
    for r in run_examples(e):
        out.append({
            "id": "example:%s:%s" % (r.rule, r.name),
            "kind": "example",
            "rule": r.rule,
            "name": r.name,
            "file": r.file,
            "line": r.line,
            "col": r.col,
            "ok": r.ok,
            "markers": normal(r.markers),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    cases = example_cases()
    cases += [run_case(*r) for r in RUNS]
    doc = {
        "generator": "ts/scripts/gen-lint-parity-fixture.py",
        "ruleFiles": EXAMPLE_FILES,
        "cases": cases,
    }
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
