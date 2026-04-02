"""Unit tests for pssparser.cli.output (HumanOutput, JsonOutput)."""
import json
from io import StringIO

import pytest

from pssparser.cli.diagnostics import Diagnostic, DiagnosticCollection
from pssparser.cli.output import HumanOutput, JsonOutput
from pssparser.cli.source_context import SourceCache


@pytest.fixture
def sample_file(tmp_path):
    p = tmp_path / "test.pss"
    p.write_text("struct S {\n    Pont origin;\n};\n")
    return str(p)


def _diag(filepath="test.pss", **kw):
    defaults = dict(
        file=filepath,
        line=2,
        col=5,
        severity="error",
        message="unknown type 'Pont'; did you mean 'Point'?",
        suggestion="Point",
        end_col=9,
    )
    defaults.update(kw)
    return Diagnostic(**defaults)


# -- HumanOutput -----------------------------------------------------------

class TestHumanOutput:
    def test_header_and_caret(self, sample_file):
        buf = StringIO()
        sc = SourceCache()
        out = HumanOutput(sc, stream=buf, color=False)
        d = _diag(filepath=sample_file)
        out.emit(d)
        text = buf.getvalue()

        # Header line
        assert f"{sample_file}:2:5: error:" in text
        # Source line present
        assert "Pont origin;" in text
        # Caret underline
        assert "^~~~" in text
        # Suggestion replacement
        assert "Point" in text

    def test_no_suggestion_line(self, sample_file):
        buf = StringIO()
        sc = SourceCache()
        out = HumanOutput(sc, stream=buf, color=False)
        d = _diag(filepath=sample_file, suggestion=None)
        out.emit(d)
        lines = buf.getvalue().splitlines()
        # Should NOT have a replacement line after the caret
        caret_idx = next(i for i, l in enumerate(lines) if "^" in l)
        # The next line should be blank (separator), not a suggestion
        assert caret_idx == len(lines) - 2  # caret, then blank

    def test_summary(self):
        buf = StringIO()
        sc = SourceCache()
        out = HumanOutput(sc, stream=buf, color=False)
        coll = DiagnosticCollection()
        coll.add(_diag())
        coll.add(Diagnostic(
            file="test.pss", line=3, col=1,
            severity="warning", message="w",
        ))
        out.summary(coll)
        text = buf.getvalue()
        assert "1 error" in text
        assert "1 warning" in text
        assert "1 file" in text

    def test_summary_plurals(self):
        buf = StringIO()
        sc = SourceCache()
        out = HumanOutput(sc, stream=buf, color=False)
        coll = DiagnosticCollection()
        coll.add(_diag(filepath="a.pss"))
        coll.add(_diag(filepath="b.pss"))
        out.summary(coll)
        text = buf.getvalue()
        assert "2 errors" in text
        assert "2 files" in text


# -- JsonOutput -------------------------------------------------------------

class TestJsonOutput:
    def test_structure(self):
        buf = StringIO()
        out = JsonOutput(stream=buf)
        coll = DiagnosticCollection()
        d = _diag()
        coll.add(d)
        out.emit(d)
        out.summary(coll)

        doc = json.loads(buf.getvalue())
        assert "diagnostics" in doc
        assert "summary" in doc
        assert len(doc["diagnostics"]) == 1
        diag0 = doc["diagnostics"][0]
        assert diag0["file"] == "test.pss"
        assert diag0["line"] == 2
        assert diag0["col"] == 5
        assert diag0["severity"] == "error"
        assert diag0["suggestion"] == "Point"
        assert diag0["end_col"] == 9
        assert doc["summary"]["errors"] == 1

    def test_no_optional_fields_when_absent(self):
        buf = StringIO()
        out = JsonOutput(stream=buf)
        coll = DiagnosticCollection()
        d = Diagnostic(
            file="x.pss", line=1, col=1,
            severity="warning", message="w",
        )
        coll.add(d)
        out.emit(d)
        out.summary(coll)
        doc = json.loads(buf.getvalue())
        diag0 = doc["diagnostics"][0]
        assert "suggestion" not in diag0
        assert "end_col" not in diag0
        assert "code" not in diag0
