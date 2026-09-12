"""Tests for the ``-Werror`` family and ``--no-warnings`` (D7).

One test per row of the acceptance table in
``docs/design/cli-diagnostics-and-stats-plan.md`` (Phase 3, D7), driven
through ``cmd_parse`` with captured streams, plus unit coverage of the
policy object and the argparse surface that builds it.
"""
import json
from io import StringIO

import pytest

from pssparser.cli.app import _build_parser
from pssparser.cli.commands import cmd_parse, _apply_warning_policy
from pssparser.cli.diagnostics import (
    Diagnostic,
    DiagnosticCollection,
    WarningPolicy,
)


# A model whose only diagnostic is the PSS104 `compile if` brace warning.
WARN_SRC = """const int X = 1;
component C {
    compile if (X == 1)
        action A { int a; }
}
"""


@pytest.fixture
def warn_file(tmp_path):
    p = tmp_path / "warn.pss"
    p.write_text(WARN_SRC)
    return str(p)


def _run(files, **kw):
    """Run ``cmd_parse`` and return ``(rc, stdout, stderr)``."""
    out, err = StringIO(), StringIO()
    rc = cmd_parse(files if isinstance(files, list) else [files],
                   stdout=out, stderr=err, **kw)
    return rc, out.getvalue(), err.getvalue()


def _policy(argv):
    """Build the policy the CLI would build for *argv* (minus the file)."""
    args = _build_parser().parse_args(argv)
    policy = args.warning_policy or WarningPolicy()
    policy.no_warnings = args.no_warnings
    return policy


# -- the acceptance table --------------------------------------------------

class TestAcceptanceTable:
    def test_default_reports_a_warning(self, warn_file):
        rc, _, err = _run(warn_file)
        assert rc == 0
        assert "warning:" in err
        assert "1 warning in 1 file" in err

    def test_werror_promotes_all(self, warn_file):
        rc, _, err = _run(warn_file, warning_policy=_policy(["-Werror"]))
        assert rc == 1
        assert "error: 'compile if' branch" in err
        assert "[-Werror]" in err
        assert "1 error in 1 file" in err

    def test_werror_by_code_promotes(self, warn_file):
        rc, _, err = _run(warn_file, warning_policy=_policy(["-Werror=PSS104"]))
        assert rc == 1
        assert "[-Werror=PSS104]" in err
        assert "1 error in 1 file" in err

    def test_wno_error_exempts_from_blanket_werror(self, warn_file):
        rc, _, err = _run(
            warn_file,
            warning_policy=_policy(["-Werror", "-Wno-error=PSS104"]),
        )
        assert rc == 0
        assert "warning:" in err
        assert "-Werror" not in err
        assert "1 warning in 1 file" in err

    def test_no_warnings_suppresses(self, warn_file):
        rc, _, err = _run(warn_file, warning_policy=_policy(["--no-warnings"]))
        assert rc == 0
        assert "compile if" not in err
        assert "0 errors in 1 file" in err

    def test_suppression_beats_promotion(self, warn_file):
        rc, _, err = _run(
            warn_file, warning_policy=_policy(["--no-warnings", "-Werror"])
        )
        assert rc == 0
        assert "compile if" not in err
        assert "0 errors in 1 file" in err

    def test_json_carries_original_severity(self, warn_file):
        rc, out, _ = _run(
            warn_file, use_json=True, warning_policy=_policy(["-Werror"])
        )
        assert rc == 1
        doc = json.loads(out)
        (entry,) = doc["diagnostics"]
        assert entry["severity"] == "error"
        assert entry["original_severity"] == "warning"
        assert doc["summary"]["errors"] == 1
        assert doc["summary"]["warnings"] == 0
        # The flag spelling is a human-rendering concern only.
        assert "werror_flag" not in entry


class TestJsonUnpromoted:
    def test_no_original_severity_by_default(self, warn_file):
        rc, out, _ = _run(warn_file, use_json=True)
        assert rc == 0
        (entry,) = json.loads(out)["diagnostics"]
        assert "original_severity" not in entry


# -- argparse surface ------------------------------------------------------

class TestArgumentParsing:
    def test_bare_werror(self):
        p = _policy(["-Werror"])
        assert p.error_all and not p.error_codes

    def test_werror_does_not_swallow_the_next_argument(self):
        """``-Werror x.pss`` must leave ``x.pss`` as a file, not an option arg."""
        args = _build_parser().parse_args(["-Werror", "x.pss"])
        assert args.files == ["x.pss"]

    def test_repeated_codes_accumulate(self):
        p = _policy(["-Werror=PSS104", "-Werror=PSS020", "-Wno-error=PSS001"])
        assert p.error_codes == {"PSS104", "PSS020"}
        assert p.no_error_codes == {"PSS001"}
        assert not p.error_all

    def test_unrecognised_w_option_is_a_usage_error(self):
        with pytest.raises(SystemExit) as exc:
            _build_parser().parse_args(["-Wbogus"])
        assert exc.value.code == 2

    def test_default_policy_is_inert(self):
        assert _policy([]).is_default


# -- the policy pass in isolation ------------------------------------------

def _warning(code=None, severity="warning"):
    return Diagnostic(
        file="f.pss", line=1, col=1, severity=severity,
        message="something", code=code,
    )


class TestPolicyPass:
    def test_default_policy_leaves_the_collection_alone(self):
        coll = DiagnosticCollection()
        d = _warning("PSS104")
        coll.add(d)
        _apply_warning_policy(coll, WarningPolicy())
        assert coll.diagnostics[0].severity == "warning"
        assert coll.diagnostics[0].original_severity is None

    def test_errors_are_never_touched(self):
        coll = DiagnosticCollection()
        coll.add(_warning("PSS001", severity="error"))
        _apply_warning_policy(coll, WarningPolicy(error_all=True))
        d = coll.diagnostics[0]
        assert d.severity == "error"
        assert d.original_severity is None
        assert d.werror_flag is None

    def test_info_and_hint_survive_no_warnings(self):
        """``--no-warnings`` means warnings, not everything non-error."""
        coll = DiagnosticCollection()
        coll.add(_warning("PSS001", severity="info"))
        coll.add(_warning("PSS002", severity="hint"))
        coll.add(_warning("PSS104"))
        _apply_warning_policy(coll, WarningPolicy(no_warnings=True))
        assert [d.severity for d in coll.diagnostics] == ["info", "hint"]

    def test_uncoded_warning_is_promoted_by_blanket_werror_only(self):
        """A marker with no code cannot be named, so only ``-Werror`` hits it."""
        coll = DiagnosticCollection()
        coll.add(_warning(None))
        _apply_warning_policy(coll, WarningPolicy(error_codes={"PSS104"}))
        assert coll.diagnostics[0].severity == "warning"

        coll = DiagnosticCollection()
        coll.add(_warning(None))
        _apply_warning_policy(coll, WarningPolicy(error_all=True))
        assert coll.diagnostics[0].severity == "error"

    def test_counts_and_has_errors_move_with_promotion(self):
        coll = DiagnosticCollection()
        coll.add(_warning("PSS104"))
        assert coll.warning_count == 1 and not coll.has_errors
        _apply_warning_policy(coll, WarningPolicy(error_all=True))
        assert coll.error_count == 1
        assert coll.warning_count == 0
        assert coll.has_errors
