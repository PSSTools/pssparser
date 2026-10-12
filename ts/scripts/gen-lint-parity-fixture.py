#!/usr/bin/env python3
"""Record what the native lint runner reports, for the TS tests.

    cd .. && PYTHONPATH=python packages/python/bin/python \\
        ts/scripts/gen-lint-parity-fixture.py -o ts/test/fixtures/lint-parity.json

Five kinds of case (lint-core-plan.md C5.5, C7.1, C7.2, C7.3):

* ``example``: every example of every built-in rule and of the rule files in
  tests/data/lint-examples/, run by ``pssparser.lint.examples`` (each example
  parsed and linked on its own, only its rule enabled). The case records
  whether it passed and the markers the rule gave.
* ``run``: rule files and a model, run with a request (enabled rules,
  options, a step budget), as ``LintEngine.run`` and ``Parser.runLint`` do.
  The case records the markers, the per-rule statistics (without the time)
  and the request problems. A request may carry a ``selection`` (C7.1).
* ``selection``: a rule selection and paths, resolved over the example rule
  files (``LintEngine.resolve_selection``, ``Parser.resolveSelection``). The
  case records the whole answer.
* ``waivers``: host markers, a model with source waivers and diagnostics to
  apply them to (``LintEngine.collect_waivers`` and ``apply_waivers``;
  ``Parser.collectWaivers`` and ``applyWaivers``). The case records the
  waivers collected and the whole answer.
* ``catalog``: the marker catalogue (``LintEngine.catalog``,
  ``Parser.catalog``) with the example rule files loaded, with and without
  host markers; and the markers of a model with core errors and warnings,
  whose codes the core gives them (``code`` on every marker).

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

#: Every named-declaration kind, and a reported declaration: each finding is
#: at the declaration's name, not across its body (linter-post-readiness E1).
NAME_SPAN = """\
pss-rules:
  rules:
    - id: ACME010
      name: named
      tier: suspicious
      summary: s
      message: m
      match: { kind: [Component, Action, Struct, Field, EnumDecl, EnumItem, FunctionPrototype, PackageScope, FunctionDefinition] }
    - id: ACME011
      name: field-type
      tier: suspicious
      summary: s
      message: m
      match: { kind: Field }
      report: >-
        type(node.type) == DataTypeUserDefined
          ? [resolves_to(node.type.type_id)] : []
"""

NAMED = """\
component dma { action Xfer { rand S_t f_one; } }
struct S_t { int x; }
enum E_t { A, B }
function void fn_a() { }
package a::bb { }
"""

#: file_of() with the host's names and a base directory (C6.9).
WHERE = """\
pss-rules:
  rules:
    - id: ACME009
      name: where-is-it
      tier: suspicious
      summary: s
      message: "${file_of(node).path} ${file_of(node).dir} ${file_of(node).stem}"
      match: { kind: Component }
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
    ("name-span", [], [("name-span.yaml", NAME_SPAN)], [("named.pss", NAMED)], {}),
    ("base-dir", [], [("where.yaml", WHERE)],
     [("/proj/ip/./a_c.pss", "component a_c { }\n"),
      ("/elsewhere/b_c.pss", "component b_c { }\n")],
     {"baseDir": "/proj"}),
    # Per-path selection (C7.1): an override turns a rule off under tests/,
    # another sets an option under ip/; the base directory is the request's.
    ("selection", EXAMPLE_FILES, [],
     [("/proj/ip/m.pss", MODEL),
      ("/proj/tests/t.pss", "component t_top { action Long_name { rand bit[8] len; } }\n")],
     {"baseDir": "/proj",
      "selection": {"lint": {"profile": "none", "select": ["ACME"],
                             "overrides": [{"files": ["tests/**"], "ignore": ["ACME001"]},
                                           {"files": ["ip"],
                                            "rule": {"ACME002": {"prefix": "le"}}}]},
                    "severity": {"ACME003": "off"}}}),
    ("selection-problems", EXAMPLE_FILES, [], [("m.pss", MODEL)],
     {"enabled": ["ACME001"],
      "selection": {"lint": {"select": ["ACME01"], "rule": {"ACME002": {"nope": 1}}}}}),
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


def native_request(req, errors, file_map):
    # As Parser.runLint() builds it: the parser's file names always go.
    out = {"gate_errors": req.get("gateErrors", errors),
           "files": {str(i): n for i, n in file_map.items()}}
    for ts, py in (("enabled", "enabled"), ("options", "options"), ("maxSteps", "max_steps"),
                   ("baseDir", "base_dir"), ("selection", "selection")):
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
    r = e.run(p.user_units(), native_request(req, errors, p.file_map), model=p._root)
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


#: resolveSelection() over the example rules: (id, selection, paths).
SELECTIONS = [
    ("profiles-and-selectors",
     {"lint": {"profile": "all", "select": ["ACME0", "family:naming"], "ignore": ["ACME002"],
               "rules-version": "2026.1"},
      "command_line": {"select": ["ACME002"]},
      "severity": {"ACME": "error", "suspicious": "info"},
      "warnings": {"error": ["info", "ACME"], "no-error": ["ACME003"]}},
     []),
    ("overrides",
     {"lint": {"profile": "none", "select": ["ACME"],
               "overrides": [{"files": ["tests/**", "*_gen.pss"], "ignore": ["ACME001"]},
                             {"files": ["ip/legacy"], "profile": "all",
                              "rule": {"ACME002": {"prefix": "x"}}}]},
      "base_dir": "/proj"},
     ["/proj/a.pss", "/proj/tests/x/t.pss", "/proj/ip/legacy/l_gen.pss", "/other/z.pss"]),
    ("errors",
     {"lint": {"select": ["ACME01", "family:nope"], "profile": "most",
               "overrides": [{"select": ["x"]}], "rule": {"nope": {}}},
      "command_line": {"ignore": ["acme"]}},
     []),
]


def selection_cases():
    e = engine_for(EXAMPLE_FILES, [])
    out = []
    for cid, sel, paths in SELECTIONS:
        r = e.resolve_selection(dict(sel, paths=paths))
        assert r["ok"], r
        del r["ok"]
        out.append({"id": "selection:" + cid, "kind": "selection", "selection": sel,
                    "paths": paths, "result": r})
    return out


#: The host markers the waiver cases resolve against (as the CLI's registry
#: would give them): core errors, the hygiene markers, a retired code, an
#: alias, and lint rules. The example rule files are loaded too.
WAIVER_HOST = [
    {"id": "PSS002", "severity": "error"},
    {"id": "PSSP000", "severity": "error", "tier": "tool"},
    {"id": "PSSP004", "severity": "info", "tier": "tool"},
    {"id": "PSSP202", "severity": "warning", "tier": "tool"},
    {"id": "PSSP203", "severity": "warning", "tier": "tool"},
    {"id": "PSSP204", "severity": "warning", "tier": "tool"},
    {"id": "PSSP205", "severity": "warning", "tier": "tool"},
    {"id": "PSS053", "status": "retired", "replaced_by": ["LINT402"]},
    {"id": "LINT401", "name": "import-shadow", "tier": "suspicious", "family": "import"},
    {"id": "LINT402", "name": "import-after-declaration", "tier": "style",
     "family": "import", "aliases": ["LINT499"], "minimal": True},
]

WAIVER_MODEL = """\
package p {
  struct t {}
  import std_pkg::*;  // pssparser waive LINT402: vendored
  @lint_pkg::waive {.id = "PSS053"}
  struct u {}
  @lint_pkg::waive {.id = "LINT40X, PSS002", .reason = "r"};
}
// pssparser waive import-after-declaration, LINT499: \u00e9t\u00e9
component C {
  @lint_pkg::waive {.id = "family:import", .reason = "r"}
  int a;
  exec init_down {
    @lint_pkg::waive {.id = "ACME", .reason = "r"}
    a = 1;
  }
}
"""

#: (id, sources, diagnostics, ran).
WAIVERS = [
    ("collect-and-apply", [("m.pss", WAIVER_MODEL), ("n.pss", "// pssparser waive: x\n")],
     [{"code": "LINT402", "file": "m.pss", "line": 3, "col": 3},
      {"code": "LINT402", "file": "m.pss", "line": 5, "col": 10},
      {"code": "PSS002", "file": "m.pss", "line": 6, "col": 1},
      {"code": "LINT401", "file": "m.pss", "line": 9, "col": 1},
      {"code": "LINT401", "file": "m.pss", "line": 11, "col": 7},
      {"code": "ACME001", "file": "m.pss", "line": 14, "col": 5},
      {"code": "PSSP205", "file": "m.pss", "line": 4, "col": 3},
      {"code": None, "file": "m.pss", "line": 3, "col": 3}],
     ["LINT401", "LINT402", "ACME001", "ACME002"]),
    ("ran-unknown", [("m.pss", WAIVER_MODEL)], [], None),
]


def waiver_cases():
    from pssparser.parser import ParseException, Parser
    e = engine_for(EXAMPLE_FILES, [])
    assert e.set_host_markers(WAIVER_HOST) == []
    out = []
    for cid, sources, diags, ran in WAIVERS:
        p = Parser()
        try:
            p.parses(sources)
            p.link()
        except ParseException:
            sys.exit("waiver case %s does not link: %s" % (cid, p.markers))
        c = e.collect_waivers(p.user_units(), dict(sources), p.file_map)
        assert c["ok"], c
        r = e.apply_waivers(c["waivers"], [dict(d, code=d["code"] or "") for d in diags], ran)
        assert r["ok"], r
        del r["ok"]
        out.append({"id": "waivers:" + cid, "kind": "waivers", "hostMarkers": WAIVER_HOST,
                    "sources": [{"name": n, "text": t} for n, t in sources],
                    "diagnostics": diags, "ran": ran, "waivers": c["waivers"], "result": r})
    return out


#: Core markers of several kinds, none of which has its code set where it is
#: emitted but LINT402: the collector gives them theirs.
CODES_MODEL = """\
package p { struct s {} import std_pkg::*; }
component pss_top {
  nosuch_t f;
  int a;
  int a;
  action A { activity { undefined_action b; } }
}
"""


def catalog_cases():
    from pssparser.parser import ParseException, Parser
    out = []
    e = engine_for(EXAMPLE_FILES, [])
    out.append({"id": "catalog:engine", "kind": "catalog", "hostMarkers": None,
                "result": e.catalog()})
    assert e.set_host_markers(WAIVER_HOST) == []
    # With host markers only the entries' metadata changes; record that much.
    keys = ("id", "name", "tier", "severity", "status", "aliases", "minimal", "source")
    out.append({"id": "catalog:host", "kind": "catalog", "hostMarkers": WAIVER_HOST,
                "keys": list(keys),
                "result": [{k: m[k] for k in keys} for m in e.catalog()["markers"]]})
    p = Parser()
    sources = [("m.pss", CODES_MODEL)]
    try:
        p.parses(sources)
        p.link()
    except ParseException:
        pass
    markers = normal([dict(m, code=m.get("code") or "") for m in p.markers])
    assert markers and all(m["code"] for m in markers), markers
    out.append({"id": "catalog:marker-codes", "kind": "marker-codes",
                "sources": [{"name": n, "text": t} for n, t in sources], "markers": markers})
    return out


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
    cases += selection_cases()
    cases += waiver_cases()
    cases += catalog_cases()
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
