"""`[output] kind = "regex"` — scrape a tool's human-readable diagnostics.

Always reports ``parse_confidence = "regex"``.  That flag is not decoration:
any finding derived from a regex-scraped run (a missing location especially)
has to be confirmed by hand before it is believed, because "the tool didn't say
it" and "our pattern didn't catch it" look identical from here.
"""
from __future__ import annotations

import re

from ..descriptor import Descriptor
from .base import Diagnostic

_SEVERITY_MAP = {
    "error": "error", "err": "error", "fatal": "error", "e": "error",
    "warning": "warning", "warn": "warning", "w": "warning",
    "note": "note", "info": "note", "n": "note",
}


def normalize_severity(raw: str | None) -> str:
    if not raw:
        return "unknown"
    return _SEVERITY_MAP.get(raw.strip().lower(), "unknown")


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _streams(stdout: str, stderr: str, desc: Descriptor) -> str:
    if desc.stream == "stdout":
        return stdout
    if desc.stream == "stderr":
        return stderr
    return stdout + ("\n" if stdout and stderr else "") + stderr


def parse(stdout: str, stderr: str, desc: Descriptor):
    pattern = re.compile(desc.pattern)
    cont = re.compile(desc.continuation) if desc.continuation else None
    diags: list[Diagnostic] = []
    pending: dict | None = None

    def flush():
        nonlocal pending
        if pending is not None:
            diags.append(Diagnostic(**pending))
            pending = None

    for line in _streams(stdout, stderr, desc).splitlines():
        m = pattern.match(line)
        if m:
            flush()
            g = m.groupdict()
            pending = dict(
                severity=normalize_severity(g.get("severity")),
                message=(g.get("message") or "").strip(),
                file=g.get("file"),
                line=_int(g.get("line")),
                col=_int(g.get("col")),
                end_line=_int(g.get("end_line")),
                end_col=_int(g.get("end_col")),
                code=g.get("code"),
                raw=line,
            )
            continue
        if cont is not None and pending is not None:
            mc = cont.match(line)
            if mc:
                extra = (mc.groupdict().get("message") or "").strip()
                if extra:
                    # Folded into the primary, not emitted as a second
                    # diagnostic: a continuation line is the same finding, and
                    # counting it separately would make the tool look noisier
                    # than it is (design §4.3, message discipline).
                    pending["message"] = f"{pending['message']} {extra}".strip()
                    pending["raw"] = f"{pending['raw']}\n{line}"
                continue
        flush()
    flush()
    return diags, "regex"
