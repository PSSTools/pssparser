"""
The CEL conformance suite (lint-core-plan.md C3.4).

The cel-spec v0.25.3 tests converted into tests/data/cel-conformance/ by
scripts/import_cel_conformance.py, run through the lint engine twice:

- unchecked, through the `cel_eval` hook, as C3.1 evaluates a parsed
  expression;
- checked, through the `cel_check` hook, as a rule's expressions run: each
  test that passes unchecked is type-checked against its `type_env`, and the
  checked expression must give the expected value, and the same value and
  call trace as the unchecked one. An expected evaluation error that the
  checker reports instead passes: the error is found earlier.

A test may be *excluded* only because the engine refuses it: an expression
outside the pss-rules profile (the parser's profile error), a name the
profile leaves out (`timestamp`, `uint`: an undeclared reference at run
time), a value or binding the profile has no type for (bytes, uint,
messages), or, checked, a check error where cel-spec expects a value (most
need `dyn`; cel-spec itself marks some `disable_check`). A wrong value is
never an exclusion.

The excluded tests and the reason for each are kept in
cel_conformance_excluded.txt, with the number of tests each file runs, so a
change to the profile or the checker that runs more or fewer tests shows up
as a diff. After an intended change, regenerate it:

    CEL_CONFORMANCE_BLESS=1 pytest tests/python/lintcore/test_cel_conformance.py
"""
import glob
import json
import math
import os

import pytest

_HERE = os.path.dirname(__file__)
_DATA = os.path.join(_HERE, "..", "..", "data", "cel-conformance")
_FILES = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(_DATA, "*.json")))
_EXCLUDED = os.path.join(_HERE, "cel_conformance_excluded.txt")


class _Unsupported(Exception):
    """A value or type the profile has no counterpart for."""


# -------------------------------------------------- cel-spec's values ------

def _expected(v):
    """A cel-spec `Value` as (type, value), the form _actual() gives."""
    (k, x), = v.items()
    if k == "bool_value":
        return ("bool", x[0] == "true")
    if k == "int64_value":
        return ("int", int(x[0]))
    if k == "double_value":
        return ("double", float(x[0]))
    if k == "string_value":
        return ("string", x[0])
    if k == "null_value":
        return ("null_type", None)
    if k == "type_value":
        return ("type", x[0])
    if k == "list_value":
        return ("list", tuple(_expected(e) for e in (x[0].get("values", []) if x else [])))
    if k == "map_value":
        ents = x[0].get("entries", []) if x else []
        return ("map", frozenset((_expected(e["key"][0]), _expected(e["value"][0]))
                                 for e in ents))
    raise _Unsupported("expects a %s" % k[:-len("_value")])


def _actual(r):
    """The engine's result as (type, value)."""
    t, v = r["type"], r["value"]
    if t == "list":
        return ("list", tuple(_actual(e) for e in v))
    if t == "map":
        return ("map", frozenset((_actual(a), _actual(b)) for a, b in v))
    if t == "double":
        if isinstance(v, str):
            v = {"Infinity": math.inf, "-Infinity": -math.inf, "NaN": math.nan}[v]
        return ("double", float(v))
    if t == "optional_type":
        return ("optional", None if v is None else _actual(v))
    return (t, v)


def _same(a, b):
    if a[0] == "double" and b[0] == "double":
        return a[1] == b[1] or (math.isnan(a[1]) and math.isnan(b[1]))
    if a[0] == "list" and b[0] == "list":
        return len(a[1]) == len(b[1]) and all(_same(x, y) for x, y in zip(a[1], b[1]))
    return a == b


def _json(v):
    """A binding's value as JSON, which the hooks type from the value."""
    t, x = v
    if t == "list":
        return [_json(e) for e in x]
    if t == "map" and all(k[0] == "string" for k, _ in x):
        return {k[1]: _json(e) for k, e in x}
    if t in ("bool", "int", "string", "null_type") or (t == "double" and x != int(x)):
        return x
    raise _Unsupported("binds a %s" % t)


_PRIMITIVE = {"BOOL": "bool", "INT64": "int", "DOUBLE": "double", "STRING": "string"}


def _type(t):
    """A cel-spec `Type` as the checker writes it."""
    (k, x), = t.items()
    if k == "primitive" and x[0] in _PRIMITIVE:
        return _PRIMITIVE[x[0]]
    if k == "null":
        return "null_type"
    if k == "list_type":
        return "list(%s)" % _type(x[0]["elem_type"][0])
    if k == "map_type":
        return "map(%s, %s)" % (_type(x[0]["key_type"][0]), _type(x[0]["value_type"][0]))
    raise _Unsupported("declares a %s" % (x[0].lower() if k == "primitive" else k))


# ------------------------------------------------------------- the run -----

def _run(hooks, t):
    """
    One test, unchecked and checked. Returns (unchecked, checked), each
    ("pass", None), ("fail", why), ("excluded", reason) or, checked only,
    ("not-run", None) when the unchecked run did not pass.
    """
    fl = t["fields"]
    parsed = hooks.cel_parse(t["expr"])
    if not parsed["ok"]:
        return ("fail", "syntax error: " + parsed["error"]["message"]), ("not-run", None)
    if parsed["profile_errors"]:
        return ("excluded", parsed["profile_errors"][0]["message"]), ("not-run", None)
    try:
        want = _expected(fl["value"][0]) if "value" in fl else None
        bindings = {b["key"][0]: _json(_expected(b["value"][0]["value"][0]))
                    for b in fl.get("bindings", [])}
        decls = {d["name"][0]: _type(d["ident"][0]["type"][0]) for d in fl.get("type_env", [])}
    except _Unsupported as e:
        return ("excluded", str(e)), ("not-run", None)

    def verdict(got):
        if want is None:
            return ("pass", None) if got[0] == "error" else ("fail", "got %r, want an error" % (got,))
        if _same(got, want):
            return ("pass", None)
        if got[0] == "error" and got[1].startswith("undeclared reference"):
            return ("excluded", got[1])
        return ("fail", "got %r, want %r" % (got, want))

    unchecked = hooks.cel_eval(t["expr"], 0, bindings or None)
    assert unchecked["ok"], unchecked
    u = verdict(_actual(unchecked["result"]))
    if u[0] != "pass":
        return u, ("not-run", None)

    doc = {"expr": t["expr"]}
    if decls:
        doc["vars"] = decls
    if bindings:
        doc["bindings"] = bindings
    checked = hooks.cel_check(doc)
    assert checked["ok"], checked
    if checked["errors"]:
        if want is None:
            return u, ("pass", None)
        if "disable_check" in fl:
            return u, ("excluded", "cel-spec: disable_check")
        return u, ("excluded", checked["errors"][0]["message"])
    c = verdict(_actual(checked["values"]["expr"]))
    if c[0] == "pass" and (checked["values"]["expr"] != unchecked["result"]
                           or checked["calls"]["expr"] != unchecked["calls"]):
        c = ("fail", "checked and unchecked differ")
    return u, c


@pytest.fixture(scope="module")
def results(factory):
    hooks = factory._lintTestHooks()
    out = {}
    for f in _FILES:
        with open(os.path.join(_DATA, f + ".json"), encoding="utf-8") as fp:
            tests = json.load(fp)["tests"]
        out[f] = [("%s/%s/%s" % (f, t["section"], t["name"]), t["expr"], _run(hooks, t))
                  for t in tests]
    return out


@pytest.mark.parametrize("name", _FILES)
def test_conformance(results, name):
    fails = ["%s  %s\n    unchecked: %s" % (tid, expr, u[1])
             for tid, expr, (u, c) in results[name] if u[0] == "fail"]
    assert not fails, "\n".join(fails)


@pytest.mark.parametrize("name", _FILES)
def test_conformance_checked(results, name):
    fails = ["%s  %s\n    checked: %s" % (tid, expr, c[1])
             for tid, expr, (u, c) in results[name] if c[0] == "fail"]
    assert not fails, "\n".join(fails)


def _excluded_text(results):
    lines = [
        "# CEL conformance tests the lint engine does not run, and why",
        "# (tests/python/lintcore/test_cel_conformance.py). Generated: run",
        "#   CEL_CONFORMANCE_BLESS=1 pytest tests/python/lintcore/test_cel_conformance.py",
        "# after a change that is meant to run more or fewer tests.",
        "#",
        "# count <file> <tests> unchecked: <passed> <excluded> checked: <passed> <excluded>",
    ]
    for f in _FILES:
        n = lambda mode, what: sum(1 for _, _, r in results[f] if r[mode][0] == what)
        lines.append("count %s %d unchecked: %d %d checked: %d %d" % (
            f, len(results[f]), n(0, "pass"), n(0, "excluded"), n(1, "pass"), n(1, "excluded")))
    for mode, label in ((0, "unchecked"), (1, "checked")):
        lines += ["", "# %s: <file>/<section>/<test>  <reason>" % label]
        for f in _FILES:
            for tid, _, r in results[f]:
                if r[mode][0] == "excluded":
                    lines.append("%s %s  %s" % (label, tid, r[mode][1].replace("\n", " ")))
    return "\n".join(lines) + "\n"


def test_excluded_list(results):
    text = _excluded_text(results)
    if os.environ.get("CEL_CONFORMANCE_BLESS"):
        with open(_EXCLUDED, "w", encoding="utf-8") as fp:
            fp.write(text)
    with open(_EXCLUDED, encoding="utf-8") as fp:
        want = fp.read()
    if text != want:
        import difflib
        diff = "".join(difflib.unified_diff(
            want.splitlines(True), text.splitlines(True), "cel_conformance_excluded.txt", "now"))
        pytest.fail("the excluded conformance tests changed; if that is intended, regenerate "
                    "with CEL_CONFORMANCE_BLESS=1:\n" + diff)
