#!/usr/bin/env python3
"""Lint cost against parse + link (lint-core-plan.md C8, framework plan F3.8).

The budget (L8): running the ``recommended`` rules costs at most 50 % of
parse + link, and one rule at most 5 %. This script measures both, natively
(the CLI's ``--stats``) and in the WebAssembly build
(``ts/scripts/bench-lint.mjs``, which needs ``npm run build`` in ``ts/``).

The corpus has no single model large enough to time: its biggest file is
6 KB, and a bucket is a set of separate models. So the model is generated:
``--units N`` packages of components, actions, activities, constraints and
exec code, each importing the one before, all linking cleanly. The rules
are the built-in ones (``rules/*.yaml``, compiled into the core) and the
given files; by default every ``tests/data/lint-examples/*.yaml``, which use
every library function. The profile is ``all``; ``--select`` adds
selectors on top of it, as the CLI's does: ``--rules --select nursery``
times the built-in rules alone while they are all in the nursery tier.

Usage::

    PYTHONPATH=python python3 scripts/bench_lint.py [--units N] [--repeat R]
        [--rules FILE ...] [--select SEL ...] [--wasm] [--json OUT]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UNIT = """\
package p{i}_pkg {{
{imp}
    enum mode{i}_e {{ M{i}_IDLE, M{i}_RUN, M{i}_STOP, M{i}_FAIL }};

    struct cfg{i}_s {{
        rand bit[8]  depth;
        rand bit[32] base;
        rand mode{i}_e mode;
        constraint {{ depth > 0; depth <= 64; base < 32'h1000_0000; }}
    }}

    buffer buf{i}_b {{
        rand bit[32] addr;
        rand bit[16] size;
        constraint {{ size > 0; addr + size < 32'hFFFF_0000; }}
    }}

    function bit[32] align{i}(bit[32] v, bit[8] a) {{
        if (a == 0) {{ return v; }}
        return (v / a) * a;
    }}

    function int fact{i}(int n) {{
        if (n <= 1) {{ return 1; }}
        return n * fact{i}(n - 1);
    }}

    component unit{i}_c {{
        cfg{i}_s cfg;
        int counter;
        int unused_{i};
        pool buf{i}_b buf_p;
        bind buf_p *;

        exec init_down {{
            counter = 0;
            cfg.depth = 4;
        }}

        action produce{i}_a {{
            output buf{i}_b out_b;
            rand bit[4] kind;
            rand mode{i}_e mode;
            rand int lonely;
            constraint {{ kind < 12; out_b.size == 16 * (kind + 1); }}
            constraint c_mode {{
                if (kind > 8) {{ mode == M{i}_RUN; }} else {{ mode != M{i}_FAIL; }}
            }}
            exec post_solve {{
                bit[32] a;
                a = align{i}(out_b.addr, 4);
                match (kind) {{
                    [0..3]: comp.counter += 1;
                    [4..7]: comp.counter += 2;
                    [8]:    comp.counter = fact{i}(3);
                    default: comp.counter = comp.counter;
                }}
                repeat (2) {{ a = a + 1; }}
            }}
        }}

        action consume{i}_a {{
            input buf{i}_b in_b;
            rand bit[8] weight;
            constraint {{ weight in [1..10]; weight != 0; }}
        }}

        action flow{i}_a {{
            rand bit[4] sel;
            rand int n;
            constraint {{ n in [1..4]; sel < 3; }}
            produce{i}_a p;
            consume{i}_a c;
            activity {{
                p;
                c;
                select {{
                    (sel == 0): do produce{i}_a;
                    (sel == 1): do consume{i}_a;
                    [2]: do produce{i}_a;
                }}
                match (sel) {{
                    [0]: do produce{i}_a;
                    [1..2]: do consume{i}_a;
                    default: do produce{i}_a;
                }}
                parallel {{
                    do produce{i}_a;
                    do consume{i}_a;
                }}
                repeat (n) {{
                    do produce{i}_a;
                }}
                if (sel > 1) {{ do produce{i}_a; }} else {{ do consume{i}_a; }}
            }}
        }}
    }}
}}
"""

TOP = """\
{imports}
component pss_top {{
{fields}
    action entry_a {{
        activity {{
{body}
        }}
    }}
}}
"""


def generate(out_dir: str, units: int) -> list:
    """Write ``units`` package files and a top; return the paths in order."""
    paths = []
    for i in range(units):
        imp = f"    import p{i - 1}_pkg::*;" if i else ""
        p = os.path.join(out_dir, f"unit{i}.pss")
        with open(p, "w") as f:
            f.write(UNIT.format(i=i, imp=imp))
        paths.append(p)
    top = os.path.join(out_dir, "top.pss")
    with open(top, "w") as f:
        f.write(TOP.format(
            imports="\n".join(f"import p{i}_pkg::*;" for i in range(units)),
            fields="\n".join(f"    unit{i}_c u{i};" for i in range(units)),
            body="\n".join(f"            do unit{i}_c::flow{i}_a;" for i in range(units))))
    paths.append(top)
    return paths


def default_rules() -> list:
    return sorted(glob.glob(os.path.join(ROOT, "tests", "data", "lint-examples", "*.yaml")))


def _native_once(paths, rules, select=()):
    env = dict(os.environ)
    env.pop("PSSPARSER_NO_LINT", None)
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    argv = [sys.executable, "-m", "pssparser", "--no-config", "--stats", "--format", "json",
            "--lint-profile", "all"]
    for r in rules:
        argv += ["--rules", r]
    for sel in select:
        argv += ["--select", sel]
    cp = subprocess.run(argv + paths, capture_output=True, text=True, env=env)
    if cp.returncode not in (0, 1):
        raise SystemExit(f"pssparser failed ({cp.returncode}):\n{cp.stderr}\n{cp.stdout[:2000]}")
    return json.loads(cp.stdout)


def _summarise(runs):
    """The fastest time (ms) over runs, and each rule's fastest.

    A run is ``{"parse", "link", "lint", "index": ms, "rules": [{id, ms,
    steps, findings}]}``; ``index`` is the part of ``lint`` spent building
    indexes, in no rule's time."""
    # The minimum: other load only ever adds time.
    med = min
    out = {k + "_ms": med([r[k] for r in runs]) for k in ("parse", "link", "lint", "index")}
    per = {}
    for r in runs:
        for s in r["rules"]:
            e = per.setdefault(s["id"], {"ms": [], "steps": s["steps"], "findings": s["findings"]})
            e["ms"].append(s["ms"])
    out["rules"] = {k: dict(v, ms=med(v["ms"])) for k, v in per.items()}
    return out


def native(paths, rules, repeat, select=()):
    runs = []
    for _ in range(repeat):
        st = _native_once(paths, rules, select)["stats"]
        t = st["timing_ms"]
        runs.append({"parse": t["parse (incl. read)"], "link": t["link"],
                     "lint": t.get("lint", 0.0), "index": st.get("lint_index_ms", 0.0),
                     "rules": st.get("lint_rules", [])})
    res = _summarise(runs)
    res["diagnostics"] = st["diagnostics_by_code"]
    return res


def wasm(paths, rules, repeat, select=()):
    script = os.path.join(ROOT, "ts", "scripts", "bench-lint.mjs")
    cp = subprocess.run(["node", script, "--repeat", str(repeat), "--rules", *rules,
                         "--select", *select, "--", *paths], capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(f"bench-lint.mjs failed:\n{cp.stderr}")
    runs = json.loads(cp.stdout)
    return _summarise(runs)


def report(name, res):
    pl = res["parse_ms"] + res["link_ms"]
    print(f"{name}: parse {res['parse_ms']:.1f} ms, link {res['link_ms']:.1f} ms, "
          f"lint {res['lint_ms']:.1f} ms = {100 * res['lint_ms'] / pl:.1f} % of parse+link"
          f" (budget 50 %); of which indexes {res['index_ms']:.1f} ms, rules "
          f"{sum(r['ms'] for r in res['rules'].values()):.1f} ms")
    worst = sorted(res["rules"].items(), key=lambda kv: -kv[1]["ms"])
    for rid, r in worst:
        flag = "  OVER" if r["ms"] > 0.05 * pl else ""
        print(f"  {rid:<14} {r['ms']:8.2f} ms {100 * r['ms'] / pl:6.2f} %  "
              f"{r['steps']:>9} steps {r['findings']:>5} findings{flag}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--units", type=int, default=40)
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--rules", nargs="*", default=None)
    ap.add_argument("--select", nargs="*", default=[],
                    help="rule selectors to add to the 'all' profile (e.g. nursery)")
    ap.add_argument("--wasm", action="store_true", help="also measure the WebAssembly build")
    ap.add_argument("--keep", metavar="DIR", help="write the model here and keep it")
    ap.add_argument("--json", metavar="OUT", help="write the results as JSON")
    a = ap.parse_args(argv)
    rules = a.rules if a.rules is not None else default_rules()
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = a.keep or tmp
        os.makedirs(out_dir, exist_ok=True)
        paths = generate(out_dir, a.units)
        size = sum(os.path.getsize(p) for p in paths)
        print(f"model: {a.units} units, {len(paths)} files, {size // 1024} KB; "
              f"{len(rules)} rule files")
        results = {"units": a.units, "bytes": size,
                   "rules": [os.path.relpath(r, ROOT) for r in rules], "select": a.select}
        results["native"] = native(paths, rules, a.repeat, a.select)
        report("native", results["native"])
        if a.wasm:
            results["wasm"] = wasm(paths, rules, a.repeat, a.select)
            report("wasm", results["wasm"])
    if a.json:
        with open(a.json, "w") as f:
            json.dump(results, f, indent=1, sort_keys=True)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
