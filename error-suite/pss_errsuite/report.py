"""Run-file emission (design §6).

Everything a metric is computed from is in the file, so a report can be
recomputed under a different tolerance policy -- or re-graded under a new
rubric version -- without re-running any tool.  `test_report.py` asserts
that property by recomputing `summary.metrics` from `cases[]` alone.

Headline numbers are always written with their denominators, both skip counts,
and the tool's declared `pss` version.  A rate without a denominator is an
invitation to quote it out of context.
"""
from __future__ import annotations

import datetime
import json
import platform
import subprocess
import sys
from pathlib import Path

from . import rubric as rubric_mod
from .classify import (ALL_STATUSES, CLEAN, CONTROL_FAILED, CRASH, DETECTED,
                       DETECTED_MISLOCATED, DETECTED_WRONG_SEVERITY, MISSED,
                       SPURIOUS, TIMEOUT)
from .runner import CaseRun

SCHEMA = "pss-errsuite/run/1"


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def suite_revision(suite_root: Path) -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=suite_root, capture_output=True, text=True,
                             timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return "git:" + out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def compute_metrics(cases: list[dict]) -> dict:
    """Recomputable from the `cases[]` array alone -- deliberately.

    `detection_rate` counts only `detect: required` cases whose control passed:
    a debatable diagnostic must never count against anyone (design §1), and a
    case whose control failed says nothing about the defect.
    """
    def status_of(c):
        return c["status"]

    required = [c for c in cases
                if c["expect"]["detect"] == "required"
                and c["expect"]["kind"] != "accept"
                and status_of(c) != CONTROL_FAILED]
    det = sum(1 for c in required if status_of(c) == DETECTED)
    mis = sum(1 for c in required if status_of(c) == DETECTED_MISLOCATED)
    missed = sum(1 for c in required if status_of(c) == MISSED)
    wrong_sev = sum(1 for c in required
                    if status_of(c) == DETECTED_WRONG_SEVERITY)
    denom = det + mis + missed + wrong_sev

    accept = [c for c in cases if c["expect"]["kind"] == "accept"]
    spurious = sum(1 for c in accept if status_of(c) == SPURIOUS)
    clean = sum(1 for c in accept if status_of(c) == CLEAN)

    graded = [c for c in cases
              if status_of(c) in (DETECTED, DETECTED_MISLOCATED)]
    with_code = sum(1 for c in graded if c["observations"]["has_code"])

    counted = det + mis
    return {
        # Design §4.3's formula, with `detected_wrong_severity` added to the
        # denominator (plan §0.7): as written, a tool that reports every defect
        # at the wrong severity drops those cases out of the fraction entirely
        # and scores 1.0 on what is left.
        "detection_rate": round(det / denom, 4) if denom else None,
        "detection_denominator": denom,
        "localization_rate": round(det / counted, 4) if counted else None,
        "localization_denominator": counted,
        "false_positive_rate": (round(spurious / (spurious + clean), 4)
                                if (spurious + clean) else None),
        "false_positive_denominator": spurious + clean,
        "identifiability": round(with_code / len(graded), 4) if graded else None,
        "identifiability_denominator": len(graded),
        "robustness": sum(1 for c in cases
                          if status_of(c) in (CRASH, TIMEOUT)),
        "message_discipline": _message_discipline(cases),
    }


def _message_discipline(cases: list[dict]) -> dict:
    """Observation only.  A tool that emits two well-located errors where we
    emit one is *different*, not wrong, so this never feeds a headline."""
    graded = [c for c in cases
              if c["status"] in (DETECTED, DETECTED_MISLOCATED)]
    if not graded:
        return {"within_tolerance": None, "denominator": 0}
    ok = sum(1 for c in graded
             if abs(c["observations"]["error_count"]
                    - c["expect"].get("count", 1)) <= 1)
    return {"within_tolerance": round(ok / len(graded), 4),
            "denominator": len(graded)}


def _diagnostic_dict(diag) -> dict:
    """The tool's diagnostic, verbatim, plus a readable file name.

    `file` is whatever the tool printed, which is a path into the run's scratch
    directory (`/tmp/pss-errsuite-a1b2c3/case/...`) -- byte-exact output is the
    whole point of the field and normalizing it would throw away the evidence.
    But a scratch path is meaningless to a reader and differs between two runs
    of the same corpus for no real reason, so `file_rel` carries the name the
    case is actually known by alongside it.
    """
    out = diag.as_dict()
    if diag.file is not None:
        out["file_rel"] = diag.file.replace("\\", "/").rsplit("/", 1)[-1]
    return out


def case_document(run: CaseRun, include_source: bool = True) -> dict:
    case = run.case
    doc: dict = {
        "case": case.case_id,
        "class": case.cls,
        "title": case.title,
        "files": [str(p.relative_to(case.root)) for p in case.input_files()],
        # The file the case's own body lives in.  Not the same as `files[0]`:
        # a case with `files:` lists companions in tool order, and the case
        # file need not be first.  Any reader asking "did the tool point at
        # the right file" needs this, not a guess.
        "case_file": case.path.name,
        "source": case.source,
        "source_sha256": case.source_sha256,
        "expect": {
            "kind": case.expect,
            "detect": case.detect,
            "count": case.count,
            "pss": case.pss,
            "about": case.about,
        },
        "status": run.status,
        "observations": run.observations.as_dict(),
    }
    if case.at is not None:
        doc["expect"]["at"] = case.at.as_dict()
        # `at:` counts from line 1 of `at-file:` when one is named, and of the
        # case file otherwise -- exactly `classify._file_matches`.  Dropping it
        # here made the rubric fall back to `files[0]` and score five correct
        # multifile cases as pointing at the wrong file.
        doc["expect"]["at"]["file"] = case.at_file or case.path.name
    if case.also:
        doc["expect"]["also"] = [
            {"line": a.line, "col": a.col, "label": a.label} for a in case.also]
    if case.lrm:
        doc["expect"]["lrm"] = case.lrm
    if case.tags:
        doc["expect"]["tags"] = case.tags
    if case.requires:
        doc["expect"]["requires"] = case.requires
    for key in ("cause", "not_cause", "names"):
        value = getattr(case, key)
        if value:
            doc["expect"][key] = value
    if run.skip_reason:
        doc["skip_reason"] = run.skip_reason
    if run.notes:
        doc["notes"] = run.notes
    if run.result is not None:
        doc["result"] = {
            "exit_code": run.result.exit_code,
            "duration_s": round(run.result.duration_s, 4),
            "timed_out": run.result.timed_out,
            "crashed": run.result.crashed,
            "parse_confidence": run.result.parse_confidence,
            "diagnostics": [_diagnostic_dict(d) for d in
                            run.result.diagnostics],
            "stdout": run.result.stdout,
            "stderr": run.result.stderr,
        }
        if run.result.invocation_error:
            doc["result"]["invocation_error"] = run.result.invocation_error
    if run.control_status is not None:
        doc["control"] = {"status": run.control_status,
                          "error_count": run.control_error_count}
    # Scored before `source` can be dropped: D3's fallback -- does the message
    # contain any of the user's own vocabulary -- has to read the program.
    block = rubric_mod.score_case(doc)
    if block is not None:
        doc["rubric"] = block
    if not include_source:
        doc.pop("source", None)
    return doc


def build_document(runs: list[CaseRun], *, desc, adapter, tolerance,
                   severity_floor: str, suite_root: Path, started: str,
                   duration_s: float, include_source: bool = True,
                   tool_pss: str | None = None,
                   pss_assumed: bool = False,
                   warnings: list[str] | None = None) -> dict:
    cases = [case_document(r, include_source) for r in runs]
    by_status = {s: 0 for s in ALL_STATUSES}
    by_class: dict[str, dict[str, int]] = {}
    for c in cases:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        bucket = by_class.setdefault(c["class"], {})
        bucket[c["status"]] = bucket.get(c["status"], 0) + 1

    version = getattr(adapter, "version", "unknown")
    return {
        "schema": SCHEMA,
        "run": {
            "id": f"{started}-{desc.name}-{version}",
            "started": started,
            "duration_s": round(duration_s, 3),
            "host": {"os": platform.system().lower(),
                     "python": platform.python_version()},
            "suite": {
                "path": str(suite_root.name + "/cases"),
                "revision": suite_revision(suite_root),
                "case_count": len(cases),
            },
            "policy": {
                "tolerance": tolerance.spec,
                "timeout_s": desc.timeout_s,
                "severity_floor": severity_floor,
                "rubric_version": rubric_mod.RUBRIC_VERSION,
            },
            "warnings": warnings or [],
        },
        "tool": {
            "name": desc.name,
            "version": version,
            "pss": tool_pss,
            "pss_assumed": pss_assumed,
            "descriptor": str(desc.path.name),
            "invocation": desc.argv,
            "capabilities": desc.capabilities.as_dict(),
            "parse_confidence": _overall_confidence(runs),
        },
        "summary": {
            "by_status": by_status,
            "by_class": by_class,
            "metrics": compute_metrics(cases),
            "rubric": rubric_mod.rollup(cases),
        },
        "cases": cases,
    }


def _overall_confidence(runs: list[CaseRun]) -> str:
    # Only runs that actually produced output say anything about how well we
    # can read this tool.  A timeout reports "none" because there was nothing
    # to parse, and letting one hang downgrade the whole run's confidence would
    # misdescribe every other case in it.
    seen = {r.result.parse_confidence for r in runs
            if r.result is not None and not r.result.timed_out
            and not r.result.crashed and not r.result.invocation_error}
    for level in ("none", "regex", "structured"):
        if level in seen:
            return level
    return "structured"


def write(document: dict, path: Path | None) -> None:
    text = json.dumps(document, indent=2, sort_keys=False) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
