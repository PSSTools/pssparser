"""E-4: --max-errors is a real cap (defect D9), not just an ignored CLI flag.

See docs/design/error-testing-plan.md §5. The reachability corpus case lives
under data/volume/ (queried by test_marker_ids.py's syntax-band tests); this
module covers the cap's actual counting semantics, which the corpus DSL
(single-ID, "at least one match" assertions) is not built to express.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect  # noqa: E402

from pssparser.cli.commands import cmd_parse  # noqa: E402


def _many_defects(n: int) -> str:
    return "\n".join("struct S%d { int ; }" % i for i in range(n))


def test_cap_stops_reporting_and_emits_pss029_last():
    _root, markers = parse_collect(_many_defects(30), max_errors=20)
    errors = [m for m in markers if m.get("severity") == "error"]
    assert len(errors) == 21
    assert [m.get("code") for m in errors].count("PSS029") == 1
    assert errors[-1].get("code") == "PSS029"


def test_max_errors_zero_is_unlimited():
    _root, markers = parse_collect(_many_defects(30), max_errors=0)
    errors = [m for m in markers if m.get("severity") == "error"]
    assert len(errors) == 30
    assert "PSS029" not in [m.get("code") for m in errors]


def test_max_errors_one():
    _root, markers = parse_collect(_many_defects(30), max_errors=1)
    errors = [m for m in markers if m.get("severity") == "error"]
    assert len(errors) == 2
    assert errors[-1].get("code") == "PSS029"


def test_cap_does_not_fire_on_a_clean_file():
    _root, markers = parse_collect(
        "component pss_top {\n    action A {}\n}\n", max_errors=1
    )
    codes = [m.get("code") for m in markers]
    assert "PSS029" not in codes


def test_cli_max_errors_changes_reported_error_count(tmp_path):
    f = tmp_path / "many.pss"
    f.write_text(_many_defects(30) + "\n")

    def _run(max_errors):
        out = io.StringIO()
        code = cmd_parse(
            files=[str(f)],
            use_json=True,
            max_errors=max_errors,
            stdout=out,
            stderr=io.StringIO(),
        )
        assert code == 1
        import json
        return json.loads(out.getvalue())

    capped = _run(5)
    uncapped = _run(0)

    assert len(capped["diagnostics"]) == 6
    assert len(uncapped["diagnostics"]) == 30
    assert len(capped["diagnostics"]) < len(uncapped["diagnostics"])
