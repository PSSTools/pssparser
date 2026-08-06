"""Compile-time elaboration through the CLI, over several files.

The parser-level tests drive ``Parser`` directly.  These go through the
command line, because that is how a build feeds a multi-file model, and
because the outcome that matters most is the *exit status*: the defect these
cover reported "0 errors" and exited 0 while dropping every gated declaration.
"""
from io import StringIO

from pssparser.cli.app import main as cli_main


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def _run(argv):
    import sys
    old_err, old_out = sys.stderr, sys.stdout
    err_buf, out_buf = StringIO(), StringIO()
    sys.stderr, sys.stdout = err_buf, out_buf
    try:
        rc = cli_main(argv)
    except SystemExit as e:
        rc = e.code if e.code is not None else 0
    finally:
        sys.stderr, sys.stdout = old_err, old_out
    return rc, err_buf.getvalue(), out_buf.getvalue()


CFG = "package cfg_pkg { static const bool FLAG = %s; }"

COMP = "component C { }"

GATED = """
import cfg_pkg::*;
extend component C {
    compile if (cfg_pkg::FLAG) {
        target function int gated() { return 1; }
    }
}
"""

CALLER = """
extend component C {
    target function int probe() { return gated(); }
}
"""


def test_gated_model_across_files_is_clean(tmp_path):
    """The whole point: gate in one file, call from another, exit 0."""
    files = [
        _write(tmp_path, "a_cfg.pss", CFG % "true"),
        _write(tmp_path, "b_comp.pss", COMP),
        _write(tmp_path, "c_gated.pss", GATED),
        _write(tmp_path, "d_caller.pss", CALLER),
    ]
    rc, err, _ = _run(files)
    assert rc == 0, err
    assert "0 errors" in err


def test_disabled_gate_reports_the_dangling_call(tmp_path):
    """With the gate off the caller is broken, and that must not exit 0."""
    files = [
        _write(tmp_path, "a_cfg.pss", CFG % "false"),
        _write(tmp_path, "b_comp.pss", COMP),
        _write(tmp_path, "c_gated.pss", GATED),
        _write(tmp_path, "d_caller.pss", CALLER),
    ]
    rc, err, _ = _run(files)
    assert rc != 0
    assert "gated" in err


def test_failing_compile_assert_is_located(tmp_path):
    """A failed assert names its own file, line and column."""
    files = [
        _write(tmp_path, "a_cfg.pss", CFG % "false"),
        _write(tmp_path, "b_assert.pss",
               "import cfg_pkg::*;\n"
               "component C {\n"
               "    compile assert(cfg_pkg::FLAG, \"this tree needs FLAG set\");\n"
               "}\n"),
    ]
    rc, err, _ = _run(files)
    assert rc != 0
    assert "compile assert failed: this tree needs FLAG set" in err
    assert "b_assert.pss:3:" in err


def test_forward_reference_names_the_offending_condition(tmp_path):
    """Order matters (PSS 3.1 19.1.2), so the diagnostic has to say what and
    where -- silently reading the condition as false is the original defect."""
    files = [
        _write(tmp_path, "a_model.pss",
               "import cfg_pkg::*;\n"
               "compile if (cfg_pkg::FLAG) {\n"
               "    component C { }\n"
               "}\n"),
        _write(tmp_path, "b_cfg.pss", CFG % "true"),
    ]
    rc, err, _ = _run(files)
    assert rc != 0
    assert "cannot be evaluated at compile time" in err
    assert "cfg_pkg::FLAG" in err
    assert "a_model.pss:2:" in err
