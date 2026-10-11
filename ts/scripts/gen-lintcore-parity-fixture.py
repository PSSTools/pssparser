#!/usr/bin/env python3
"""Record what the native lint engine's low-level pieces return, for the TS tests.

    cd .. && PYTHONPATH=python packages/python/bin/python \\
        ts/scripts/gen-lintcore-parity-fixture.py -o ts/test/fixtures/lintcore-parity.json

The lint engine's YAML layer, CEL parser and evaluator, and regex engine
(lint-core-plan.md C1.2, C1.4, C2, C3) and the rule loader (C4.1) return their results as JSON text from
private test hooks, built identically into the native and the WASM core. This
records the native text for a set of inputs; `ts/test/lintcore-parity.test.ts`
feeds the same inputs to the WASM hooks and compares the text byte for byte.

Short outputs are stored whole, so a failure shows the difference. Long ones
(a parsed `ast/*.yaml` file, a deep expression tree) are stored as a SHA-256
and a length, which keeps the committed fixture small; the case's `id` says
which input to rerun when one of those differs. Large input sets (generated
expressions, the CEL conformance files) are *batches*: one hash over all
their outputs, the conformance inputs read from tests/data/cel-conformance/.

Re-run it when an input set or the engine's output changes; the diff is then a
record of what changed.
"""

import argparse
import glob
import hashlib
import json
import os
import random
import sys

#: Outputs at most this long (in UTF-8 bytes) are stored whole.
INLINE_LIMIT = 512

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

YAML_INLINE = [
    ("typing", "on: off\nyes: no\nn: ~\nb: True\ni: 0x10\no: 0o17\nf: 1e3\n"
               "g: -.Inf\nh: .nan\nq: '1'\nv: 1.2.3\nz: -0\nbig: 9223372036854775808\n"),
    ("marks", "a: 1\nbb: [x, 'y']\nc:\n  - {k: v}\n  - \"dq\"\n"),
    ("block-scalars", "lit: |\n  line 1\n   line 2\nfold: >-\n  a\n  b\n\nkeep: |+\n  x\n\n"),
    ("anchors", "b: &x {k: 1}\nu: *x\nm:\n  <<: *x\n  j: 2\n"),
    ("json", '{"pss-rules": 1, "rules": [{"id": "A", "where": "true"}]}'),
    ("empty", ""),
    ("comment-only", "# nothing\n"),
    ("dup-key", "rules:\n  - id: A\n    id: B\n"),
    ("tag", "x: !!str 1\n"),
    ("multi-doc", "a: 1\n---\nb: 2\n"),
    ("two-colons", "a: b: c\n"),
    ("bad-indent", "a:\n  - x\n - y\n"),
    ("too-deep", "[" * 100 + "]" * 100),
    ("unicode", "k: 'héllo ☃'\n\"ключ\": 1\n"),
]

#: CEL errors in each scalar style, located in the YAML file (C2.2).
YAML_CEL = [
    ("plain.yaml", "where: a = b\n"),
    ("squo.yaml", "where: 'x == ''a'' &&\n  b = c'\n"),
    ("dquo.yaml", 'where: "\'\\t\\u00e9\' == x &&\\\n    b = c"\n'),
    ("literal.yaml", "where: |\n\n  a &&\n    b +\n"),
    ("folded.yaml", "rules:\n  - where: >-\n      a &&\n      b &&\n      c = d\n"),
    ("flow.yaml", "rules:\n- {id: X, where: \"a = b\"}\n- {id: Y, where: ok}\n"),
]

CEL_PARSE = [
    "1 + 2 * 3", "a || b && c", "a ? b : c ? d : e", "!!a", "-1", "--1", "-x.y",
    "a.b[1].c(d)", "x in [1, 2,]", "has(n.rhs)", "l.all(x, x > 0)", "a.?b", "a[?0]",
    "{?'k': v}", "-9223372036854775808", "r'\\d' + \"\"\"x\ny\"\"\"",
    "b'\\xff'", "1u", "pkg.Msg{f: 1}", "m.all(k, v, true)", ".a.b",
    "[1, 2].map(x, x > 1, x * 2)", "cel.bind(v, 1, v + 1)", "l.exists_one(x, x)",
    "l.existsOne(x, x)", "`a-b`", "x.`y.z`", "1.5e-3", "0x7fffffffffffffff",
    "'\\u00e9\\U0001F600\\x41\\101'", "// comment\n1",
    # errors
    "1 +", "a = b", "f(1,)", "if", "x.all(1, true)", "9223372036854775808", "'abc",
    "'\\q'", "(" * 70 + "1" + ")" * 70, "+".join(["a"] * 300), "a.b.", "{1:}",
]

CEL_EVAL = [
    "false && (1/0 == 1)", "(1/0 == 1) && false", "true || {}['x']", "{}['x'] || true",
    "1 == 1.0", "1 < 1.5", "[1, 2].map(x, x * 2)", "[1, 2, 3].exists_one(x, x > 2)",
    "[1, 2, 3].filter(x, x > 1).size()", "size('héllo')", "'abc'.matches('^a.c$')",
    "1.0 / 0.0", "-1.0 / 0.0", "0.0 / 0.0", "2.0", "1e300 * 1e300", "-0.0",
    "9223372036854775807 + 1", "-9223372036854775807 - 2", "1 / 0", "[1][1]", "[1][-1]",
    "{'a': 1/0}", "1 + 1.0", "x", "{'a': 1, 'b': [true, null]}", "string(1.5)",
    "int('12')", "int(2.9)", "double('1e3')", "dyn(1) == 1.0", "'a' < 'b'",
    "[1, 2] == [1, 2]", "{'a': 1} == {'a': 1.0}", "-9223372036854775808 / -1",
    "-9223372036854775808 % -1", "cel.bind(v, [1, 2], v + v)",
    # C3.1: optionals, types, enum constants
    "{'a': 1}.?a", "{}.?a.b", "[?optional.none(), ?optional.of(2)]", "{?'k': optional.none()}",
    "optional.of({'c': {}}).c.missing.orValue('d')", "optional.none().value()",
    "[1][?3].hasValue()", "type(1) == int", "type(optional.none())", "type(type)",
    "ExprBinOp.BinOp_Eq", "FieldAttr.Rand", "ExprBinOp.Nope", "type(null) == null_type",
]

# (expression, bindings JSON)
CEL_EVAL_BOUND = [
    ("x + y", '{"x": 1, "y": 2}'), ("m.a.exists(v, v > 1)", '{"m": {"a": [1, 2]}}'),
    ("int", '{"int": 3}'), ("s.size()", '{"s": "héllo"}'),
]

#: Type-checker documents (C3.3): types, errors located in the YAML, helpers.
CEL_CHECK = [
    ("ok.yaml", "expr: \"[1, 2].map(x, x * 2)\"\n"),
    ("types.json", json.dumps({"vars": {"n": "ExprBin", "l": "list(ScopeChild)"}, "run": False,
                               "expr": "[n.lhs, n.rhs, null].size() + "
                                       "l.filter(c, type(c) == Action).size()"})),
    ("error.yaml", "expr: |\n  1 +\n    'a'\n"),
    ("where.yaml", "where: >-\n  [1,\n   2]\n"),
    ("report.yaml", "vars: {node: ExprBin}\nreport: '[node.op]'\n"),
    ("nesting.yaml", "expr: '[[[1]]].all(a, a.all(b, b.all(c, c > 0)))'\n"),
    ("helpers.yaml", "define:\n  twice(x): x * 2\n  k: twice(21)\nlet:\n  d: k + 1\n"
                     "expr: twice(d)\n"),
    ("cycle.yaml", "define:\n  a(x): b(x)\n  b(y): >-\n    1 +\n    a(y)\nexpr: a(1)\n"),
    ("capture.yaml", "bindings: {n: 1}\ndefine:\n  f(a): a + n\nexpr: '[2].map(n, f(n))'\n"),
    ("no-dyn.yaml", "expr: \"[1, 'a'] == dyn(1)\"\n"),
    ("surrogates.json", '{"expr": "\'\\ud83d\\udc31\' + x"}'),
]

REGEX = [
    ("b+", "abbc"), ("^b", "abc"), ("(?i)HELLO", "say hello"),
    ("[[:digit:]]{2,3}$", "ab123"), ("\\bfoo\\b", "a foo b"), ("\\bfoo\\b", "afoob"),
    ("é+", "xééy"), ("a.c", "a\nc"), ("(?s)a.c", "a\nc"), ("x{", "x{"),
    ("[^a-z]", "abc1"), ("(?m)^b$", "a\nb\nc"), ("a|bc|", "zzz"), ("\\d+\\.\\d*", "v1.25"),
    ("[\\w-]+@", "a-b@c"), ("\\x41\\u00e9", "Aé"), ("(a)(b)?c", "ac"),
    # rejected
    ("a(?=b)", ""), ("(a)\\1", ""), ("\\pL", ""), ("a**", ""), ("a{2000}", ""), ("(a", ""),
    ("[a", ""), ("(" * 40 + "a" + ")" * 40, ""), ("[z-a]", ""), ("(?P<n>a)", ""),
    # linear time
    ("(a*)*b", "a" * 500), ("(x+x+)+y", "x" * 500),
]


def rule_files():
    for f in sorted(glob.glob(os.path.join(ROOT, "tests", "data", "pss-rules", "*"))):
        if not f.endswith((".expect", ".md")):
            with open(f, encoding="utf-8") as fp:
                yield os.path.relpath(f, ROOT), fp.read()


def yaml_files():
    pats = ["ast/*.yaml", ".github/workflows/*.yml", ".forgejo/workflows/*.yml", "ivpm.yaml"]
    for p in pats:
        for f in sorted(glob.glob(os.path.join(ROOT, p))):
            with open(f, encoding="utf-8") as fp:
                yield os.path.relpath(f, ROOT), fp.read()


def generated_cel(n, seed):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from cel_differential import Gen
    rnd = random.Random(seed)
    for _ in range(n):
        ty = rnd.choice(["int", "bool", "string", "list_int", "double", "map_si"])
        yield Gen(rnd, 5).gen(ty)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--generated", type=int, default=500,
                    help="generated CEL expressions, each parsed and evaluated")
    args = ap.parse_args()

    from pssparser import core
    hooks = core.Factory.inst()._lintTestHooks()

    cases = []

    def record(cid, fn, *fargs, inline=True, file=None, file_arg=None):
        out = hooks.raw(fn, *fargs)
        b = out.encode("utf-8")
        c = {"id": cid, "fn": fn, "args": list(fargs)}
        if file is not None:
            # The text is a repository file: the test reads it, rather than
            # the fixture carrying a copy. The text is the last argument, or
            # argument `file_arg`.
            c["args"][-1 if file_arg is None else file_arg] = None
            c["file"] = file
            if file_arg is not None:
                c["fileArg"] = file_arg
        if inline and len(b) <= INLINE_LIMIT:
            c["out"] = out
        else:
            c["sha256"] = hashlib.sha256(b).hexdigest()
            c["len"] = len(b)
        cases.append(c)

    for name, text in YAML_INLINE:
        record("yaml:" + name, "YamlLoad", name + ".yaml", text)
    for name, text in yaml_files():
        record("yaml-file:" + name, "YamlLoad", name, text, file=name)
        record("yaml-map:" + name, "YamlSourceMaps", name, text, file=name)
    for i, (name, text) in enumerate(YAML_CEL):
        record("yaml-cel:%d" % i, "YamlCelParse", name, text, "where")
    for name, text in YAML_INLINE:
        record("yaml-map:" + name, "YamlSourceMaps", name + ".yaml", text)
    for i, e in enumerate(CEL_PARSE):
        record("cel-parse:%d" % i, "CelParse", e)
    for i, e in enumerate(CEL_EVAL):
        record("cel-eval:%d" % i, "CelEval", e, "", 0)
    for i, (e, b) in enumerate(CEL_EVAL_BOUND):
        record("cel-eval-bound:%d" % i, "CelEval", e, b, 0)
    record("cel-eval:budget", "CelEval", "[" + ", ".join(["1"] * 100) + "].map(x, x + 1)", "", 50)
    # Batches: many inputs, one hash over all their outputs, so the fixture
    # stays small. When a batch differs, re-run its inputs one by one.
    batches = []

    def batch(bid, fn, inputs, extra, source=None, lead=(), wrap=None, wrap_with=None,
              inputs_of=None):
        # `lead`: arguments before the input; `wrap`: the input becomes the
        # JSON document {**wrap_with, wrap: input}, written as JSON.stringify
        # writes it; `inputs_of`: the inputs are those of that earlier batch.
        h = hashlib.sha256()
        for x in inputs:
            if wrap:
                x = json.dumps(dict(wrap_with or {}, **{wrap: x}), ensure_ascii=False,
                               separators=(",", ":"))
            h.update(hooks.raw(fn, *lead, x, *extra).encode("utf-8"))
            h.update(b"\0")
        b = {"id": bid, "fn": fn, "extra": list(extra), "sha256": h.hexdigest()}
        if lead:
            b["lead"] = list(lead)
        if wrap:
            b["wrap"] = wrap
        if wrap_with:
            b["wrapWith"] = wrap_with
        if inputs_of is not None:
            b["inputsOf"] = inputs_of
        elif source is None:
            b["inputs"] = inputs
        else:
            # The inputs are the `expr` of each test in this committed file.
            b["source"] = source
        batches.append(b)

    gen = list(generated_cel(args.generated, 1))
    batch("generated-parse", "CelParse", gen, [])
    batch("generated-eval", "CelEval", gen, ["", 0], inputs_of="generated-parse")
    # Checked: lifting the nesting limit, which the generator does not keep to.
    batch("generated-check", "CelCheck", gen, [], lead=["check.json"], wrap="expr",
          wrap_with={"max_nesting": 99}, inputs_of="generated-parse")
    for f in sorted(glob.glob(os.path.join(ROOT, "tests", "data", "cel-conformance", "*.json"))):
        with open(f, encoding="utf-8") as fp:
            exprs = [t["expr"] for t in json.load(fp)["tests"]]
        rel = os.path.relpath(f, ROOT)
        name = os.path.basename(f).split(".")[0]
        batch("conformance-parse:" + name, "CelParse", exprs, [], source=rel)
        batch("conformance-eval:" + name, "CelEval", exprs, ["", 0], source=rel)
        batch("conformance-check:" + name, "CelCheck", exprs, [], source=rel,
              lead=["check.json"], wrap="expr")
    record("reflect-schema", "ReflectSchema", inline=False)
    record("cel-functions", "CelFunctions", inline=False)
    for name, text in CEL_CHECK:
        record("cel-check:" + name, "CelCheck", name, text)
    for i, (p, t) in enumerate(REGEX):
        record("regex:%d" % i, "RegexSearch", p, t)
    # The rule loader (C4.1): every fixture in tests/data/pss-rules/, as the
    # test loads it.
    for name, text in rule_files():
        record("rule-load:" + os.path.basename(name), "RuleLoad", os.path.basename(name), text,
               1 if text.startswith("# builtin") else 0, file=name, file_arg=1)

    with open(args.output, "w", encoding="utf-8") as fp:
        json.dump({"generator": "ts/scripts/gen-lintcore-parity-fixture.py", "cases": cases,
                   "batches": batches},
                  fp, indent=1, ensure_ascii=False)
        fp.write("\n")
    print("wrote %s: %d cases, %d batches" % (os.path.relpath(args.output), len(cases),
                                               len(batches)))


if __name__ == "__main__":
    main()
