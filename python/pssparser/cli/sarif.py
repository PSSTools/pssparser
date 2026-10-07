"""SARIF 2.1.0 output (``--format sarif``).

One ``run`` per invocation.  ``tool.driver.rules`` lists every rule that was
enabled for the run plus every ID that appears in a result, so a code-scanning
UI can show a rule's help even for a finding from a core diagnostic.

Severity maps to ``level`` per lint-framework L1: ``error`` -> ``error``,
``warning`` -> ``warning``, ``info`` -> ``note``, ``hint`` -> ``none``.
Tool diagnostics (an extension that failed to load) have no source location
and are reported as results without ``locations``, which SARIF permits.
A diagnostic a source waiver covered is a result with an ``inSource``
suppression whose justification is the waiver's reason.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, TextIO

from pssparser.checkers.extension import NO_FILE
from pssparser.checkers import taxonomy
from .diagnostics import Diagnostic, DiagnosticCollection

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"

LEVELS = {"error": "error", "warning": "warning", "info": "note", "hint": "none"}

_CODE_PREFIX = re.compile(r"^\[[A-Z]{2,5}[0-9]{3}\]\s*")


def strip_code(message: str) -> str:
    """Drop a leading ``[ID] `` -- SARIF carries the ID in ``ruleId``."""
    return _CODE_PREFIX.sub("", message, count=1)


def artifact_uri(path: str) -> str:
    """A path relative to the working directory when it lies below it,
    otherwise an absolute ``file://`` URI."""
    try:
        rel = os.path.relpath(path)
        if not rel.startswith(".."):
            return Path(rel).as_posix()
    except ValueError:
        pass
    return Path(os.path.abspath(path)).as_uri()


def _region(line: int, col: int, end_col: Optional[int]) -> dict:
    region = {"startLine": max(line, 1), "startColumn": max(col, 1)}
    if end_col is not None and end_col > col:
        region["endColumn"] = end_col
    return region


class SarifOutput:
    """Collect diagnostics and write one SARIF log to *stream*."""

    def __init__(
        self,
        stream: TextIO | None = None,
        catalog: Optional[Dict[str, object]] = None,
        enabled_rules: Optional[List[str]] = None,
    ) -> None:
        self._stream = stream or sys.stdout
        self._catalog = catalog or {}
        self._enabled = list(enabled_rules or [])
        self._diags: List[Diagnostic] = []

    def emit(self, diag: Diagnostic) -> None:
        self._diags.append(diag)

    def finish(self, coll: DiagnosticCollection, quiet: bool, stats=None) -> None:
        if quiet:
            return
        # A waived finding is still a result in SARIF, marked suppressed: a
        # code-scanning UI shows it as dismissed, with the reason.
        self._diags.extend(getattr(coll, "waived", []))
        json.dump(self.document(), self._stream, indent=2)
        self._stream.write("\n")

    # -- document ---------------------------------------------------------

    def _rule(self, code: str) -> dict:
        rule: dict = {"id": code}
        md = self._catalog.get(code)
        if md is None:
            return rule
        if getattr(md, "name", ""):
            rule["name"] = md.name
        rule["shortDescription"] = {"text": md.summary}
        if md.detail:
            rule["fullDescription"] = {"text": md.detail}
        rule["defaultConfiguration"] = {"level": LEVELS.get(md.severity, "warning")}
        if taxonomy.namespace_of(code) == "LINT":
            rule["helpUri"] = taxonomy.doc_url(code)
        props: dict = {}
        if getattr(md, "tier", ""):
            props["tier"] = md.tier
        if getattr(md, "family", ""):
            props["family"] = md.family
        tags = [t for t in (getattr(md, "tier", ""), getattr(md, "family", "")) if t]
        if tags:
            props["tags"] = tags
        if getattr(md, "lrm", ()):
            props["lrm"] = list(md.lrm)
        if props:
            rule["properties"] = props
        return rule

    def document(self) -> dict:
        from pssparser.__version__ import get_version

        codes: List[str] = []
        for code in self._enabled + [d.code for d in self._diags if d.code]:
            if code not in codes:
                codes.append(code)
        rules = [self._rule(c) for c in codes]
        index = {c: i for i, c in enumerate(codes)}

        results = []
        for diag in self._diags:
            result: dict = {
                "level": LEVELS.get(diag.severity, "warning"),
                "message": {"text": strip_code(diag.message)},
            }
            if diag.code:
                result["ruleId"] = diag.code
                result["ruleIndex"] = index[diag.code]
            if diag.file != NO_FILE:
                result["locations"] = [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": artifact_uri(diag.file)},
                        "region": _region(diag.line, diag.col, diag.end_col),
                    }
                }]
            if diag.related:
                result["relatedLocations"] = [
                    {
                        "id": n,
                        "message": {"text": rel.label},
                        "physicalLocation": {
                            "artifactLocation": {"uri": artifact_uri(rel.file)},
                            "region": _region(rel.line, rel.col, None),
                        },
                    }
                    for n, rel in enumerate(diag.related)
                ]
            if diag.original_severity is not None:
                result["properties"] = {
                    "originalSeverity": diag.original_severity,
                    "promotedBy": diag.werror_flag,
                }
            if diag.waiver is not None:
                result["suppressions"] = [{
                    "kind": "inSource",
                    "justification": diag.waiver.get("reason", ""),
                }]
            results.append(result)

        return {
            "$schema": SARIF_SCHEMA,
            "version": SARIF_VERSION,
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "pssparser",
                        "version": get_version(),
                        "informationUri": taxonomy.PROJECT_URL,
                        "rules": rules,
                    }
                },
                "results": results,
            }],
        }
