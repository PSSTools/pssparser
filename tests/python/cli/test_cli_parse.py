"""End-to-end tests for the CLI.

These tests invoke the CLI programmatically via ``cli.app.main()`` and
verify exit codes and output patterns for each mode.
"""
import json
import os
from io import StringIO

from pssparser.cli.app import main as cli_main


# -- helpers ----------------------------------------------------------------

def _write_pss(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def _run(argv, capture_stderr=True, capture_stdout=True):
    """Run cli_main with argv, return (exit_code, stderr_text, stdout_text)."""
    import sys
    old_err, old_out = sys.stderr, sys.stdout
    err_buf = StringIO() if capture_stderr else old_err
    out_buf = StringIO() if capture_stdout else old_out
    sys.stderr = err_buf
    sys.stdout = out_buf
    try:
        rc = cli_main(argv)
    except SystemExit as e:
        rc = e.code if e.code is not None else 0
    finally:
        sys.stderr = old_err
        sys.stdout = old_out
    return rc, err_buf.getvalue() if capture_stderr else "", out_buf.getvalue() if capture_stdout else ""


# -- valid input ------------------------------------------------------------

class TestParseValid:
    def test_valid_file_exit_zero(self, tmp_path):
        f = _write_pss(tmp_path, "ok.pss", "struct S { int x; };")
        rc, err, _ = _run([f])
        assert rc == 0
        assert "0 errors" in err


# -- syntax errors ----------------------------------------------------------

class TestParseSyntaxErrors:
    def test_missing_semicolon(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss", "struct S { int x }")
        rc, err, _ = _run([f])
        assert rc == 1
        assert "error" in err.lower()

    def test_source_context_shown(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss", "struct S { int x }")
        rc, err, _ = _run(["--no-color", f])
        assert rc == 1
        # caret or source line should appear
        assert "^" in err or "int x" in err


# -- resolution errors ------------------------------------------------------

class TestParseResolutionErrors:
    def test_unknown_type(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss",
                        "struct S { UnknownType x; };")
        rc, err, _ = _run(["--no-color", f])
        assert rc == 1
        assert "UnknownType" in err

    def test_did_you_mean(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss",
                        "struct Point { int x; }; struct S { Pont p; };")
        rc, err, _ = _run(["--no-color", f])
        assert rc == 1
        assert "did you mean" in err.lower()


# -- --syntax-only -----------------------------------------------------------

class TestSyntaxOnly:
    def test_syntax_only_skips_link_errors(self, tmp_path):
        """Unknown type should NOT be caught with --syntax-only."""
        f = _write_pss(tmp_path, "ref.pss",
                        "struct S { UnknownType x; };")
        rc, err, _ = _run(["--syntax-only", f])
        assert rc == 0

    def test_syntax_only_catches_syntax(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss", "struct S { int x }")
        rc, err, _ = _run(["--syntax-only", f])
        assert rc == 1


# -- --json -----------------------------------------------------------------

class TestJsonMode:
    def test_json_valid(self, tmp_path):
        f = _write_pss(tmp_path, "ok.pss", "struct S { int x; };")
        rc, _, out = _run(["--json", f])
        assert rc == 0
        doc = json.loads(out)
        assert doc["summary"]["errors"] == 0

    def test_json_with_errors(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss",
                        "struct S { UnknownType x; };")
        rc, _, out = _run(["--json", f])
        assert rc == 1
        doc = json.loads(out)
        assert doc["summary"]["errors"] >= 1
        assert any("UnknownType" in d["message"]
                    for d in doc["diagnostics"])


# -- --dump-ast --------------------------------------------------------------

class TestDumpAst:
    def test_dump_creates_file(self, tmp_path):
        f = _write_pss(tmp_path, "ok.pss", "struct S { int x; };")
        ast_out = str(tmp_path / "ast.json")
        rc, _, _ = _run(["--dump-ast", ast_out, f])
        assert rc == 0
        assert os.path.isfile(ast_out)
        doc = json.loads(open(ast_out).read())
        assert "type" in doc

    def test_dump_not_created_on_error(self, tmp_path):
        f = _write_pss(tmp_path, "bad.pss",
                        "struct S { UnknownType x; };")
        ast_out = str(tmp_path / "ast.json")
        rc, _, _ = _run(["--dump-ast", ast_out, f])
        assert rc == 1
        assert not os.path.isfile(ast_out)


# -- --quiet ----------------------------------------------------------------

class TestQuiet:
    def test_quiet_suppresses_output(self, tmp_path):
        f = _write_pss(tmp_path, "ok.pss", "struct S { int x; };")
        rc, err, _ = _run(["--quiet", f])
        assert rc == 0
        assert err == ""


# -- usage errors -----------------------------------------------------------

class TestUsageErrors:
    def test_missing_file(self):
        rc, err, _ = _run(["/no/such/file.pss"])
        assert rc == 2
        assert "not found" in err

    def test_no_files(self):
        rc, err, _ = _run([])
        assert rc == 2

    def test_parse_subcommand_rejected(self, tmp_path):
        f = _write_pss(tmp_path, "ok.pss", "struct S { int x; };")
        rc, err, _ = _run(["parse", f])
        assert rc == 2
        assert "no longer required" in err
