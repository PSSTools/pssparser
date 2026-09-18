"""`pss-errsuite …` (design §8).

`run` is a *measurement*, not a gate: it exits 0 even when the tool under test
missed every case, because the output is the finding.  `validate` is the
opposite -- it exits non-zero on any corpus defect, because a malformed case
makes every number downstream of it wrong.
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
import time
from pathlib import Path

from . import compare as compare_mod
from . import digest as digest_mod
from . import report
from . import rubric
from .adapters import make_adapter
from .case import CaseFormatError, collect_cases
from .classify import SKIPPED, SKIPPED_VERSION, TOOL_ERROR
from .descriptor import DescriptorError, load_descriptor
from .locate import Tolerance
from .runner import Runner, version_tuple
from .taxonomy import PSS_VERSIONS
from .validate import validate_corpus

SUITE_ROOT = Path(__file__).resolve().parent.parent


def _default_cases() -> Path:
    local = Path.cwd() / "cases"
    return local if local.is_dir() else SUITE_ROOT / "cases"


def _select(cases, class_filter: str | None, case_id: str | None):
    out = cases
    if class_filter:
        out = [c for c in out if fnmatch.fnmatch(c.cls, class_filter)
               or c.cls.startswith(class_filter + ".")
               or c.cls == class_filter]
    if case_id:
        out = [c for c in out if c.case_id == case_id]
    return out


# -- run ---------------------------------------------------------------------

def cmd_run(args) -> int:
    try:
        desc = load_descriptor(Path(args.tool), SUITE_ROOT)
    except DescriptorError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    try:
        cases = collect_cases(Path(args.cases))
    except CaseFormatError as e:
        print(f"error: {e}", file=sys.stderr)
        print("hint: run `pss-errsuite validate` for the full list",
              file=sys.stderr)
        return 2
    cases = _select(cases, args.filter, args.case)
    if not cases:
        print("error: no cases selected", file=sys.stderr)
        return 2

    warnings = []
    tool_pss = desc.pss
    if tool_pss is None:
        # Assume the newest version the corpus contains: an undeclared version
        # fails loudly in the tool's disfavour (every 3.1 case runs and can be
        # missed) rather than silently inflating its score by skipping them.
        tool_pss = max(
            [c.pss for c in cases] + [PSS_VERSIONS[-1]], key=version_tuple)
        warnings.append(
            f"{desc.path.name} declares no [tool] pss; assuming {tool_pss}, "
            f"the newest version in the corpus. Every headline number below "
            f"should be read with that in mind.")

    adapter = make_adapter(desc)
    version = adapter.probe_version()

    tolerance = Tolerance(args.tolerance)
    jobs = args.jobs
    if desc.adapter != "subprocess" and jobs != 1:
        warnings.append("in-process adapter forces -j1")
        jobs = 1

    runner = Runner(adapter, desc, tolerance=tolerance,
                    severity_floor=args.severity_floor, jobs=jobs,
                    timeout_s=args.timeout, tool_pss=tool_pss,
                    scratch_root=Path(args.scratch) if args.scratch else None,
                    verify_fixit=not args.no_verify_fixit)
    started = report._utc_now()
    t0 = time.perf_counter()
    try:
        runs = runner.run_all(cases, progress=_progress(args))
    finally:
        if not args.keep_scratch:
            runner.cleanup()
    duration = time.perf_counter() - t0

    doc = report.build_document(
        runs, desc=desc, adapter=adapter, tolerance=tolerance,
        severity_floor=args.severity_floor, suite_root=SUITE_ROOT,
        started=started, duration_s=duration,
        include_source=not args.no_source, tool_pss=tool_pss,
        pss_assumed=desc.pss is None, warnings=warnings)
    # A run in which the tool could not be invoked is not a measurement of the
    # tool, and writing it to `--out` replaces a good run file with one whose
    # every headline reads `n/a`.  Refuse rather than clobber.  (This is not
    # hypothetical: a descriptor whose argv is a bare `pssparser` not on PATH
    # produces exactly this, and the summary's `tool_error=167` is easy to
    # read past.)
    failed = doc["summary"]["by_status"].get(TOOL_ERROR, 0)
    total = len(doc["cases"])
    if total and failed * 2 >= total and not args.force:
        print(f"error: the tool could not be run on {failed} of {total} "
              f"cases; this is a broken invocation, not a result",
              file=sys.stderr)
        print(f"hint: check [invoke] argv in {desc.path.name} "
              f"(version probe said {version!r}); "
              f"pass --force to write the run file anyway", file=sys.stderr)
        return 2

    report.write(doc, Path(args.out) if args.out else None)

    _print_summary(doc, version, args)
    return 0


def _progress(args):
    if args.quiet or not sys.stderr.isatty():
        return None

    def show(run):
        sys.stderr.write(f"  {run.status:<24} {run.case.case_id}\n")
    return show


def _print_summary(doc: dict, version: str, args) -> None:
    out = sys.stderr if args.out is None else sys.stdout
    s = doc["summary"]
    by = s["by_status"]
    m = s["metrics"]
    tool = doc["tool"]
    for w in doc["run"]["warnings"]:
        print(f"warning: {w}", file=out)
    print(f"{tool['name']} {version} (PSS {tool['pss']}"
          f"{', assumed' if tool['pss_assumed'] else ''}, "
          f"{tool['parse_confidence']} output) over "
          f"{doc['run']['suite']['case_count']} cases "
          f"in {doc['run']['duration_s']}s", file=out)
    line = ", ".join(f"{k}={v}" for k, v in by.items() if v)
    print(f"  {line}", file=out)
    print(f"  detection {_pct(m['detection_rate'])} "
          f"(n={m['detection_denominator']}, detect:required only), "
          f"localization {_pct(m['localization_rate'])} "
          f"(n={m['localization_denominator']}), "
          f"false positives {_pct(m['false_positive_rate'])} "
          f"(n={m['false_positive_denominator']})", file=out)
    print(f"  skipped {by.get(SKIPPED, 0)} (capability) + "
          f"{by.get(SKIPPED_VERSION, 0)} (version); "
          f"crash/timeout {m['robustness']}", file=out)
    if args.out:
        print(f"  wrote {args.out}", file=out)


def _pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


# -- list --------------------------------------------------------------------

def cmd_list(args) -> int:
    cases = _select(collect_cases(Path(args.cases)), args.filter, None)
    if args.detect:
        cases = [c for c in cases if c.detect == args.detect]
    if args.lrm:
        cases = [c for c in cases if c.lrm and fnmatch.fnmatch(c.lrm, args.lrm)]
    for c in cases:
        print(f"{c.case_id:<32} {c.cls:<34} {c.expect:<7} {c.detect:<12} "
              f"{c.title}")
    print(f"{len(cases)} case(s)", file=sys.stderr)
    return 0


# -- validate ----------------------------------------------------------------

def cmd_validate(args) -> int:
    findings = validate_corpus(Path(args.cases))
    errors = [f for f in findings if f.severity == "error"]
    for f in findings:
        print(str(f), file=sys.stderr if f.severity == "error" else sys.stdout)
    n = len(list(collect_cases_safely(Path(args.cases))))
    print(f"{n} case(s), {len(errors)} error(s), "
          f"{len(findings) - len(errors)} warning(s)", file=sys.stderr)
    return 1 if errors else 0


def collect_cases_safely(root: Path):
    try:
        return collect_cases(root)
    except CaseFormatError:
        return []


# -- compare -----------------------------------------------------------------

def cmd_compare(args) -> int:
    try:
        runs = [compare_mod.load_run(Path(p)) for p in args.runs]
        doc = compare_mod.compare_runs(runs)
    except compare_mod.CompareError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.out:
        report.write(doc, Path(args.out))
    if args.md:
        text = compare_mod.render_markdown(
            doc, source_of=compare_mod.source_lookup([r.doc for r in runs]))
        path = Path(args.md)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if not args.out and not args.md:
        report.write(doc, None)

    _print_compare_summary(doc, args)
    return 0


def _print_compare_summary(doc: dict, args) -> None:
    out = sys.stderr if not (args.out or args.md) else sys.stdout
    meta = doc["compare"]
    for w in meta["warnings"]:
        print(f"warning: {w}", file=out)
    print(f"{meta['shared_case_count']} shared case(s), baseline "
          f"{meta['baseline']}", file=out)
    for label, counts in doc["summary"]["by_tag"].items():
        line = ", ".join(f"{t}={counts[t]}" for t in compare_mod.ALL_TAGS
                         if counts.get(t))
        print(f"  vs {label}: {line}", file=out)
    for name in ("out", "md"):
        if getattr(args, name):
            print(f"  wrote {getattr(args, name)}", file=out)


# -- show --------------------------------------------------------------------

def cmd_show(args) -> int:
    """One case, verbose -- the header, the source, and what a tool said.

    With `--run` it reads a run file (no tool invoked, so it works on a machine
    that cannot build the tool); with `--tool` it runs that one case live.
    """
    try:
        cases = collect_cases(Path(args.cases))
    except CaseFormatError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    found = [c for c in cases if c.case_id == args.case]
    if not found:
        print(f"error: no case with id {args.case!r} under {args.cases}",
              file=sys.stderr)
        return 2
    case = found[0]

    print(f"{case.case_id}  [{case.cls}]")
    print(f"  {case.title}")
    print(f"  expect: {case.expect}   detect: {case.detect}"
          + (f"   lrm: {case.lrm}" if case.lrm else ""))
    if case.at is not None:
        print(f"  at: {case.at.line}:{case.at.col}"
              + (f" ({case.at_file})" if case.at_file else ""))
    print(f"  file: {case.path}")
    print()
    for i, line in enumerate(case.source.rstrip("\n").splitlines(), 1):
        marker = ">" if case.at is not None and i == case.at.line else " "
        print(f"{marker}{i:>4} | {line}")
    print()

    if args.run:
        return _show_from_run(case, Path(args.run))
    if args.tool:
        return _show_from_tool(case, args)
    return 0


def _show_from_run(case, path: Path) -> int:
    try:
        run = compare_mod.load_run(path)
    except compare_mod.CompareError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    doc = run.cases.get(case.case_id)
    if doc is None:
        print(f"error: {path.name} has no entry for {case.case_id}",
              file=sys.stderr)
        return 2
    print(f"{run.tool.get('name')} {run.tool.get('version')}: {doc['status']}")
    _print_diagnostics((doc.get("result") or {}).get("diagnostics") or [],
                       (doc.get("observations") or {}).get("primary_index"))
    return 0


def _show_from_tool(case, args) -> int:
    try:
        desc = load_descriptor(Path(args.tool), SUITE_ROOT)
    except DescriptorError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    runner = Runner(make_adapter(desc), desc, tolerance=Tolerance(args.tolerance),
                    severity_floor=args.severity_floor)
    try:
        run = runner.run_case(case)
    finally:
        runner.cleanup()
    print(f"{desc.name}: {run.status}"
          + (f" ({run.skip_reason})" if run.skip_reason else ""))
    if run.control_status:
        print(f"  control: {run.control_status} "
              f"({run.control_error_count} error(s))")
    if run.result is not None:
        _print_diagnostics([d.as_dict() for d in run.result.diagnostics],
                           run.observations.primary_index)
    return 0


def _print_diagnostics(diags: list[dict], primary_index) -> None:
    if not diags:
        print("  (no diagnostics)")
        return
    for i, d in enumerate(diags):
        mark = "*" if i == primary_index else " "
        where = ""
        if d.get("line") is not None:
            where = f"{d.get('file') or '?'}:{d['line']}:{d.get('col', '?')}: "
        code = f"[{d['code']}] " if d.get("code") else ""
        print(f" {mark} {where}{d['severity']}: {code}{d['message']}")


# -- digest ------------------------------------------------------------------

def cmd_digest(args) -> int:
    """The run file reduced to case + reported error, for a human to read."""
    doc = _load_run_document(Path(args.run))
    if doc is None:
        return 2
    small = digest_mod.build(doc)
    report.write(small, Path(args.out) if args.out else None)
    if args.out:
        print(f"{len(small['cases'])} case(s) -> {args.out}", file=sys.stderr)
    return 0


# -- grade -------------------------------------------------------------------

def _load_run_document(path: Path) -> dict | None:
    try:
        return compare_mod.load_run(path).doc
    except compare_mod.CompareError as e:
        print(f"error: {e}", file=sys.stderr)
        return None


def cmd_grade(args) -> int:
    """Re-score a run file. No tool is invoked: the run file already carries
    the source, the expectation and the verbatim diagnostics."""
    path = Path(args.run)
    doc = _load_run_document(path)
    if doc is None:
        return 2

    cache = rubric.RubricCache(Path(args.cache))
    rubric.regrade(doc, cache=cache)

    if args.tier == "b":
        if not args.rater:
            print("error: --tier b needs --rater NAME; a human score with no "
                  "name attached cannot be argued with later", file=sys.stderr)
            return 2
        graded = _walk_tier_b(doc, cache, args)
        cache.save()
        rubric.regrade(doc, cache=cache)
        print(f"scored {graded} case(s) by hand; cache at {args.cache}",
              file=sys.stderr)

    report.write(doc, Path(args.out) if args.out else path)
    _print_rubric_summary(doc, args)
    return 0


def _walk_tier_b(doc: dict, cache, args) -> int:
    """Interactive Tier-B pass over design §5.3's sample."""
    version = (doc.get("tool") or {}).get("version") or ""
    by_id = {c["case"]: c for c in doc.get("cases") or []}
    sample = rubric.tier_b_sample(doc.get("cases") or [])
    if args.limit:
        sample = sample[:args.limit]
    scored = 0
    for i, case_id in enumerate(sample, 1):
        case = by_id[case_id]
        key = rubric.fingerprint(case, version)
        if cache.get(key) and not args.regrade:
            continue
        print(f"\n[{i}/{len(sample)}] {case_id}  [{case['class']}]")
        print(f"  {case['title']}")
        primary = rubric.primary_diagnostic(case)
        if primary is not None:
            print(f"  message: {primary.get('message')}")
        print(f"  Tier A: " + ", ".join(
            f"{d}={case['rubric'][d]}" for d in rubric.DIMENSIONS))
        for key_, note in (case["rubric"].get("notes") or {}).items():
            print(f"    {key_}: {note}")
        entry = {"rater": args.rater, "case": case_id}
        try:
            for dim in rubric.DIMENSIONS:
                raw = input(f"  {dim} ({rubric.DIMENSION_NAMES[dim]}) 0-3, "
                            f"blank to keep Tier A, q to stop: ").strip()
                if raw.lower() == "q":
                    return scored
                if raw:
                    entry[dim] = max(0, min(3, int(raw)))
        except (EOFError, KeyboardInterrupt):
            print()
            return scored
        except ValueError:
            print("  not a number; skipping this case")
            continue
        if any(d in entry for d in rubric.DIMENSIONS):
            cache.put(key, entry)
            scored += 1
    return scored


def _print_rubric_summary(doc: dict, args) -> None:
    out = sys.stderr if not args.out else sys.stdout
    roll = doc["summary"]["rubric"]
    cov = roll["coverage"]
    print(f"rubric v{roll['version']}: {roll['graded']} of "
          f"{roll['gradeable']} gradeable case(s) scored "
          f"(tier A {roll['tier']['A']}, tier B {roll['tier']['B']})",
          file=out)
    dims = ", ".join(
        f"{d}={_num(roll['dimensions'][d]['mean'])}"
        f"[{roll['dimensions'][d]['measured']}]" for d in rubric.DIMENSIONS)
    print(f"  means {dims}   (n measured in brackets)", file=out)
    print(f"  metadata: cause {cov['cause']}/{cov['gradeable']}, "
          f"names {cov['names']}/{cov['gradeable']}, "
          f"not_cause {cov['not_cause']}/{cov['gradeable']}", file=out)
    if roll["flags"]:
        print("  flags: " + ", ".join(f"{k}={v}"
                                      for k, v in sorted(roll["flags"].items())),
              file=out)
    worst = sorted((v["mean"], k) for k, v in roll["by_class"].items()
                   if v["mean"] is not None)[:3]
    if worst:
        print("  weakest classes: " + ", ".join(f"{k} {_num(m)}"
                                                for m, k in worst), file=out)


def _num(value) -> str:
    return "n/a" if value is None else f"{value:.2f}"


# -- triage ------------------------------------------------------------------

def cmd_triage(args) -> int:
    """The day-to-day command: the work queue, worst first.

    Sorted ascending by D1 then D4 -- a `detected` case whose message is about
    the wrong thing outranks a missing fix-it, because accuracy is the only
    dimension that can zero a composite on its own.
    """
    doc = _load_run_document(Path(args.run))
    if doc is None:
        return 2
    cases = doc.get("cases") or []

    if args.missing:
        ids = rubric.cases_missing_metadata(cases, args.missing)
        for case_id in ids:
            case = next(c for c in cases if c["case"] == case_id)
            print(f"{case_id:<40} {case['class']:<28} {case['title']}")
        print(f"{len(ids)} gradeable case(s) with no `{args.missing}:`; until "
              f"they have one, {'D1' if args.missing != 'names' else 'D3'} is "
              f"unmeasured for them, not bad", file=sys.stderr)
        return 0

    graded = [c for c in cases if c.get("rubric")]
    if args.filter:
        graded = [c for c in graded
                  if fnmatch.fnmatch(c["class"], args.filter)
                  or c["class"].startswith(args.filter + ".")]
    if args.flag:
        graded = [c for c in graded
                  if args.flag in (c["rubric"].get("flags") or ())]

    def key(case):
        block = case["rubric"]
        # `None` sorts after every score: an unmeasured dimension is not a
        # finding, so it must not head a queue of real ones.
        return tuple(4 if block[d] is None else block[d] for d in ("d1", "d4"))

    graded.sort(key=key)
    if args.limit:
        graded = graded[:args.limit]

    for case in graded:
        block = case["rubric"]
        scores = "".join("-" if block[d] is None else str(block[d])
                         for d in rubric.DIMENSIONS)
        print(f"{_num(block['composite']):>5}  {scores}  {case['case']:<40} "
              f"{case['class']}")
        if args.notes:
            for dim, note in (block.get("notes") or {}).items():
                print(f"         {dim}: {note}")
            for flag in block.get("flags") or ():
                print(f"         ! {flag}")
    print(f"{len(graded)} case(s), worst first (D1 then D4); "
          f"columns are d1..d6, '-' is unmeasured", file=sys.stderr)
    return 0


# -- argument parsing --------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog="pss-errsuite",
        description="Run a tool-neutral PSS error corpus against any tool")
    sub = top.add_subparsers(dest="command", required=True)

    def add_cases(p):
        p.add_argument("--cases", default=str(_default_cases()),
                       metavar="DIR", help="corpus root")

    run = sub.add_parser("run", help="run the corpus against one tool")
    add_cases(run)
    run.add_argument("--tool", required=True, metavar="TOML",
                     help="tool descriptor")
    run.add_argument("--filter", default=None, metavar="CLASS",
                     help="only cases whose class matches (glob or prefix)")
    run.add_argument("--case", default=None, metavar="ID",
                     help="only this case id")
    run.add_argument("-j", "--jobs", type=int, default=1, metavar="N")
    run.add_argument("--tolerance", default="token:2",
                     help="exact | line | token:N (default token:2)")
    run.add_argument("--timeout", type=float, default=None, metavar="SECONDS")
    run.add_argument("--severity-floor", default="error",
                     choices=("error", "warning", "note"))
    run.add_argument("--out", default=None, metavar="JSON",
                     help="write the run file here (default: stdout)")
    run.add_argument("--no-source", action="store_true",
                     help="omit case sources from the run file")
    run.add_argument("--scratch", default=None, metavar="DIR",
                     help="scratch root (default: a temporary directory)")
    run.add_argument("--keep-scratch", action="store_true")
    run.add_argument("--force", action="store_true",
                     help="write the run file even if the tool could not be "
                          "invoked on most cases")
    run.add_argument("--no-verify-fixit", action="store_true",
                     help="skip applying each fix-it and re-running the tool "
                          "(costs one extra invocation per fix-it offered)")
    run.add_argument("-q", "--quiet", action="store_true")
    run.set_defaults(func=cmd_run)

    lst = sub.add_parser("list", help="list corpus cases")
    add_cases(lst)
    lst.add_argument("--filter", default=None, metavar="CLASS")
    lst.add_argument("--detect", default=None,
                     choices=("required", "recommended", "optional"))
    lst.add_argument("--lrm", default=None, metavar="GLOB")
    lst.set_defaults(func=cmd_list)

    val = sub.add_parser("validate", help="lint the corpus itself")
    add_cases(val)
    val.set_defaults(func=cmd_validate)

    cmp_ = sub.add_parser("compare", help="join two or more run files")
    cmp_.add_argument("runs", nargs="+", metavar="RUN.json",
                      help="run files; the first is the baseline ('we')")
    cmp_.add_argument("--out", default=None, metavar="JSON")
    cmp_.add_argument("--md", default=None, metavar="MARKDOWN",
                      help="also render the human report (internal only)")
    cmp_.set_defaults(func=cmd_compare)

    show = sub.add_parser("show", help="one case, verbose")
    add_cases(show)
    show.add_argument("case", metavar="ID")
    show.add_argument("--tool", default=None, metavar="TOML",
                      help="run this one case against a tool")
    show.add_argument("--run", default=None, metavar="JSON",
                      help="read the result from a run file instead")
    show.add_argument("--tolerance", default="token:2")
    show.add_argument("--severity-floor", default="error",
                      choices=("error", "warning", "note"))
    show.set_defaults(func=cmd_show)

    dig = sub.add_parser("digest",
                         help="a run file reduced to case + reported error")
    dig.add_argument("run", metavar="RUN.json")
    dig.add_argument("--out", default=None, metavar="JSON",
                     help="write here (default: stdout)")
    dig.set_defaults(func=cmd_digest)

    grade = sub.add_parser("grade", help="re-score a run file's messages")
    grade.add_argument("run", metavar="RUN.json")
    grade.add_argument("--out", default=None, metavar="JSON",
                       help="write here instead of rewriting RUN.json")
    grade.add_argument("--tier", default="a", choices=("a", "b"),
                       help="b walks design §5.3's sample interactively")
    grade.add_argument("--rater", default=None, metavar="NAME",
                       help="who is scoring (required for --tier b)")
    grade.add_argument("--limit", type=int, default=None, metavar="N")
    grade.add_argument("--regrade", action="store_true",
                       help="re-ask for cases already scored by hand")
    grade.add_argument("--cache", default=str(SUITE_ROOT / ".rubric-cache.json"),
                       metavar="JSON", help="Tier-B score cache (gitignored)")
    grade.set_defaults(func=cmd_grade)

    tri = sub.add_parser("triage", help="the work queue, worst messages first")
    tri.add_argument("run", metavar="RUN.json")
    tri.add_argument("--filter", default=None, metavar="CLASS")
    tri.add_argument("--limit", type=int, default=None, metavar="N")
    tri.add_argument("--flag", default=None, metavar="FLAG",
                     help=f"only cases carrying this flag, e.g. "
                          f"{rubric.F_FIXIT_INVALID}")
    tri.add_argument("--notes", action="store_true",
                     help="print the per-dimension notes")
    tri.add_argument("--missing", default=None,
                     choices=("cause", "not_cause", "names"),
                     help="instead list gradeable cases lacking this header "
                          "field -- the metadata backfill queue")
    tri.set_defaults(func=cmd_triage)

    return top


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
