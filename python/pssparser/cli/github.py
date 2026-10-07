"""GitHub Actions workflow-command output (``--format github``).

One ``::error``/``::warning``/``::notice`` line per diagnostic, which GitHub
turns into an annotation on the pull request.  ``hint`` diagnostics are not
emitted: an annotation is not an editor nudge.  Escaping follows GitHub's
workflow-command rules: ``%``, CR and LF in the message; additionally ``:``
and ``,`` in property values.
"""
from __future__ import annotations

import sys
from typing import TextIO

from pssparser.checkers.extension import NO_FILE
from .diagnostics import Diagnostic, DiagnosticCollection
from .sarif import artifact_uri, strip_code

_COMMANDS = {"error": "error", "warning": "warning", "info": "notice"}


def escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(text: str) -> str:
    return escape_data(text).replace(":", "%3A").replace(",", "%2C")


class GithubOutput:
    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout

    def emit(self, diag: Diagnostic) -> None:
        command = _COMMANDS.get(diag.severity)
        if command is None:
            return
        props = []
        if diag.file != NO_FILE:
            props.append(f"file={escape_property(artifact_uri(diag.file))}")
            props.append(f"line={diag.line}")
            props.append(f"col={diag.col}")
            if diag.end_col is not None and diag.end_col > diag.col:
                props.append(f"endColumn={diag.end_col}")
        if diag.code:
            props.append(f"title={escape_property(diag.code)}")
        head = f"::{command} {','.join(props)}" if props else f"::{command}"
        self._stream.write(f"{head}::{escape_data(strip_code(diag.message))}\n")

    def finish(self, coll: DiagnosticCollection, quiet: bool, stats=None) -> None:
        pass
