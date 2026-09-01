#!/usr/bin/env python3
"""Profile PSSParser.g4 against the shared PSS corpus.

See ``docs/design/grammar-profiling-harness.md``.

    scripts/profile_grammar.py                       # warm+cold, text report
    scripts/profile_grammar.py --mode warm --top 40
    scripts/profile_grammar.py --report md --out out/profile.md
    scripts/profile_grammar.py --baseline docs/profiling/baseline.json --fail-on-regress
    scripts/profile_grammar.py --write-baseline docs/profiling/baseline.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "python"))

from pssparser.profiling import corpus as corpus_mod          # noqa: E402
from pssparser.profiling import grammar_map                    # noqa: E402
from pssparser.profiling import report as report_mod           # noqa: E402
from pssparser.profiling.collect import collect_warm           # noqa: E402
from pssparser.profiling.collect_cold import collect_cold      # noqa: E402
from pssparser.profiling.compare import compare                # noqa: E402
from pssparser.profiling.model import CorpusProfile            # noqa: E402


def build_profile(args, mode, files, sweep_root, repo_root, lines, sha):
    if mode == "warm":
        profiles = collect_warm(files, lines, repeat=args.repeat)
        crashed = []
    else:
        def progress(path):
            if not args.quiet:
                print("  cold: %s" % path.name, file=sys.stderr)
        profiles, crashed = collect_cold(files, progress=progress)

    if crashed:
        # Never silent: a sweep that quietly covers 88 of 92 files reads as
        # though it covered all 92.
        print("WARNING: %d file(s) could not be profiled (crash or timeout):"
              % len(crashed), file=sys.stderr)
        for path in crashed:
            print("    %s" % path, file=sys.stderr)

    return CorpusProfile(
        mode=mode,
        grammar_sha=sha,
        corpus_rev=corpus_mod.corpus_rev(repo_root),
        corpus_root=str(sweep_root),
        repeat=args.repeat,
        synthetic=(args.repeat > 1),
        files=profiles)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("cold", "warm", "both"), default="both",
                    help="cold: one process per file, attributes DFA build cost. "
                         "warm: one process, steady state. Default: both.")
    ap.add_argument("--bucket", choices=("good", "bad", "all"), default="good",
                    help="which corpus bucket to sweep (default: good). "
                         "'bad' is the parses=false material.")
    ap.add_argument("--corpus", default=None, help="corpus root override")
    ap.add_argument("--grammar", default=None, help="grammar path override")
    ap.add_argument("--repeat", type=int, default=1,
                    help="warm mode only: re-parse the corpus N times for timing "
                         "signal. Marks the result synthetic.")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--report", choices=("text", "md", "json", "none"),
                    default="text")
    ap.add_argument("--out", default=None, help="write the report here")
    ap.add_argument("--json-out", default=None, help="write the raw profile here")
    ap.add_argument("--baseline", default=None, help="compare against this profile")
    ap.add_argument("--write-baseline", default=None,
                    help="write a warm good-bucket profile as the new baseline")
    ap.add_argument("--fail-on-regress", action="store_true",
                    help="exit 1 if the baseline comparison fails")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    sweep_root, repo_root, source = corpus_mod.find_corpus(args.corpus)
    if sweep_root is None:
        print("error: no PSS corpus found. Try `ivpm update`, or set "
              "PSS_CORPUS / --corpus.", file=sys.stderr)
        return 2

    grammar = grammar_map.find_grammar(args.grammar)
    lines = grammar_map.rule_lines(grammar)
    sha = grammar_map.grammar_sha(grammar)

    policy = corpus_mod.bucket_policy(repo_root)
    files = corpus_mod.corpus_files(sweep_root, policy, args.bucket)
    if not files:
        print("error: corpus at %s has no files in bucket %r"
              % (sweep_root, args.bucket), file=sys.stderr)
        return 2

    if not args.quiet:
        print("corpus: %s -- %d files, bucket %s"
              % (source, len(files), args.bucket), file=sys.stderr)

    if args.write_baseline:
        # A baseline is warm, good-bucket, unrepeated, by construction -- not
        # by asking the caller to remember to pass the right flags.
        if args.bucket != "good" or args.repeat != 1:
            print("error: a baseline must be --bucket good --repeat 1",
                  file=sys.stderr)
            return 2
        profile = build_profile(args, "warm", files, sweep_root, repo_root, lines, sha)
        path = Path(args.write_baseline)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(profile.compacted().to_json(), encoding="utf-8")
        print("wrote baseline: %s (grammar %s, corpus %s)"
              % (path, profile.grammar_sha, profile.corpus_rev))
        return 0

    modes = ["warm", "cold"] if args.mode == "both" else [args.mode]
    profiles = {}
    for mode in modes:
        if mode == "cold" and args.repeat > 1:
            print("note: --repeat applies to warm mode only; ignored for cold",
                  file=sys.stderr)
        profiles[mode] = build_profile(
            args, mode, files, sweep_root, repo_root, lines, sha)

    chunks = []
    for mode in modes:
        profile = profiles[mode]
        if args.report == "text":
            chunks.append(report_mod.text_report(profile, args.top))
        elif args.report == "md":
            chunks.append(report_mod.markdown_report(profile, args.top))
        elif args.report == "json":
            chunks.append(profile.to_json())

    text = "\n\n".join(chunks)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print("wrote %s" % args.out, file=sys.stderr)
    elif args.report != "none":
        print(text)

    if args.json_out:
        # Warm is the profile worth keeping: it is what a baseline is made of.
        keep = profiles.get("warm", profiles[modes[0]])
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(keep.to_json(), encoding="utf-8")
        print("wrote %s" % args.json_out, file=sys.stderr)

    rc = 0
    if args.baseline:
        base = CorpusProfile.from_json(
            Path(args.baseline).read_text(encoding="utf-8"))
        current = profiles.get("warm")
        if current is None:
            print("error: --baseline needs a warm run", file=sys.stderr)
            return 2
        result = compare(base, current)
        print("")
        print("Baseline comparison")
        print("-" * 72)
        print(result.describe())
        if result.failed:
            print("")
            print("REGRESSION")
            if args.fail_on_regress:
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
