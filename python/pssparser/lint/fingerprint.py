"""A finding's identity, independent of where it is in the file.

A baseline has to recognise a finding it recorded after the file has been
edited: lines inserted above it, the file reformatted, a comment added inside
the flagged code.  So the fingerprint hashes what was flagged and where in the
*model* it is, never the line or column::

    sha256(code \\0 decl_path \\0 normalised_span)

* ``code`` is the marker ID.
* ``decl_path`` is the enclosing declaration
  (:mod:`pssparser.lint.declpath`), such as ``pkg::C::A::constraint c``.
* ``normalised_span`` is the source text of the code tokens the diagnostic's
  span overlaps, joined by single spaces.  Whitespace and comments are
  dropped, so reformatting does not change it.  A diagnostic with no extent
  covers the one token at its column.

The digest is cut to its first 16 hex digits (64 bits): the baseline also
keys on the code and the file, so collisions are not a practical concern,
and a short value keeps a baseline file readable.

Two identical findings in one declaration have the same fingerprint; the
baseline tells them apart by counting them (``Entry.count``).
"""
from __future__ import annotations

import bisect
import hashlib
import os
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

#: Identifies the algorithm.  SARIF reports the value under this key in
#: ``partialFingerprints``; change it if the hash input ever changes.
SCHEME = "pssparser/v1"

#: Hex digits kept from the SHA-256 digest.
DIGEST_LEN = 16


def _location(diag) -> Tuple[str, int, int, int]:
    """(file, line, col, extent) from a Diagnostic or a marker dict."""
    if isinstance(diag, dict):
        col = int(diag.get("col", 0) or 0)
        return (diag.get("file", ""), int(diag.get("line", 0) or 0), col,
                int(diag.get("extent", 0) or 0))
    col = int(getattr(diag, "col", 0) or 0)
    extent = getattr(diag, "extent", None)
    if extent is None:
        end_col = getattr(diag, "end_col", None)
        extent = (end_col - col) if end_col and end_col > col else 0
    return (getattr(diag, "file", ""), int(getattr(diag, "line", 0) or 0),
            col, int(extent or 0))


def _code(diag) -> str:
    if isinstance(diag, dict):
        return diag.get("code") or ""
    return getattr(diag, "code", None) or ""


class SourceTokens:
    """One file's code tokens, with offset lookup by line and column."""

    def __init__(self, source: Any):
        from pssparser import tokens

        stream = source if hasattr(source, "code") else tokens.tokenize(source)
        text = stream.text
        self._line_starts = [0]
        pos = text.find("\n")
        while pos >= 0:
            self._line_starts.append(pos + 1)
            pos = text.find("\n", pos + 1)
        self._code = [t for t in stream if not t.is_trivia]
        self._stops = [t.stop for t in self._code]

    def offset(self, line: int, col: int) -> Optional[int]:
        """Code-point offset of a 1-based *line* and *col*."""
        if line < 1 or line > len(self._line_starts):
            return None
        return self._line_starts[line - 1] + max(col, 1) - 1

    def span(self, line: int, col: int, extent: int = 0) -> str:
        """The normalised text of the span; ``""`` if it covers no code."""
        start = self.offset(line, col)
        if start is None:
            return ""
        # The first code token that ends at or after the start: the one the
        # span starts in, or the next one when it starts on whitespace.
        i = bisect.bisect_left(self._stops, start)
        if i >= len(self._code):
            return ""
        if extent <= 0:
            return self._code[i].text
        end = start + extent
        out: List[str] = []
        while i < len(self._code) and self._code[i].start < end:
            out.append(self._code[i].text)
            i += 1
        return " ".join(out)


def normalised_span(source: Any, line: int, col: int, extent: int = 0) -> str:
    """The normalised text of a span: code tokens joined by single spaces.

    *source* is PSS text, bytes or a :class:`~pssparser.tokens.TokenStream`.
    *line* and *col* are 1-based; *extent* counts characters, and ``0`` means
    the one token at that column.
    """
    return SourceTokens(source).span(line, col, extent)


def digest(code: str, decl_path: str, span: str) -> str:
    """The fingerprint of an already normalised span."""
    h = hashlib.sha256("\0".join((code, decl_path, span)).encode("utf-8"))
    return h.hexdigest()[:DIGEST_LEN]


def fingerprint(diag, decl_path: str, source: Any) -> str:
    """The fingerprint of *diag* (a ``Diagnostic`` or marker dict).

    *decl_path* is the enclosing declaration's path, ``""`` at file scope;
    *source* is the text of the diagnostic's file, or its token stream.
    """
    _, line, col, extent = _location(diag)
    return digest(_code(diag), decl_path, normalised_span(source, line, col, extent))


class Fingerprinter:
    """Fingerprints many diagnostics, tokenizing each file once.

    *index* is a :class:`~pssparser.lint.declpath.DeclPathIndex`, or ``None``
    when there is no AST (every path is then ``""``).  *read* returns a
    file's text; it defaults to reading the file as UTF-8.
    """

    def __init__(self, index=None, read: Optional[Callable[[str], Any]] = None):
        self._index = index
        self._read = read or _read_file
        self._files: Dict[str, Optional[SourceTokens]] = {}

    def _tokens(self, path: str) -> Optional[SourceTokens]:
        key = os.path.realpath(path) if path else path
        if key not in self._files:
            try:
                self._files[key] = SourceTokens(self._read(path))
            except (OSError, UnicodeDecodeError, ValueError):
                self._files[key] = None
        return self._files[key]

    def decl_path(self, diag) -> str:
        file, line, col, _ = _location(diag)
        if self._index is None or line < 1:
            return ""
        return self._index.path_at(file, line, col)

    def __call__(self, diag) -> Optional[str]:
        """The fingerprint, or ``None`` for a diagnostic with no code or no
        readable source location."""
        code = _code(diag)
        file, line, col, extent = _location(diag)
        if not code or line < 1 or not file:
            return None
        toks = self._tokens(file)
        if toks is None:
            return None
        return digest(code, self.decl_path(diag), toks.span(line, col, extent))


def _read_file(path: str) -> bytes:
    with open(path, "rb") as fp:
        return fp.read()


def assign(diags: Iterable[Any], fingerprinter: Fingerprinter) -> None:
    """Set ``fingerprint`` on each Diagnostic that has one."""
    for diag in diags:
        diag.fingerprint = fingerprinter(diag)
