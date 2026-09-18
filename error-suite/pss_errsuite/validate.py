"""Corpus self-validation (design §9).

`validate` runs before any tool does, and it is the one part of the suite that
is a *gate* rather than a measurement: a malformed case silently produces a
wrong number, and a wrong number is worse than no number.

The rule that matters most is the `detect: required` / `lrm:` pairing.  A
`required` case is one we are prepared to say a tool *must* diagnose, so it
carries the clause that says so.  Enforcing it mechanically is what keeps the
headline detection rate defensible when a vendor disputes it (design §3.2).
"""
from __future__ import annotations

import re
from pathlib import Path

from .case import TOOL_KEYS, Case, CaseFormatError
from .taxonomy import CAPABILITIES, PSS_VERSIONS, is_known_class

#: Target is < 40 lines (design §3.1).  The gate sits above the target so that
#: a case with a legitimately long-ish preamble is a review conversation, not a
#: build break.
LINE_BUDGET = 60
LINE_TARGET = 40


class Finding:
    def __init__(self, path: Path, message: str, severity: str = "error"):
        self.path = path
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"{self.path}: {self.severity}: {self.message}"


def validate_corpus(root: Path) -> list[Finding]:
    root = Path(root)
    findings: list[Finding] = []
    cases: list[Case] = []

    for path in sorted(root.rglob("*.pss")):
        if path.name.startswith("_") or path.name.endswith(".ok.pss"):
            continue
        try:
            cases.append(_load(path, root))
        except CaseFormatError as e:
            findings.append(Finding(path, str(e)))

    seen: dict[str, Path] = {}
    for case in cases:
        if case.case_id in seen:
            findings.append(Finding(
                case.path,
                f"duplicate case id {case.case_id!r}; also used by "
                f"{seen[case.case_id]}"))
        else:
            seen[case.case_id] = case.path
        findings.extend(validate_case(case))
    return findings


def _load(path: Path, root: Path) -> Case:
    from .case import load_case
    return load_case(path, root)


def validate_case(case: Case) -> list[Finding]:
    out: list[Finding] = []
    path = case.path

    if not is_known_class(case.cls):
        out.append(Finding(path, f"class {case.cls!r} is not in the taxonomy"))

    if case.pss not in PSS_VERSIONS:
        out.append(Finding(
            path, f"pss: {case.pss!r} is not a version the corpus declares "
                  f"support for {list(PSS_VERSIONS)}"))

    for req in case.requires:
        if req == "solver":
            out.append(Finding(
                path, "requires: solver -- solver-dependent defects are out of "
                      "scope (design §1); this case should not exist"))
        elif req not in CAPABILITIES:
            out.append(Finding(
                path, f"requires: {req!r} is not a known capability "
                      f"{list(CAPABILITIES)}"))

    # A `<tool>.<key>` nobody consumes does nothing and says nothing about it.
    # A warning rather than an error: the namespace may belong to a tool this
    # suite has never been shown, and a corpus that refuses to validate until
    # every vendor is onboarded is worse than an unread directive.
    for tool, opts in sorted(case.tool_opts.items()):
        for key in sorted(set(opts) - TOOL_KEYS):
            out.append(Finding(
                path, f"{tool}.{key}: no reader in this suite consumes "
                      f"{key!r} (known: {', '.join(sorted(TOOL_KEYS))}); it "
                      f"will be ignored", severity="warning"))

    # `at-file:` decides which file the diagnostic must be attributed to, so a
    # typo there silently turns every run of the case into a `missed`.
    if case.at_file and case.at_file not in (case.files or []):
        out.append(Finding(
            path, f"at-file: {case.at_file!r} is not in files: "
                  f"{case.files or [path.name]}"))

    # -- controls ---------------------------------------------------------
    if case.expect != "accept":
        try:
            own = case.control_source()
            overrides = case.control_overrides()
        except CaseFormatError as e:
            own, overrides = None, None
            out.append(Finding(path, str(e)))
        if own is not None and own == case.source:
            out.append(Finding(
                path, "the control is identical to the case -- the 'fix:' "
                      "directive changed nothing"))
        elif overrides is None:
            out.append(Finding(
                path, "no control: add a '<name>.ok.pss' sibling or a 'fix:' "
                      "directive -- or, when the defect is in a companion "
                      "file, a '.ok.pss' beside that companion. Without one, "
                      "a tool that rejects the scaffolding scores a "
                      "detection"))

    # -- the promotion rule -----------------------------------------------
    if case.detect == "required" and not case.lrm:
        out.append(Finding(
            path, "detect: required needs an 'lrm:' clause citation (design "
                  "§3.2): required means the LRM says shall/is an error"))
    if case.cls.startswith("semantic.") and not case.lrm:
        out.append(Finding(path, "semantic cases need an 'lrm:' citation"))

    # -- rubric metadata (design §5.4) ------------------------------------
    overlap = set(t.lower() for t in case.cause) & set(
        t.lower() for t in case.not_cause)
    if overlap:
        out.append(Finding(
            path, f"not_cause: {sorted(overlap)} also appears in cause:; a "
                  f"term cannot be both required and forbidden"))
    for name in case.names:
        if not re.search(r"\b" + re.escape(name) + r"\b", case.body):
            out.append(Finding(
                path, f"names: {name!r} does not occur in the case source"))

    # -- budget -----------------------------------------------------------
    n_lines = len(case.source.splitlines())
    if n_lines > LINE_BUDGET:
        out.append(Finding(
            path, f"{n_lines} lines exceeds the {LINE_BUDGET}-line budget "
                  f"(target is < {LINE_TARGET})"))
    elif n_lines > LINE_TARGET:
        out.append(Finding(
            path, f"{n_lines} lines is over the {LINE_TARGET}-line target",
            severity="warning"))

    if case.expect != "accept" and not case.title:
        out.append(Finding(path, "missing 'title:'", severity="warning"))

    return out
