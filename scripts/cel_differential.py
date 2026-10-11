#!/usr/bin/env python3
#****************************************************************************
#* cel_differential.py
#*
#* Differential test of the lint engine's CEL evaluator against cel-python,
#* on randomly generated, well-typed, pure-value expressions
#* (lint-core-plan.md C0 measurement; seeds C3.4's test_cel_differential.py).
#*
#*   PYTHONPATH=python python scripts/cel_differential.py \
#*       [--celpy <site-packages holding celpy>] [-n 2000] [--seed 1] [-v]
#*
#* cel-python is in ivpm.yaml's default-dev set; --celpy points at another
#* install. tests/python/lintcore/test_cel_differential.py runs the same
#* generator under pytest.
#*
#* The generator is type-directed so nearly every expression type-checks;
#* errors still occur at run time (division by zero, overflow, index out of
#* range, missing key) and must agree too: both sides an error, or both the
#* same value.
#*
#* What it stays away from, and why. cel-python 0.5 predates CEL's
#* heterogeneous numeric equality (`1 == 1.0` is an error there and `true` in
#* the current spec) and has no `cel.bind`. It also deviates from the spec in
#* four ways found by this script (C0, 2026-10-10), each confirmed by
#* evaluating the minimal case in both implementations:
#*
#*   D1  x / 0.0 is always +inf (IEEE 754: -1.5/0.0 is -inf, 0.0/0.0 is NaN)
#*   D2  a concatenated string loses its CEL type: ('q' + 'a').contains('a')
#*       is "no such overload"
#*   D3  negative list indexes count from the end, as in Python: [1,2][-1]
#*       is 2 (spec: index out of range)
#*   D4  an error inside a map literal is stored as a value instead of making
#*       the literal an error
#*   D5  an error inside a comprehension escapes as an exception, so `&&` and
#*       `||` cannot absorb it: [1].exists_one(v, {}['a'] == v) && false is an
#*       error there and false in the spec. Rare at the default depth (seen
#*       once in 2000 expressions at --depth 7); not avoided, so it can show
#*       up as a disagreement
#*
#* The generator avoids them (non-zero literal divisors for doubles, literal
#* receivers for string methods, indexes 0..3, literal map values). They and
#* everything else cel-python cannot judge are covered by the conformance
#* suite, which is the arbiter where the two disagree.
#****************************************************************************
import argparse
import json
import math
import random
import sys


class Gen:
    def __init__(self, rnd, max_depth=4):
        self.r = rnd
        self.max_depth = max_depth
        self.vars = []      # (name, type) in scope
        self.nvar = 0

    def pick(self, *opts):
        return self.r.choice(opts)

    def var_of(self, ty):
        c = [n for n, t in self.vars if t == ty]
        return self.r.choice(c) if c else None

    def gen(self, ty, d=0):
        leaf = d >= self.max_depth or self.r.random() < 0.25
        v = self.var_of(ty)
        if v is not None and self.r.random() < 0.3:
            return v
        return getattr(self, "g_" + ty)(d, leaf)

    # -- int ---------------------------------------------------------------
    def int_lit(self):
        k = self.r.random()
        if k < 0.7:
            return str(self.r.randint(-20, 20))
        if k < 0.85:
            return str(self.r.choice([0, 1, -1, 2, 7]))
        return str(self.r.choice([9223372036854775807, -9223372036854775807,
                                  4611686018427387904, 3037000500]))

    def g_int(self, d, leaf):
        if leaf:
            return self.int_lit()
        k = self.r.randint(0, 9)
        if k <= 3:
            op = self.pick("+", "-", "*", "/", "%")
            return "(%s %s %s)" % (self.gen("int", d + 1), op, self.gen("int", d + 1))
        if k == 4:
            return "-(%s)" % self.gen("int", d + 1)
        if k == 5:
            return "size(%s)" % self.gen(self.pick("string", "list_int"), d + 1)
        if k == 6:
            return "%s[%s]" % (self.gen("list_int", d + 1), self.r.randint(0, 3))     # D3
        if k == 7:
            return "(%s ? %s : %s)" % (self.gen("bool", d + 1), self.gen("int", d + 1),
                                       self.gen("int", d + 1))
        if k == 8:
            return "%s[%s]" % (self.gen("map_si", d + 1), self.str_lit(keys=True))
        return "%s.filter(%s).size()" % (self.gen("list_int", d + 1), self.lambda_("bool", d))

    # -- double ------------------------------------------------------------
    def g_double(self, d, leaf):
        if leaf:
            return self.pick("0.5", "1.0", "2.0", "0.25", "-1.5", "3.0", "1e3", "0.0")
        k = self.r.randint(0, 4)
        if k <= 1:
            op = self.pick("+", "-", "*")
            return "(%s %s %s)" % (self.gen("double", d + 1), op, self.gen("double", d + 1))
        if k == 2:
            # D1: a non-zero literal divisor
            return "(%s / %s)" % (self.gen("double", d + 1), self.pick("0.5", "2.0", "-1.5", "1e3"))
        if k == 3:
            return "double(%s)" % self.gen("int", d + 1)
        return "(%s ? %s : %s)" % (self.gen("bool", d + 1), self.gen("double", d + 1),
                                   self.gen("double", d + 1))

    # -- bool --------------------------------------------------------------
    def g_bool(self, d, leaf):
        if leaf:
            return self.pick("true", "false")
        k = self.r.randint(0, 9)
        if k <= 1:
            ty = self.pick("int", "string", "double", "bool")
            op = self.pick("==", "!=", "<", "<=", ">", ">=")
            return "(%s %s %s)" % (self.gen(ty, d + 1), op, self.gen(ty, d + 1))
        if k == 2:
            ty = self.pick("list_int", "map_si")
            return "(%s %s %s)" % (self.gen(ty, d + 1), self.pick("==", "!="), self.gen(ty, d + 1))
        if k == 3:
            return "(%s %s %s)" % (self.gen("bool", d + 1), self.pick("&&", "||"),
                                   self.gen("bool", d + 1))
        if k == 4:
            return "!(%s)" % self.gen("bool", d + 1)
        if k == 5:
            return "(%s in %s)" % (self.gen("int", d + 1), self.gen("list_int", d + 1))
        if k == 6:
            return "(%s in %s)" % (self.str_lit(keys=True), self.gen("map_si", d + 1))
        if k == 7:
            fn = self.pick("contains", "startsWith", "endsWith")
            return "%s.%s(%s)" % (self.str_lit(), fn, self.gen("string", d + 1))     # D2
        m = self.pick("all", "exists", "exists_one")
        return "%s.%s(%s)" % (self.gen("list_int", d + 1), m, self.lambda_("bool", d))

    # -- string ------------------------------------------------------------
    def str_lit(self, keys=False):
        if keys:
            return self.pick("'a'", "'b'", "'c'")
        return self.pick("''", "'a'", "'ab'", "'abc'", "'b'", "'héllo'", "'x y'", "\"q\"")

    def g_string(self, d, leaf):
        if leaf:
            return self.str_lit()
        k = self.r.randint(0, 3)
        if k <= 1:
            return "(%s + %s)" % (self.gen("string", d + 1), self.gen("string", d + 1))
        if k == 2:
            return "string(%s)" % self.gen("int", d + 1)
        return "(%s ? %s : %s)" % (self.gen("bool", d + 1), self.gen("string", d + 1),
                                   self.gen("string", d + 1))

    # -- list<int>, map<string,int> ----------------------------------------
    def g_list_int(self, d, leaf):
        if leaf:
            n = self.r.randint(0, 4)
            return "[%s]" % ", ".join(self.int_lit() for _ in range(n))
        k = self.r.randint(0, 3)
        if k == 0:
            return "(%s + %s)" % (self.gen("list_int", d + 1), self.gen("list_int", d + 1))
        if k == 1:
            return "%s.map(%s)" % (self.gen("list_int", d + 1), self.lambda_("int", d))
        if k == 2:
            return "%s.filter(%s)" % (self.gen("list_int", d + 1), self.lambda_("bool", d))
        n = self.r.randint(1, 3)
        return "[%s]" % ", ".join(self.gen("int", d + 1) for _ in range(n))

    def g_map_si(self, d, leaf):
        keys = self.r.sample(["a", "b", "c"], self.r.randint(0, 3))
        # D4: literal values only
        return "{%s}" % ", ".join("'%s': %s" % (k, self.int_lit()) for k in keys)

    def lambda_(self, body_ty, d):
        self.nvar += 1
        name = "v%d" % self.nvar
        self.vars.append((name, "int"))
        body = self.gen(body_ty, d + 1)
        self.vars.pop()
        return "%s, %s" % (name, body)


def canon_ours(v):
    t, x = v["type"], v["value"]
    if t == "error":
        return ("error",)
    if t == "list":
        return ("list", tuple(canon_ours(e) for e in x))
    if t == "map":
        return ("map", frozenset((canon_ours(k), canon_ours(e)) for k, e in x))
    if t == "double":
        if isinstance(x, str):
            x = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}[x]
        return ("double", "nan" if math.isnan(x) else math.copysign(0.0, x) if x == 0 else float(x))
    return (t, x)


def canon_celpy(celpy, r):
    ct = celpy.celtypes
    if isinstance(r, celpy.CELEvalError) or isinstance(r, Exception):
        return ("error",)
    if isinstance(r, (ct.BoolType, bool)):
        return ("bool", bool(r))
    if isinstance(r, (ct.IntType, int)):
        return ("int", int(r))
    if isinstance(r, (ct.DoubleType, float)):
        f = float(r)
        return ("double", "nan" if math.isnan(f) else math.copysign(0.0, f) if f == 0 else f)
    if isinstance(r, (ct.StringType, str)):
        return ("string", str(r))
    if isinstance(r, (ct.ListType, list)):
        return ("list", tuple(canon_celpy(celpy, e) for e in r))
    if isinstance(r, (ct.MapType, dict)):
        return ("map", frozenset((canon_celpy(celpy, k), canon_celpy(celpy, v)) for k, v in r.items()))
    return ("?", repr(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--celpy", help="site-packages directory holding celpy, if not importable")
    ap.add_argument("-n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()

    if a.celpy:
        sys.path.insert(0, a.celpy)
    import celpy
    from pssparser import core
    hooks = core.Factory.inst()._lintTestHooks()
    env = celpy.Environment()

    rnd = random.Random(a.seed)
    stats = {"agree_value": 0, "agree_error": 0, "disagree": 0, "celpy_compile_error": 0,
             "ours_parse_error": 0}
    bad = []
    for i in range(a.n):
        ty = rnd.choice(["int", "bool", "string", "list_int", "double", "map_si"])
        expr = Gen(rnd, a.depth).gen(ty)
        ours = hooks.cel_eval(expr)
        if not ours["ok"]:
            stats["ours_parse_error"] += 1
            bad.append((expr, "ours: " + ours["error"]["message"], ""))
            continue
        try:
            prog = env.program(env.compile(expr))
        except Exception as ex:
            stats["celpy_compile_error"] += 1
            continue
        try:
            theirs = canon_celpy(celpy, prog.evaluate({}))
        except Exception:
            theirs = ("error",)
        mine = canon_ours(ours["result"])
        if mine == theirs:
            stats["agree_error" if mine == ("error",) else "agree_value"] += 1
        else:
            stats["disagree"] += 1
            bad.append((expr, mine, theirs))

    print(json.dumps(stats))
    for e, m, t in bad[:40 if a.v else 10]:
        print("  %s\n     ours=%s\n   celpy=%s" % (e, m, t))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
