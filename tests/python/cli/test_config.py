"""Unit tests for configuration discovery, parsing, validation, and precedence.

These exercise ``pssparser.cli.config`` directly.  The CLI-level behaviour --
``--config``, ``--no-config``, ``--show-config``, and what a config file does
to a real run -- lives in ``test_config_cli.py``.

Every test that relies on the upward search chdirs into a tmp tree, because
discovery deliberately starts at the working directory rather than at a
source file's directory.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from pssparser.cli import config as cfg_mod
from pssparser.cli.config import (
    ConfigError,
    discover_config_files,
    format_show_config,
    load_config_file,
    resolve,
)


def args(**kw):
    """Build an argparse-like namespace with the CLI defaults."""
    ns = argparse.Namespace(
        config=None,
        no_config=False,
        checkers=None,
        no_checkers=None,
        load_checkers=None,
        warning_policy=None,
        no_warnings=False,
        no_extensions=False,
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ----------------------------------------------------------------------
# The TOML shim (C7)
# ----------------------------------------------------------------------


def test_a_toml_parser_is_available():
    """The shim resolved to something on this interpreter.

    3.11+ gets stdlib ``tomllib``; 3.10 needs ``tomli`` from
    ``install_requires``.  A None here means the dependency is missing.
    """
    assert cfg_mod.tomllib is not None


def test_config_is_the_only_toml_import_site():
    """One shim, one place.

    A bare ``import tomllib`` elsewhere works on 3.11 and fails on 3.10 --
    the kind of bug that only shows up on the interpreter nobody develops
    on.  Keeping the fallback in one module is what makes a second site
    impossible to write carelessly; ``profiling/corpus.py`` imports the
    resolved name from here rather than repeating the try/except.
    """
    import re

    # A *bare* import is the thing being banned; `from ...config import
    # tomllib` is the sanctioned way to reach the resolved name.
    bare = re.compile(r"^\s*import tomll?i(b)?\b", re.MULTILINE)
    root = Path(__file__).resolve().parents[3] / "python" / "pssparser"
    offenders = [
        str(py.relative_to(root))
        for py in root.rglob("*.py")
        if py.name != "config.py" and bare.search(py.read_text())
    ]
    assert offenders == []


# ----------------------------------------------------------------------
# Discovery (C1)
# ----------------------------------------------------------------------


def test_finds_a_config_in_the_current_directory(tmp_path, monkeypatch):
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    monkeypatch.chdir(tmp_path)
    found = discover_config_files()
    assert [p.name for p in found] == [".pssparser.toml"]


def test_search_walks_upward(tmp_path, monkeypatch):
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    assert [p.parent for p in discover_config_files()] == [tmp_path]


def test_search_stops_at_a_git_directory(tmp_path, monkeypatch):
    """A config above a repository root belongs to some other project.

    Without this stop, running pssparser inside a checkout that happens to
    live under a directory with a stray ``.pssparser.toml`` would silently
    adopt it.
    """
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.chdir(repo)
    assert discover_config_files() == []


def test_the_git_directory_itself_may_hold_the_config(tmp_path, monkeypatch):
    """Stopping *at* the repo root still means looking in it."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    write(repo / ".pssparser.toml", 'select = ["core"]\n')
    monkeypatch.chdir(repo)
    assert [p.parent for p in discover_config_files()] == [repo]


def test_a_pyproject_without_our_table_does_not_stop_the_search(tmp_path, monkeypatch):
    """Almost every Python project has a pyproject.toml.

    If a bare one halted the walk, a repo-root config would be unreachable
    from any package subdirectory that happens to have its own.
    """
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    sub = tmp_path / "sub"
    write(sub / "pyproject.toml", '[project]\nname = "unrelated"\n')
    monkeypatch.chdir(sub)
    assert [p.parent for p in discover_config_files()] == [tmp_path]


def test_an_unparseable_pyproject_is_stepped_over(tmp_path, monkeypatch):
    """Someone else's broken file must not fail our run.

    A ``pyproject.toml`` belongs to the whole project; pssparser is not
    entitled to refuse to start because another tool's section has a syntax
    error in it.  ``--config`` is where a parse error *is* reported.
    """
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    sub = tmp_path / "sub"
    write(sub / "pyproject.toml", "this is not [ valid toml\n")
    monkeypatch.chdir(sub)
    assert [p.parent for p in discover_config_files()] == [tmp_path]


def test_pyproject_with_our_table_does_stop_the_search(tmp_path, monkeypatch):
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    sub = tmp_path / "sub"
    write(sub / "pyproject.toml", '[tool.pssparser]\nselect = ["core"]\n')
    monkeypatch.chdir(sub)
    assert [p.parent for p in discover_config_files()] == [sub]


def test_both_files_in_one_directory_are_ordered_pyproject_first(tmp_path, monkeypatch):
    """Order is precedence: the dedicated file is the more specific answer."""
    write(tmp_path / "pyproject.toml", '[tool.pssparser]\nselect = ["core"]\n')
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    monkeypatch.chdir(tmp_path)
    assert [p.name for p in discover_config_files()] == [
        "pyproject.toml", ".pssparser.toml",
    ]


def test_nothing_found_is_not_an_error(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    assert discover_config_files() == []


def test_source_files_in_two_directories_still_resolve_one_config(tmp_path, monkeypatch):
    """Discovery keys off CWD, not off the inputs.

    ``pssparser a/x.pss b/y.pss`` must not silently apply two different
    configurations to two halves of one run.
    """
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    write(tmp_path / "a" / ".pssparser.toml", 'select = ["nope-a"]\n')
    write(tmp_path / "b" / ".pssparser.toml", 'select = ["nope-b"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    assert cfg.select == ["core"]


# ----------------------------------------------------------------------
# Parsing and schema validation (C2)
# ----------------------------------------------------------------------


def test_pyproject_table_is_unwrapped(tmp_path):
    p = write(tmp_path / "pyproject.toml", '[tool.pssparser]\nselect = ["core"]\n')
    table, display = load_config_file(p)
    assert table == {"select": ["core"]}
    assert display.endswith("[tool.pssparser]")


def test_unknown_key_is_rejected_with_a_suggestion(tmp_path):
    p = write(tmp_path / ".pssparser.toml", 'selct = ["core"]\n')
    with pytest.raises(ConfigError, match="did you mean 'select'"):
        load_config_file(p)


def test_unknown_key_with_no_near_match_lists_the_known_keys(tmp_path):
    """Do not invent a suggestion for a word nothing resembles.

    A bad guess is worse than none: it sends the user to rewrite a line that
    was never going to be the right line.
    """
    p = write(tmp_path / ".pssparser.toml", 'zzzquux = 1\n')
    with pytest.raises(ConfigError) as exc:
        load_config_file(p)
    assert "did you mean" not in str(exc.value)
    assert "known keys:" in str(exc.value)


def test_the_plural_checkers_trap_gets_its_own_explanation(tmp_path):
    """'checkers' is the first thing everyone types.

    A bare "did you mean 'checker'?" would send them to the per-checker
    options table, which is not what they wanted either.
    """
    p = write(tmp_path / ".pssparser.toml", 'checkers = ["core"]\n')
    with pytest.raises(ConfigError) as exc:
        load_config_file(p)
    msg = str(exc.value)
    assert "select" in msg and "disable" in msg and "load" in msg
    assert "cannot coexist" in msg


def test_wrong_type_for_a_root_key(tmp_path):
    p = write(tmp_path / ".pssparser.toml", 'select = "core"\n')
    with pytest.raises(ConfigError, match="must be an array"):
        load_config_file(p)


def test_non_string_entry_in_a_string_array(tmp_path):
    p = write(tmp_path / ".pssparser.toml", "select = [1]\n")
    with pytest.raises(ConfigError, match="must be a string"):
        load_config_file(p)


def test_version_must_not_be_a_boolean(tmp_path):
    """``bool`` subclasses ``int``, so an int slot accepts ``true`` unless
    it is stopped explicitly."""
    p = write(tmp_path / ".pssparser.toml", "version = true\n")
    with pytest.raises(ConfigError, match="must be an integer"):
        load_config_file(p)


def test_a_future_schema_version_is_refused(tmp_path):
    p = write(tmp_path / ".pssparser.toml", "version = 99\n")
    with pytest.raises(ConfigError, match="understands version"):
        load_config_file(p)


def test_the_current_schema_version_is_accepted(tmp_path):
    p = write(
        tmp_path / ".pssparser.toml", f"version = {cfg_mod.SCHEMA_VERSION}\n"
    )
    table, _ = load_config_file(p)
    assert table["version"] == cfg_mod.SCHEMA_VERSION


def test_invalid_severity_value(tmp_path):
    p = write(tmp_path / ".pssparser.toml", '[severity]\nPSS001 = "loud"\n')
    with pytest.raises(ConfigError, match="must be one of"):
        load_config_file(p)


def test_severity_off_is_accepted(tmp_path):
    p = write(tmp_path / ".pssparser.toml", '[severity]\nPSS001 = "off"\n')
    table, _ = load_config_file(p)
    assert table["severity"]["PSS001"] == "off"


def test_unknown_warnings_key(tmp_path):
    p = write(tmp_path / ".pssparser.toml", "[warnings]\nerrors = true\n")
    with pytest.raises(ConfigError, match="did you mean 'error'"):
        load_config_file(p)


def test_warnings_error_accepts_bool_or_array(tmp_path):
    p = write(tmp_path / ".pssparser.toml", "[warnings]\nerror = true\n")
    assert load_config_file(p)[0]["warnings"]["error"] is True
    p = write(tmp_path / ".pssparser.toml", '[warnings]\nerror = ["PSS110"]\n')
    assert load_config_file(p)[0]["warnings"]["error"] == ["PSS110"]


def test_warnings_error_rejects_a_string(tmp_path):
    p = write(tmp_path / ".pssparser.toml", '[warnings]\nerror = "yes"\n')
    with pytest.raises(ConfigError, match="warnings.error"):
        load_config_file(p)


def test_unknown_extension_key(tmp_path):
    p = write(
        tmp_path / ".pssparser.toml", "[extensions.acme]\nenable = false\n"
    )
    with pytest.raises(ConfigError, match="did you mean 'enabled'"):
        load_config_file(p)


def test_checker_table_must_be_a_table(tmp_path):
    p = write(tmp_path / ".pssparser.toml", 'checker = "naming"\n')
    with pytest.raises(ConfigError, match="must be a table"):
        load_config_file(p)


def test_a_severity_entry_written_as_a_table_is_explained(tmp_path):
    """``[severity.PSS001]`` is a plausible typo for ``PSS001 = "off"``."""
    p = write(
        tmp_path / ".pssparser.toml", '[severity.PSS001]\nlevel = "off"\n'
    )
    with pytest.raises(ConfigError, match="plain values"):
        load_config_file(p)


def test_missing_explicit_config_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config_file(tmp_path / "nope.toml", required=True)


def test_unparseable_explicit_config_is_an_error(tmp_path):
    p = write(tmp_path / "bad.toml", "not [ valid\n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config_file(p, required=True)


def test_explicit_pyproject_without_our_table_is_an_error(tmp_path):
    """Naming a file explicitly means expecting it to configure something."""
    p = write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    with pytest.raises(ConfigError, match="no \\[tool.pssparser\\] table"):
        load_config_file(p, required=True)


def test_an_unparseable_dedicated_file_found_by_search_still_raises(tmp_path):
    """Unlike pyproject.toml, ``.pssparser.toml`` is ours alone.

    A syntax error in a file that exists only to configure pssparser is
    always the user's problem to fix, discovered or named.
    """
    p = write(tmp_path / ".pssparser.toml", "not [ valid\n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config_file(p)


# ----------------------------------------------------------------------
# Precedence (C1) -- one test per adjacent pair
# ----------------------------------------------------------------------


def test_pssparser_toml_beats_pyproject(tmp_path, monkeypatch):
    write(tmp_path / "pyproject.toml", '[tool.pssparser]\nselect = ["low"]\n')
    write(tmp_path / ".pssparser.toml", 'select = ["high"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    assert cfg.select == ["high"]
    assert cfg.provenance["select"] == ".pssparser.toml"


def test_explicit_config_replaces_discovery(tmp_path, monkeypatch):
    """--config is authoritative, not additive.

    A named file is the answer to "which rules run"; letting a stray
    ``.pssparser.toml`` two directories up keep contributing would defeat
    the point of naming one.
    """
    write(tmp_path / ".pssparser.toml", 'select = ["discovered"]\ndisable = ["d"]\n')
    explicit = write(tmp_path / "ci.toml", 'select = ["explicit"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args(config=str(explicit)))
    assert cfg.select == ["explicit"]
    assert cfg.disable == []


def test_cli_beats_the_config_file(tmp_path, monkeypatch):
    write(tmp_path / ".pssparser.toml", 'select = ["from-file"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args(checkers=["from-cli"]))
    assert cfg.select == ["from-cli"]
    assert cfg.provenance["select"] == "command line"
    assert "select" in cfg.overridden


def test_an_unused_flag_does_not_overwrite_the_file(tmp_path, monkeypatch):
    """The trap this whole layer has to avoid.

    ``--checker`` defaults to ``None``, not ``[]``; if the override tested
    for truth rather than for presence, every run without the flag would
    silently wipe a configured ``select``.
    """
    write(tmp_path / ".pssparser.toml", 'select = ["from-file"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    assert cfg.select == ["from-file"]
    assert cfg.overridden == []


def test_layers_merge_per_key_not_wholesale(tmp_path, monkeypatch):
    """A higher layer overrides the keys it sets and leaves the rest."""
    write(
        tmp_path / "pyproject.toml",
        '[tool.pssparser]\nselect = ["low"]\ndisable = ["kept"]\n',
    )
    write(tmp_path / ".pssparser.toml", 'select = ["high"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    assert cfg.select == ["high"]
    assert cfg.disable == ["kept"]
    assert cfg.provenance["disable"].startswith("pyproject.toml")


def test_severity_tables_merge_entry_by_entry(tmp_path, monkeypatch):
    """A narrow override must not discard the rest of the table."""
    write(
        tmp_path / "pyproject.toml",
        '[tool.pssparser.severity]\nPSS001 = "off"\nPSS002 = "off"\n',
    )
    write(tmp_path / ".pssparser.toml", '[severity]\nPSS002 = "error"\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    assert cfg.severity == {"PSS001": "off", "PSS002": "error"}
    assert cfg.provenance["severity.PSS001"].startswith("pyproject.toml")
    assert cfg.provenance["severity.PSS002"] == ".pssparser.toml"


def test_arrays_replace_rather_than_append(tmp_path, monkeypatch):
    """Otherwise a lower layer's entry could never be removed."""
    write(tmp_path / "pyproject.toml", '[tool.pssparser]\nselect = ["a", "b"]\n')
    write(tmp_path / ".pssparser.toml", 'select = ["b"]\n')
    monkeypatch.chdir(tmp_path)
    assert resolve(args()).select == ["b"]


def test_no_config_ignores_everything(tmp_path, monkeypatch):
    write(tmp_path / ".pssparser.toml", 'select = ["from-file"]\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args(no_config=True))
    assert cfg.select is None
    assert cfg.is_empty


def test_no_config_with_an_explicit_config_still_ignores_it(tmp_path, monkeypatch):
    explicit = write(tmp_path / "ci.toml", 'select = ["explicit"]\n')
    monkeypatch.chdir(tmp_path)
    assert resolve(args(config=str(explicit), no_config=True)).is_empty


def test_warning_flags_override_the_file(tmp_path, monkeypatch):
    from pssparser.cli.diagnostics import WarningPolicy

    write(tmp_path / ".pssparser.toml", "[warnings]\nerror = false\n")
    monkeypatch.chdir(tmp_path)
    policy = WarningPolicy(error_all=True)
    cfg = resolve(args(warning_policy=policy))
    assert cfg.warnings_error_all is True
    assert "warnings.error" in cfg.overridden


def test_warning_settings_reach_the_policy(tmp_path, monkeypatch):
    from pssparser.cli.diagnostics import WarningPolicy

    write(
        tmp_path / ".pssparser.toml",
        '[warnings]\nerror = ["PSS110"]\nno-error = ["PSS111"]\nnone = true\n',
    )
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    policy = WarningPolicy()
    cfg_mod.to_warning_policy(cfg, policy)
    assert policy.error_codes == {"PSS110"}
    assert policy.no_error_codes == {"PSS111"}
    assert policy.no_warnings is True
    assert policy.error_all is False


# ----------------------------------------------------------------------
# Registry-dependent validation (C2 fail-fast, C3 core-error guard)
# ----------------------------------------------------------------------


@pytest.fixture
def manager():
    from pssparser.checkers import CheckerManager

    m = CheckerManager()
    m.discover(load_extensions=False)
    return m


def test_select_naming_an_uninstalled_checker_fails_fast(manager):
    cfg = resolve(args(checkers=["not-installed"]))
    with pytest.raises(ConfigError, match="not installed"):
        cfg_mod.validate_against_registry(cfg, manager)


def test_select_typo_gets_a_suggestion(manager):
    cfg = resolve(args(checkers=["cores"]))
    with pytest.raises(ConfigError, match="did you mean 'core'"):
        cfg_mod.validate_against_registry(cfg, manager)


def test_severity_naming_an_unknown_marker_fails_fast(tmp_path, monkeypatch, manager):
    write(tmp_path / ".pssparser.toml", '[severity]\nNOPE999 = "off"\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    with pytest.raises(ConfigError, match="unknown marker"):
        cfg_mod.validate_against_registry(cfg, manager)


def test_a_core_error_cannot_be_downgraded(tmp_path, monkeypatch, manager):
    """The restriction that keeps a forced exit code honest.

    The parse- and link-failure paths return rc=1 with no linked AST.  If a
    config could turn those diagnostics off, the run would report success
    for having compiled nothing.
    """
    core_error = next(
        m["id"] for m in manager.list_all_markers()
        if m["checker"] == "core" and m["severity"] == "error"
    )
    write(tmp_path / ".pssparser.toml", f'[severity]\n{core_error} = "off"\n')
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    with pytest.raises(ConfigError, match="core error"):
        cfg_mod.validate_against_registry(cfg, manager)


def test_a_core_warning_may_be_turned_off(tmp_path, monkeypatch, manager):
    """Only *errors* are protected; a warning is the user's call."""
    core_warnings = [
        m["id"] for m in manager.list_all_markers()
        if m["checker"] == "core" and m["severity"] == "warning"
    ]
    if not core_warnings:
        pytest.skip("no core warning markers declared")
    write(
        tmp_path / ".pssparser.toml", f'[severity]\n{core_warnings[0]} = "off"\n'
    )
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args())
    cfg_mod.validate_against_registry(cfg, manager)  # must not raise


def test_a_core_error_may_be_restated_as_an_error(tmp_path, monkeypatch, manager):
    """Setting it to what it already is is a no-op, not a violation."""
    core_error = next(
        m["id"] for m in manager.list_all_markers()
        if m["checker"] == "core" and m["severity"] == "error"
    )
    write(tmp_path / ".pssparser.toml", f'[severity]\n{core_error} = "error"\n')
    monkeypatch.chdir(tmp_path)
    cfg_mod.validate_against_registry(resolve(args()), manager)


def test_options_for_an_uninstalled_checker_fail_fast(tmp_path, monkeypatch, manager):
    write(tmp_path / ".pssparser.toml", "[checker.nope]\nstyle = 'x'\n")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="not installed"):
        cfg_mod.validate_against_registry(resolve(args()), manager)


def test_disabling_an_absent_extension_is_allowed(tmp_path, monkeypatch, manager):
    """One config file has to serve a dev box and a leaner CI image.

    ``enabled = false`` on an extension that is not installed asks for
    nothing that is not already true, so there is nothing to fail about.
    """
    write(tmp_path / ".pssparser.toml", "[extensions.absent]\nenabled = false\n")
    monkeypatch.chdir(tmp_path)
    cfg_mod.validate_against_registry(resolve(args()), manager)


def test_enabling_an_absent_extension_fails_fast(tmp_path, monkeypatch, manager):
    """The other half of the asymmetry: this one *does* mean rules missing."""
    write(tmp_path / ".pssparser.toml", "[extensions.absent]\nenabled = true\n")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="not installed"):
        cfg_mod.validate_against_registry(resolve(args()), manager)


# ----------------------------------------------------------------------
# --show-config (C6)
# ----------------------------------------------------------------------


def test_show_config_attributes_every_layer(tmp_path, monkeypatch):
    """The Phase 2 gate: one key set at four layers, each correctly blamed."""
    write(
        tmp_path / "pyproject.toml",
        "[tool.pssparser]\n"
        'disable = ["from-pyproject"]\n'
        '[tool.pssparser.severity]\nPSS001 = "off"\n',
    )
    write(
        tmp_path / ".pssparser.toml",
        'load = ["m:C"]\n[severity]\nPSS002 = "error"\n',
    )
    monkeypatch.chdir(tmp_path)
    cfg = resolve(args(checkers=["from-cli"]))
    text = format_show_config(cfg)

    assert "pyproject.toml [tool.pssparser]" in text
    assert ".pssparser.toml" in text
    for line in text.splitlines():
        if line.strip().startswith("select "):
            assert line.endswith("command line")
        if line.strip().startswith("disable "):
            assert "pyproject.toml" in line
        if line.strip().startswith("load "):
            assert line.endswith(".pssparser.toml")
        if line.strip().startswith("severity.PSS001"):
            assert "pyproject.toml" in line
        if line.strip().startswith("severity.PSS002"):
            assert line.endswith(".pssparser.toml")


def test_show_config_marks_unset_values_as_default(tmp_path, monkeypatch):
    """"Nothing set it" is an answer to "why did this run?" too."""
    monkeypatch.chdir(tmp_path)
    text = format_show_config(resolve(args()))
    assert "Configuration files: none found" in text
    assert "(default)" in text


def test_show_config_paths_are_relative_to_cwd(tmp_path, monkeypatch):
    """Absolute paths would make the output machine-dependent, and this is
    the cheapest golden test of the whole precedence stack."""
    write(tmp_path / ".pssparser.toml", 'select = ["core"]\n')
    monkeypatch.chdir(tmp_path)
    text = format_show_config(resolve(args()))
    assert str(tmp_path) not in text
    assert ".pssparser.toml" in text
