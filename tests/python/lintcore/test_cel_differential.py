"""
Differential test of the lint engine's CEL against cel-python
(lint-core-plan.md C3.4).

scripts/cel_differential.py's generator writes random, well-typed,
pure-value expressions; each is evaluated by the engine and by cel-python
(celpy), and both must give the same value, or both an error. Each must also
type-check, since the generator is type-directed, and the checked expression
must give the same value as the unchecked one.

cel-python deviates from the spec in ways the generator avoids (D1-D4 in the
script's header). D5, an error escaping a comprehension, is not avoided: it
is rare, does not occur in the fixed run, and a disagreement of its shape is
counted rather than failed (the conformance suite's logic.json is the
arbiter of `&&` and `||`).

The fixed run is CEL_DIFF_N (2000) expressions from CEL_DIFF_SEED (1); a
larger run on request:

    CEL_DIFF_N=50000 CEL_DIFF_SEED=7 pytest tests/python/lintcore/test_cel_differential.py
"""
import importlib.util
import os
import random
import re

import pytest

celpy = pytest.importorskip("celpy", reason="cel-python is not installed (ivpm default-dev)")

_spec = importlib.util.spec_from_file_location("cel_differential", os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scripts", "cel_differential.py"))
cel_differential = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cel_differential)

_N = int(os.environ.get("CEL_DIFF_N", "2000"))
_SEED = int(os.environ.get("CEL_DIFF_SEED", "1"))
_TYPES = ["int", "bool", "string", "list_int", "double", "map_si"]


def _d5(expr, mine, theirs):
    """
    Has the disagreement the shape of D5? cel-python lets an error inside a
    comprehension escape, so `&&` and `||` cannot absorb it: the spec (and
    the engine, which logic.json tests) gives a bool, cel-python an error.
    None in the fixed run; about 1 in 20000 expressions in a larger one.
    """
    return (mine[0] == "bool" and theirs == ("error",)
            and ("&&" in expr or "||" in expr)
            and any(m in expr for m in (".all(", ".exists(", ".exists_one(", ".map(", ".filter(")))


@pytest.fixture(scope="module")
def expressions():
    rnd = random.Random(_SEED)
    out = []
    for _ in range(_N):
        ty = rnd.choice(_TYPES)
        out.append((ty, cel_differential.Gen(rnd).gen(ty)))
    return out


def test_against_celpy(factory, expressions):
    hooks = factory._lintTestHooks()
    env = celpy.Environment()
    bad = []
    errors = 0
    d5 = 0
    for _, expr in expressions:
        ours = hooks.cel_eval(expr)
        assert ours["ok"], (expr, ours)
        try:
            theirs = cel_differential.canon_celpy(
                celpy, env.program(env.compile(expr)).evaluate({}))
        except Exception:
            theirs = ("error",)
        mine = cel_differential.canon_ours(ours["result"])
        errors += mine == ("error",)
        if mine == theirs:
            continue
        if _d5(expr, mine, theirs):
            d5 += 1
        else:
            bad.append("%s\n    ours=%s\n   celpy=%s" % (expr, mine, theirs))
    assert not bad, "%d of %d disagree:\n%s" % (len(bad), len(expressions), "\n".join(bad[:20]))
    assert d5 <= len(expressions) // 1000
    # Both kinds of outcome are exercised: values and run-time errors.
    assert 0 < errors < len(expressions)


_CEL_TYPE = {"int": "int", "bool": "bool", "string": "string", "double": "double",
             "list_int": "list(int)", "map_si": "map(string, int)"}


def _fits(got, want):
    """`got` is `want`, or more general: '?' (a type no element fixed, as of
    `[]`) stands for any type."""
    pattern = re.escape(got).replace(re.escape("?"), "[^,()]+(?:\\(.*?\\))?")
    return re.fullmatch(pattern, want) is not None


def test_checked(factory, expressions):
    # Well-typed by construction, so each type-checks, to the type it was
    # generated for, and evaluates as it does unchecked. The nesting limit is
    # lifted: it is the profile's, and the generator does not keep to it.
    # The one refusal allowed is of an operand whose type nothing fixes, as
    # in `-({}['b'])`: with no dyn the checker cannot choose the overload.
    hooks = factory._lintTestHooks()
    bad = []
    unknown = 0
    for ty, expr in expressions:
        r = hooks.cel_check({"expr": expr, "max_nesting": 99})
        unchecked = hooks.cel_eval(expr)
        if r["errors"]:
            if all("not known" in e["message"] for e in r["errors"]):
                unknown += 1
            else:
                bad.append("%s\n    %s" % (expr, r["errors"][0]["message"]))
        elif not _fits(r["types"]["expr"], _CEL_TYPE[ty]):
            bad.append("%s\n    type %s, generated as %s" % (expr, r["types"]["expr"], _CEL_TYPE[ty]))
        elif (r["values"]["expr"] != unchecked["result"]
              or r["calls"]["expr"] != unchecked["calls"]):
            bad.append("%s\n    checked %s, unchecked %s" % (
                expr, r["values"]["expr"], unchecked["result"]))
    assert not bad, "%d of %d:\n%s" % (len(bad), len(expressions), "\n".join(bad[:20]))
    assert unknown < len(expressions) // 20
