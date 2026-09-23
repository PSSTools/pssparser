"""CLI-level tests for the configuration layer.

What a config file actually *does* to a run: which checkers execute, what
severity their diagnostics carry, what the exit code becomes, and what
``--show-config`` / ``--describe-checker`` print.

``tests/python/cli/test_config.py`` covers discovery, parsing, and precedence
in isolation; this file is the end-to-end half.
"""
from __future__ import annotations

import io
import sys

import pytest

from pssparser.checkers import CheckerBase, MarkerDef
from pssparser.cli.app import main

# A source with exactly one naming violation and no parse errors, so a test
# can tell "the checker did not run" from "the file was rejected".
CLEAN_SRC = "component pss_top {\n}\n"
BAD_NAME_SRC = "component pss_top {\n  action write_data {\n  }\n}\n"
BROKEN_SRC = "component pss_top {\n"


def run(argv):
    """Run main() with captured streams; return (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A tmp directory that is the CWD, with a .git so the search stops."""
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def src(project, text=BAD_NAME_SRC, name="demo.pss"):
    p = project / name
    p.write_text(text)
    return str(p)


def config(project, text, name=".pssparser.toml"):
    p = project / name
    p.write_text(text)
    return str(p)


# ----------------------------------------------------------------------
# A checker to configure
# ----------------------------------------------------------------------


class _Configurable(CheckerBase):
    """Emits one marker per action, with a message built from its options."""

    name = "configurable"
    description = "Test checker with options"
    runs_without_link = True
    marker_defs = [
        MarkerDef(
            id="TST001",
            severity="warning",
            summary="A configurable finding",
            detail="Exists so the config layer has something to steer.",
        ),
    ]
    options_schema = {
        "label": {"type": "string", "default": "default-label",
                  "help": "Text put in the message."},
        "limit": {"type": "int", "default": 1, "help": "An integer option."},
        "loud": {"type": "bool", "default": False, "help": "A boolean."},
        "names": {"type": "string-list", "default": [], "help": "A list."},
        "mode": {"type": "string", "default": "a", "choices": ["a", "b"],
                 "help": "A constrained string."},
    }

    #: Last resolved table, so a test can assert on what configure() saw
    #: without needing the diagnostic to carry every value.
    seen: dict = {}

    def configure(self, options):
        super().configure(options)
        type(self).seen = dict(options)

    def check(self, context):
        for scope in context.global_scopes:
            filename = context.file_map.get(scope.getFileid(), "")
            context.add_marker(
                code="TST001", file=filename, line=1, col=1,
                message=f"label={self.options['label']}",
            )


class _Optionless(CheckerBase):
    name = "optionless"
    description = "Test checker with no options at all"
    runs_without_link = True
    marker_defs = [
        MarkerDef(id="TST002", severity="warning", summary="Optionless finding",
                  detail="Exists to prove configure() stays optional."),
    ]

    def check(self, context):
        for scope in context.global_scopes:
            filename = context.file_map.get(scope.getFileid(), "")
            context.add_marker(
                code="TST002", file=filename, line=1, col=1,
                message="optionless ran",
            )


_SPEC = f"{__name__}:_Configurable"
_SPEC_OPTIONLESS = f"{__name__}:_Optionless"


@pytest.fixture(autouse=True)
def _reset_seen():
    _Configurable.seen = {}
    yield
    _Configurable.seen = {}


# ----------------------------------------------------------------------
# The config file reaches the run
# ----------------------------------------------------------------------


def test_a_config_file_selects_checkers(project):
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\nselect = ["configurable"]\n')
    rc, _, err = run([f])
    assert "TST001" in err
    assert rc == 0


def test_no_config_ignores_the_file(project):
    """The escape hatch has to be complete, not partial."""
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\nselect = ["configurable"]\n')
    rc, _, err = run(["--no-config", f])
    assert "TST001" not in err
    assert rc == 0


def test_explicit_config_is_used(project):
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\nselect = ["configurable"]\n', "ci.toml")
    rc, _, err = run(["--config", "ci.toml", f])
    assert "TST001" in err


def test_a_missing_explicit_config_is_exit_2(project):
    """A typo in a config path must not quietly change which rules run."""
    f = src(project)
    rc, _, err = run(["--config", "nope.toml", f])
    assert rc == 2
    assert "not found" in err
    assert "nope.toml" in err


def test_an_unparseable_explicit_config_is_exit_2(project):
    f = src(project)
    config(project, "this is not [ toml\n", "bad.toml")
    rc, _, err = run(["--config", "bad.toml", f])
    assert rc == 2
    assert "invalid TOML" in err


def test_an_unknown_key_is_exit_2_with_a_suggestion(project):
    f = src(project)
    config(project, 'selct = ["core"]\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "did you mean 'select'" in err


def test_select_naming_an_uninstalled_checker_is_exit_2(project):
    """Fail-fast, matching --checker.

    A rule silently not running is the failure mode the whole feature
    exists to prevent, so a config naming a missing checker stops the run
    rather than warning into a stream that nobody reads.
    """
    f = src(project)
    config(project, 'select = ["not-installed"]\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "not installed" in err


def test_the_config_is_validated_before_the_file_is_parsed(project):
    """A bad config must not cost a full parse first.

    The source here is syntactically broken; if validation ran after
    parsing, the parse errors would arrive before (or instead of) the
    config error.
    """
    f = src(project, BROKEN_SRC)
    config(project, 'select = ["not-installed"]\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "not installed" in err
    assert "unexpected" not in err


def test_load_from_a_config_file_is_attributed(project):
    """An error about a spec the user is not looking at must say where it
    came from."""
    f = src(project)
    config(project, 'load = ["no.such.module:Nope"]\n')
    rc, _, err = run([f])
    assert rc == 2
    assert ".pssparser.toml" in err


def test_load_from_the_command_line_is_not_attributed(project):
    """They just typed it; naming "command line" back at them is noise."""
    f = src(project)
    rc, _, err = run(["--load-checker", "no.such.module:Nope", f])
    assert rc == 2
    assert "command line" not in err


# ----------------------------------------------------------------------
# Severity overrides (C3)
# ----------------------------------------------------------------------


def test_severity_off_removes_the_diagnostic(project):
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        '[severity]\nTST001 = "off"\n',
    )
    rc, _, err = run([f])
    assert "TST001" not in err
    assert rc == 0


def test_severity_error_changes_the_exit_code(project):
    """A warning promoted by config is a real error, exit code included."""
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        '[severity]\nTST001 = "error"\n',
    )
    rc, _, err = run([f])
    assert "error:" in err
    assert rc == 1


def test_severity_off_changes_the_exit_code_from_1_to_0(project):
    f = src(project)
    cfg = (
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        '[severity]\nTST001 = "%s"\n'
    )
    config(project, cfg % "error")
    assert run([f])[0] == 1
    config(project, cfg % "off")
    assert run([f])[0] == 0


def test_severity_runs_before_the_warning_policy(project):
    """Order matters in both directions.

    -Werror applied first would promote a diagnostic the config had already
    turned off, so an "off" rule would still fail CI.
    """
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        '[severity]\nTST001 = "off"\n',
    )
    rc, _, err = run(["-Werror", f])
    assert "TST001" not in err
    assert rc == 0


def test_severity_does_not_rescue_a_failed_parse(project):
    """force_rc=1 still wins.

    A config that turns off whatever the parser complained about must not
    produce a successful run for a file that did not compile -- which is
    also why downgrading a core error is refused at load time.
    """
    f = src(project, BROKEN_SRC)
    config(project, f'load = ["{_SPEC}"]\n')
    rc, _, _ = run([f])
    assert rc == 1


def test_downgrading_a_core_error_is_a_config_error(project):
    f = src(project)
    config(project, '[severity]\nPSS002 = "warning"\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "core error" in err


def test_an_unknown_marker_in_severity_is_exit_2(project):
    f = src(project)
    config(project, '[severity]\nNOSUCH = "off"\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "unknown marker" in err


# ----------------------------------------------------------------------
# Per-checker options (C4)
# ----------------------------------------------------------------------


def test_options_reach_configure_with_defaults_filled_in(project):
    """configure() always sees a complete table.

    An implementation should never need `.get(key, default)`, because the
    default already lives in the schema and duplicating it is how the two
    drift apart.
    """
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        '[checker.configurable]\nlabel = "custom"\n',
    )
    rc, _, err = run([f])
    assert "label=custom" in err
    assert _Configurable.seen == {
        "label": "custom", "limit": 1, "loud": False,
        "names": [], "mode": "a",
    }


def test_declared_defaults_apply_when_nothing_is_set(project):
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\nselect = ["configurable"]\n')
    run([f])
    assert _Configurable.seen["label"] == "default-label"


def test_every_option_type_round_trips(project):
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        "[checker.configurable]\n"
        'label = "x"\nlimit = 7\nloud = true\nnames = ["a", "b"]\nmode = "b"\n',
    )
    run([f])
    assert _Configurable.seen == {
        "label": "x", "limit": 7, "loud": True,
        "names": ["a", "b"], "mode": "b",
    }


def test_unknown_option_is_exit_2_with_a_suggestion(project):
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\n[checker.configurable]\nlabl = "x"\n',
    )
    rc, _, err = run([f])
    assert rc == 2
    assert "did you mean 'label'" in err


def test_wrong_option_type_is_exit_2(project):
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\n[checker.configurable]\nlimit = "x"\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "must be of type int" in err


def test_a_boolean_is_not_an_integer(project):
    """``bool`` subclasses ``int``; without an explicit guard ``limit = true``
    would be accepted and then behave as 1."""
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\n[checker.configurable]\nlimit = true\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "must be of type int" in err


def test_a_value_outside_choices_is_exit_2(project):
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\n[checker.configurable]\nmode = "z"\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "must be one of" in err


def test_a_non_string_in_a_string_list_is_exit_2(project):
    f = src(project)
    config(project, f'load = ["{_SPEC}"]\n[checker.configurable]\nnames = [1]\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "string-list" in err


def test_options_for_an_optionless_checker_is_exit_2(project):
    """Silently ignoring the table is the failure this rejects.

    A checker that declares no schema accepts nothing; an ignored
    ``[checker.x]`` is a rule the user believes is configured and is not.
    """
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC_OPTIONLESS}"]\n[checker.optionless]\nfoo = 1\n',
    )
    rc, _, err = run([f])
    assert rc == 2
    assert "accepts no options" in err


def test_a_checker_without_configure_still_runs(project):
    """The hook is optional; checkers written before options existed work."""
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC_OPTIONLESS}"]\nselect = ["optionless"]\n',
    )
    rc, _, err = run([f])
    assert "optionless ran" in err
    assert rc == 0


def test_options_are_validated_before_the_file_is_parsed(project):
    f = src(project, BROKEN_SRC)
    config(project, f'load = ["{_SPEC}"]\n[checker.configurable]\nmode = "z"\n')
    rc, _, err = run([f])
    assert rc == 2
    assert "must be one of" in err


def test_one_run_cannot_mutate_the_next_runs_defaults(project):
    """A mutable default copied per instance, not shared with the schema."""
    f = src(project)
    config(
        project,
        f'load = ["{_SPEC}"]\nselect = ["configurable"]\n'
        '[checker.configurable]\nnames = ["a"]\n',
    )
    run([f])
    config(project, f'load = ["{_SPEC}"]\nselect = ["configurable"]\n')
    run([f])
    assert _Configurable.seen["names"] == []
    assert _Configurable.options_schema["names"]["default"] == []


# ----------------------------------------------------------------------
# --show-config (C6)
# ----------------------------------------------------------------------


def test_show_config_exits_0_without_source_files(project):
    """It is a query flag: answering "what is configured?" must not require
    something to run it against."""
    config(project, 'select = ["core"]\n')
    rc, out, _ = run(["--show-config"])
    assert rc == 0
    assert ".pssparser.toml" in out


def test_show_config_reports_cli_overrides(project):
    config(project, 'select = ["core"]\n')
    rc, out, _ = run(["--show-config", "--checker", "core"])
    assert rc == 0
    assert "Overridden by command-line flags:" in out
    assert "select" in out


def test_show_config_with_no_file_says_so(project):
    rc, out, _ = run(["--show-config"])
    assert rc == 0
    assert "none found" in out


def test_show_config_is_stable_across_runs(project):
    """It is the cheapest golden of the precedence stack, so it has to be
    byte-reproducible."""
    config(project, 'select = ["core"]\n[severity]\nPSS001 = "off"\n')
    assert run(["--show-config"])[1] == run(["--show-config"])[1]


# ----------------------------------------------------------------------
# --describe-checker (C5)
# ----------------------------------------------------------------------


def test_describe_checker_shows_markers_and_options(project):
    rc, out, _ = run(["--load-checker", _SPEC, "--describe-checker", "configurable"])
    assert rc == 0
    assert "TST001" in out
    assert "label" in out and "default: 'default-label'" in out
    assert "one of: a, b" in out
    assert "[checker.configurable]" in out


def test_describe_checker_for_an_optionless_checker(project):
    rc, out, _ = run(
        ["--load-checker", _SPEC_OPTIONLESS, "--describe-checker", "optionless"]
    )
    assert rc == 0
    assert "takes no configuration" in out


def test_describe_checker_unknown_name_is_exit_2(project):
    rc, _, err = run(["--describe-checker", "nosuch"])
    assert rc == 2
    assert "--list-checkers" in err


def test_describe_checker_typo_gets_a_suggestion(project):
    rc, _, err = run(["--describe-checker", "cores"])
    assert rc == 2
    assert "did you mean 'core'" in err


def test_describe_checker_needs_no_source_files(project):
    assert run(["--describe-checker", "core"])[0] == 0
