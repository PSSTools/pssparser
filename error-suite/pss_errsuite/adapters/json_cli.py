"""`[output] kind = "json"` — read structured diagnostics.

The default field mapping is pssparser's ``--json`` document (plan §0.2); any
other tool remaps with ``[output] fields``.  Note what pssparser does *not*
emit: there is no ``end_line``, so spans are single-line only, which caps it at
D2 = 2 for any construct that spans lines.  `Diagnostic.__post_init__` fills
``end_line = line`` so consumers need not care, and the cap is reported as the
tool defect it is rather than smoothed over.
"""
from __future__ import annotations

import json

from ..descriptor import Descriptor
from .base import Diagnostic, Fix, Related
from .regex_out import normalize_severity

DEFAULT_FIELDS = {
    "diagnostics": "diagnostics",
    "severity": "severity",
    "message": "message",
    "file": "file",
    "line": "line",
    "col": "col",
    "end_line": "end_line",
    "end_col": "end_col",
    "code": "code",
    "suggestion": "suggestion",
    "fix": "fix",
    "related": "related",
    "related_label": "label",
}


def _dig(doc, path: str):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _find_json(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # A tool that prints a banner before its JSON: take the widest {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _int(value):
    return value if isinstance(value, int) else None


def parse(stdout: str, stderr: str, desc: Descriptor):
    fields = dict(DEFAULT_FIELDS)
    fields.update(desc.fields)
    streams = [stdout] if desc.stream == "stdout" else (
        [stderr] if desc.stream == "stderr" else [stdout, stderr])

    doc = None
    for stream in streams:
        doc = _find_json(stream)
        if doc is not None:
            break
    if doc is None:
        # Nothing parseable.  If the tool said *something*, we failed to read
        # it and must say so; silence on a clean file is a legitimate empty
        # result with full confidence.
        said_something = any(s.strip() for s in streams)
        return [], ("none" if said_something else "structured")

    items = _dig(doc, fields["diagnostics"])
    if items is None and isinstance(doc, list):
        items = doc
    if not isinstance(items, list):
        return [], "none"

    diags = []
    for item in items:
        if not isinstance(item, dict):
            continue
        related = []
        for r in item.get(fields["related"]) or ():
            if isinstance(r, dict):
                related.append(Related(
                    file=r.get(fields["file"]),
                    line=_int(r.get(fields["line"])),
                    col=_int(r.get(fields["col"])),
                    label=str(r.get(fields["related_label"]) or ""),
                ))
        raw_fix = item.get(fields["fix"])
        fix = None
        if isinstance(raw_fix, dict):
            fix = Fix(
                file=raw_fix.get(fields["file"]) or item.get(fields["file"]),
                line=_int(raw_fix.get(fields["line"])),
                col=_int(raw_fix.get(fields["col"])),
                end_line=_int(raw_fix.get(fields["end_line"])),
                end_col=_int(raw_fix.get(fields["end_col"])),
                replacement=str(raw_fix.get("replacement") or ""),
            )
        diags.append(Diagnostic(
            severity=normalize_severity(item.get(fields["severity"])),
            message=str(item.get(fields["message"]) or ""),
            file=item.get(fields["file"]),
            line=_int(item.get(fields["line"])),
            col=_int(item.get(fields["col"])),
            end_line=_int(item.get(fields["end_line"])),
            end_col=_int(item.get(fields["end_col"])),
            code=item.get(fields["code"]),
            suggestion=item.get(fields["suggestion"]),
            fix=fix,
            related=tuple(related),
            raw=json.dumps(item, sort_keys=True),
        ))
    return diags, "structured"
