"""The run file, reduced to "which case, and what did the tool say" (§6).

A run file is ~700 KB for 167 cases because it is evidence: every case's full
source, both streams verbatim, the control result, the rubric block with its
notes. That is the right shape for something another tool reads, and the wrong
shape for a person scrolling it.

A digest is the same run, one line of meaning per diagnostic, at about a
fifteenth the size. It is **derived, never a substitute**: nothing here is
computed, every field is copied from the run file, and anything that needed
recomputing (a different tolerance, a newer rubric) has to go back to the run
file. So a digest is safe to read and useless to argue from, which is the
correct pair of properties for a summary.

Same publication rule as everything else derived from a run: a digest names a
tool and reports how it diagnoses the corpus, so it stays out of version
control. `.gitignore` covers `runs/`.
"""
from __future__ import annotations

SCHEMA = "pss-errsuite/digest/1"


def _where(line, col) -> str | None:
    if line is None:
        return None
    return f"{line}:{col}" if col is not None else f"{line}"


def _span(diag: dict) -> str | None:
    """`14:9` or `14:9-14` -- the end only when the tool actually gave one."""
    base = _where(diag.get("line"), diag.get("col"))
    if base is None:
        return None
    end_col = diag.get("end_col")
    if end_col is None:
        return base
    end_line = diag.get("end_line")
    if end_line is not None and end_line != diag.get("line"):
        return f"{base}-{end_line}:{end_col}"
    return f"{base}-{end_col}"


def digest_case(case: dict) -> dict:
    """One case: what we asked, what came back."""
    expect = case.get("expect") or {}
    at = expect.get("at") or {}
    out: dict = {
        "case": case.get("case"),
        "class": case.get("class"),
        "title": case.get("title"),
        "file": (case.get("files") or [None])[0],
        "expect": expect.get("kind"),
        "detect": expect.get("detect"),
        "status": case.get("status"),
    }
    if at:
        out["at"] = _where(at.get("line"), at.get("col"))
    if expect.get("lrm"):
        out["lrm"] = expect["lrm"]

    reported = []
    primary = (case.get("observations") or {}).get("primary_index")
    for i, diag in enumerate((case.get("result") or {}).get("diagnostics")
                             or []):
        entry = {"severity": diag.get("severity"),
                 "at": _span(diag),
                 "message": diag.get("message")}
        if diag.get("code"):
            entry["code"] = diag["code"]
        own = (out["file"] or "").rsplit("/", 1)[-1]
        if diag.get("file_rel") and diag["file_rel"] != own:
            # Only worth saying when it is *not* the case's own file: a
            # multifile case whose diagnostic lands on a companion is exactly
            # the attribution question that class exists to ask.
            entry["file"] = diag["file_rel"]
        if diag.get("suggestion"):
            entry["suggestion"] = diag["suggestion"]
        if i == primary:
            entry["primary"] = True
        reported.append(entry)
    out["reported"] = reported

    if case.get("skip_reason"):
        out["skip_reason"] = case["skip_reason"]
    if (case.get("control") or {}).get("status") == "failed":
        # Never silently drop this: a failed control means the result above
        # says nothing about the defect.
        out["control"] = "failed"

    rubric = case.get("rubric")
    if rubric:
        out["rubric"] = {
            "composite": rubric.get("composite"),
            # `d1..d6` as one string, `-` for unmeasured: readable at a glance
            # and the same column order `triage` prints.
            "scores": "".join("-" if rubric.get(d) is None
                              else str(rubric[d])
                              for d in ("d1", "d2", "d3", "d4", "d5", "d6")),
        }
        if rubric.get("flags"):
            out["rubric"]["flags"] = rubric["flags"]
    return out


def build(document: dict) -> dict:
    run = document.get("run") or {}
    tool = document.get("tool") or {}
    summary = document.get("summary") or {}
    return {
        "schema": SCHEMA,
        "run": {
            "id": run.get("id"),
            "started": run.get("started"),
            "suite": (run.get("suite") or {}).get("revision"),
            "case_count": (run.get("suite") or {}).get("case_count"),
            "policy": run.get("policy"),
        },
        "tool": {
            "name": tool.get("name"),
            "version": tool.get("version"),
            "pss": tool.get("pss"),
            "parse_confidence": tool.get("parse_confidence"),
        },
        "summary": {
            "by_status": summary.get("by_status"),
            "metrics": summary.get("metrics"),
        },
        "cases": [digest_case(c) for c in document.get("cases") or []],
    }
