"""In-process pssparser adapter: the fast path for the gap-finding loop.

This is the **only** module in the harness that may touch pssparser, and it
imports it lazily inside `run()` so that the suite stays runnable by someone who
has another vendor's tool and no pssparser build at all
(`test_no_toplevel_pssparser_import.py` enforces that).

Two behaviours are not shared with the CLI descriptor and must not be smoothed
over, because the divergence is itself information (plan §0.3):

* `Parser.parse()` raises `ParseException` as soon as a file produces an error,
  **before the remaining files are read**.  For a multi-file case that means
  the later files were never seen; we record that rather than hiding it.
* The checker phase the CLI runs is not reproduced here.  Diagnostics that come
  from checkers appear under `pssparser-cli` and not under this adapter.

So the two pssparser descriptors are expected to disagree on
`syntax.multifile`, `syntax.volume` and anything checker-emitted.  Comparing
them is the first real exercise of `compare` (design §7).
"""
from __future__ import annotations

import time
from pathlib import Path

from .base import CaseOpts, Diagnostic, Related, ToolResult

_SEVERITY_MAP = {"error": "error", "warning": "warning", "info": "note",
                 "hint": "note"}


class InProcessPssparserAdapter:
    name = "pssparser"

    def __init__(self, desc=None):
        self.desc = desc
        self.name = desc.name if desc is not None else "pssparser"
        self.version = "unknown"

    def probe_version(self) -> str:
        try:
            from pssparser.__version__ import get_version
            self.version = get_version()
        except Exception as e:  # pragma: no cover - only when unimportable
            self.version = f"unknown ({e})"
        return self.version

    def run(self, files: list[Path], opts: CaseOpts) -> ToolResult:
        try:
            from pssparser import Parser
            from pssparser.parser import ParseException
        except Exception as e:
            return ToolResult(
                exit_code=None,
                invocation_error=f"pssparser is not importable: {e}",
                parse_confidence="none")

        t0 = time.perf_counter()
        parser = Parser()
        if opts.max_errors is not None:
            try:
                parser.setMaxErrors(opts.max_errors)
            except AttributeError:
                pass
        truncated = False
        try:
            parser.parse([str(f) for f in files])
            parser.link()
        except ParseException as exc:
            markers = getattr(exc, "markers", None) or parser.markers
            truncated = len(files) > 1
            return self._result(markers, t0, truncated)
        except Exception as e:
            return ToolResult(
                exit_code=None, crashed=True, duration_s=time.perf_counter() - t0,
                stderr=f"{type(e).__name__}: {e}", parse_confidence="none")
        return self._result(parser.markers, t0, truncated)

    def _result(self, markers, t0: float, truncated: bool) -> ToolResult:
        diags = tuple(_to_diagnostic(m) for m in markers)
        stderr = ("note: parse aborted at the first erroring file; later "
                  "files were not read\n" if truncated else "")
        errors = any(d.severity == "error" for d in diags)
        return ToolResult(
            exit_code=1 if errors else 0,
            diagnostics=diags,
            stderr=stderr,
            duration_s=time.perf_counter() - t0,
            parse_confidence="structured",
        )


def _to_diagnostic(m: dict) -> Diagnostic:
    col = m.get("col")
    extent = m.get("extent") or 0
    related = tuple(
        Related(file=r.get("file"), line=r.get("line"), col=r.get("col"),
                label=r.get("label", ""))
        for r in (m.get("related") or ()))
    return Diagnostic(
        severity=_SEVERITY_MAP.get(m.get("severity"), "unknown"),
        message=m.get("message", ""),
        file=m.get("file"),
        line=m.get("line"),
        col=col,
        end_col=(col + extent) if (col is not None and extent) else None,
        code=m.get("code") or None,
        related=related,
    )
