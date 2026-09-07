#!/usr/bin/env python3
"""Time the native parser over the corpus, for comparison with wasm/spike.mjs.

    PYTHONPATH=python packages/python/bin/python wasm/bench-native.py

The two harnesses must do the same work or the ratio means nothing:

  * one Parser per file, so neither side amortises the standard-library load
    across the corpus;
  * the stdlib load timed separately, because it is paid once per Parser and
    folding it into a per-file average overstates every file;
  * the same files, in the same order.

The native side is reached through the Python bindings rather than through C++
directly.  That adds a Cython call per parse -- one call, for a parse that
takes milliseconds -- and it is the comparison that matters anyway: the Python
bindings are the shipping native consumer, so "3x native" means 3x what a
pssparser user gets today.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python"))

from pssparser.parser import Parser  # noqa: E402


def collect(corpus_dir):
    out = []
    for dirpath, _, filenames in os.walk(corpus_dir):
        for fn in sorted(filenames):
            if fn.endswith(".pss"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    corpus_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        root, "packages", "pss-corpus", "curated")

    paths = collect(corpus_dir)
    if not paths:
        raise SystemExit("no .pss files under %s" % corpus_dir)

    sources = []
    for p in paths:
        with open(p, "r", encoding="utf-8", errors="replace") as fp:
            sources.append((os.path.relpath(p, corpus_dir), fp.read()))

    total_bytes = sum(len(c) for _, c in sources)
    results = []
    stdlib_times = []

    for name, content in sources:
        parser = Parser()

        # Force the stdlib load on its own, by parsing an empty source. The
        # first real parse would otherwise carry it and there would be no way
        # to separate the two.
        t = time.perf_counter()
        try:
            parser.parses([("<warmup>", "")])
        except Exception:
            pass
        stdlib_times.append((time.perf_counter() - t) * 1000.0)

        t = time.perf_counter()
        failed = False
        try:
            parser.parses([(name, content)])
        except Exception:
            failed = True
        ms = (time.perf_counter() - t) * 1000.0

        results.append({"name": name, "ms": ms, "failed": failed,
                        "bytes": len(content), "markers": len(parser.markers)})

    total_ms = sum(r["ms"] for r in results)
    slowest = max(results, key=lambda r: r["ms"])
    stdlib_avg = sum(stdlib_times) / len(stdlib_times)

    print("corpus             : %d files, %d bytes" % (len(results), total_bytes))
    print("  parsed ok        : %d/%d" % (sum(1 for r in results if not r["failed"]), len(results)))
    print("  stdlib load (avg): %.1f ms  <- paid once per Parser" % stdlib_avg)
    print("  parse total      : %.1f ms" % total_ms)
    print("  throughput       : %.0f KiB/s" % (total_bytes / 1024 / (total_ms / 1000)))
    print("  slowest file     : %s %.1f ms (%d bytes)" % (
        os.path.basename(slowest["name"]), slowest["ms"], slowest["bytes"]))

    if os.environ.get("BENCH_JSON"):
        with open(os.environ["BENCH_JSON"], "w") as fp:
            json.dump(results, fp, indent=2)
        print("  wrote            : %s" % os.environ["BENCH_JSON"])


if __name__ == "__main__":
    main()
