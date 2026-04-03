"""Unit tests for pssparser.cli.diagnostics."""
import pytest
from pssparser.cli.diagnostics import Diagnostic, DiagnosticCollection


# -- Diagnostic.from_marker -------------------------------------------------

class TestDiagnosticFromMarker:
    def test_basic_error(self):
        m = {
            "severity": "error",
            "message": "unknown type 'Pont'; did you mean 'Point'?",
            "file": "test.pss",
            "line": 10,
            "col": 5,
        }
        d = Diagnostic.from_marker(m)
        assert d.severity == "error"
        assert d.file == "test.pss"
        assert d.line == 10
        assert d.col == 5
        assert d.suggestion == "Point"
        # 'Pont' is 4 chars, end_col = 5 + 4 = 9
        assert d.end_col == 9

    def test_no_suggestion(self):
        m = {
            "severity": "error",
            "message": "unknown type 'CompletelyUnknownXYZ'",
            "file": "a.pss",
            "line": 1,
            "col": 1,
        }
        d = Diagnostic.from_marker(m)
        assert d.suggestion is None
        # end_col still computed from symbol length
        assert d.end_col == 1 + len("CompletelyUnknownXYZ")

    def test_warning(self):
        m = {
            "severity": "warning",
            "message": "some warning",
            "file": "b.pss",
            "line": 5,
            "col": 3,
        }
        d = Diagnostic.from_marker(m)
        assert d.severity == "warning"
        assert d.end_col is None  # no symbol in message

    def test_defaults(self):
        d = Diagnostic.from_marker({})
        assert d.file == "<unknown>"
        assert d.line == 0
        assert d.col == 1
        assert d.severity == "error"


# -- DiagnosticCollection ---------------------------------------------------

class TestDiagnosticCollection:
    def _make(self, sev="error"):
        return Diagnostic(
            file="t.pss", line=1, col=1, severity=sev, message="msg"
        )

    def test_counts(self):
        c = DiagnosticCollection()
        c.add(self._make("error"))
        c.add(self._make("warning"))
        c.add(self._make("error"))
        assert c.error_count == 2
        assert c.warning_count == 1

    def test_has_errors(self):
        c = DiagnosticCollection()
        assert not c.has_errors
        c.add(self._make("warning"))
        assert not c.has_errors
        c.add(self._make("error"))
        assert c.has_errors

    def test_max_errors(self):
        c = DiagnosticCollection(max_errors=2)
        assert c.add(self._make("error")) is True
        assert c.add(self._make("error")) is True
        # Third error exceeds limit
        assert c.add(self._make("error")) is False

    def test_files(self):
        c = DiagnosticCollection()
        c.add(Diagnostic(file="a.pss", line=1, col=1, severity="error", message=""))
        c.add(Diagnostic(file="b.pss", line=1, col=1, severity="error", message=""))
        c.add(Diagnostic(file="a.pss", line=2, col=1, severity="error", message=""))
        assert c.files == {"a.pss", "b.pss"}
