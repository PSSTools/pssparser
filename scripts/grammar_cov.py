#!/usr/bin/env python3
"""Grammar coverage: which parser rules the legal corpus never uses.

Every file in the legal corpus is parsed with profiling on, and the parse
tree's rule contexts are counted per rule (``ParseProfileInfo.
get_rule_invocations``). A rule with **zero** contexts is grammar no corpus
file exercises, and that list drives corpus build-out
(docs/design/symbol-resolution-plan.md §3, §7, WS0.7).

Why rules and not ANTLR decisions, which the profiling harness already
records: a decision is counted only when it goes through adaptive prediction.
An LL(1) decision is resolved by a generated ``switch`` on the next token and
reports zero invocations whether or not the input used it -- on the current
corpus only about 70 of 337 decisions ever register, including none in
``component_declaration``.

Usage::

    PYTHONPATH=python python3 scripts/grammar_cov.py report
    PYTHONPATH=python python3 scripts/grammar_cov.py baseline   # docs/coverage/grammar.json

Not a gate yet: the plan makes it one once the corpus has closed the obvious
holes. Regenerate the baseline after a grammar change or a corpus addition.

Limitation: the alternatives *within* a rule are not counted separately, so
a rule used through one alternative counts as covered.
"""
import argparse
import collections
import json
import sys
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "coverage" / "grammar.json"

sys.path.insert(0, str(ROOT / "scripts"))
from refcov import corpus_files  # noqa: E402  (same legal corpus)


def compute(files=None):
    import pssparser.core as zspp
    import pssparser.ast as zsp_ast
    from pssparser.profiling.grammar_map import find_grammar, grammar_sha, rule_lines

    grammar = find_grammar()
    lines = rule_lines(grammar)
    files = corpus_files() if files is None else files

    ast_f = zsp_ast.Factory.inst()
    parser_f = zspp.Factory.inst()

    counts = collections.Counter()
    names = set()
    parsed = 0
    for i, fn in enumerate(files):
        marker_l = parser_f.mkMarkerCollector()
        builder = parser_f.mkAstBuilder(marker_l)
        builder.setEnableProfile(True)
        scope = ast_f.mkGlobalScope(i)
        builder.build(scope, StringIO(Path(fn).read_text(errors="replace")))
        if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
            continue
        parsed += 1
        for rule, n in builder.getProfileInfo().get_rule_invocations().items():
            names.add(rule)
            counts[rule] += n

    rules = {r: counts[r] for r in sorted(names)}
    unused = [{"rule": r, "grammar_line": lines.get(r, 0)}
              for r in sorted(names, key=lambda r: lines.get(r, 0)) if not counts[r]]
    return {
        "grammar_sha": grammar_sha(grammar),
        "files": len(files),
        "parsed_files": parsed,
        "rules": len(rules),
        "rules_used": sum(1 for v in rules.values() if v),
        "unused_rules": unused,
        "rule_counts": rules,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["report", "baseline"])
    args = ap.parse_args(argv)
    data = compute()
    if args.cmd == "baseline":
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(data, indent=1) + "\n")
        print("wrote %s" % BASELINE.relative_to(ROOT))
    print("%d/%d parser rules used by %d corpus files (%d parsed)" % (
        data["rules_used"], data["rules"], data["files"], data["parsed_files"]))
    print("rules no corpus file uses (%d):" % len(data["unused_rules"]))
    for u in data["unused_rules"]:
        print("  src/PSSParser.g4:%-5d %s" % (u["grammar_line"], u["rule"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
