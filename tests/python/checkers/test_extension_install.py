"""End-to-end tests over *real* installed entry-point metadata.

Every other extension test fakes ``manager._entry_points``, which is the right
default: discovery must not depend on what happens to be installed in the
developer's environment.  But faking it also means nothing exercises the part
that actually breaks in the field -- the ``setup.cfg`` declaration, the
``.dist-info/entry_points.txt`` it produces, and ``importlib.metadata``
finding it.  These tests install into a throwaway directory with ``--target``
and put it on a subprocess's ``PYTHONPATH``, so the metadata is genuine
without anyone having to rebuild pssparser into a fresh venv.

Marked ``needs_install`` and skipped when no installer is available.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.needs_install

_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
_EXAMPLE = os.path.join(_REPO, "examples", "pss_rule_collection")


def _installer() -> list:
    """Return an install command prefix, or skip if none is available."""
    uv = shutil.which("uv")
    if uv:
        return [uv, "pip", "install"]
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True, capture_output=True,
        )
    except Exception:
        pytest.skip("neither uv nor pip is available to install the example")
    return [sys.executable, "-m", "pip", "install"]


def _install(source: str, target: str) -> None:
    cmd = _installer() + ["--quiet", "--no-deps", "--target", target, source]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(
            f"install of {source} failed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


def _run_in_subprocess(target: str, code: str) -> str:
    """Run *code* with *target* and the repo's python/ on PYTHONPATH."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([os.path.join(_REPO, "python"), target])
    env.pop("PSSPARSER_NO_EXTENSIONS", None)
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True, text=True, env=env, cwd=_REPO,
    )
    if result.returncode != 0:
        pytest.fail(f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result.stdout


def _write_broken_extension(path: str) -> str:
    """Create a distribution whose extension module fails to import."""
    src = os.path.join(path, "src", "broken_rules")
    os.makedirs(src, exist_ok=True)
    with open(os.path.join(src, "__init__.py"), "w") as f:
        f.write("raise ImportError('deliberately broken example extension')\n")
    with open(os.path.join(path, "setup.cfg"), "w") as f:
        f.write(textwrap.dedent("""\
            [metadata]
            name = pss-broken-rules
            version = 9.9.9

            [options]
            package_dir =
                = src
            packages = find:

            [options.packages.find]
            where = src

            [options.entry_points]
            pssparser.extensions =
                broken-rules = broken_rules
            """))
    with open(os.path.join(path, "setup.py"), "w") as f:
        f.write("from setuptools import setup\nsetup()\n")
    return path


# ---------------------------------------------------------------------------
# The Phase 1 gate
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """Install the example collection into a throwaway --target directory."""
    target = str(tmp_path_factory.mktemp("target"))
    _install(_EXAMPLE, target)
    return target


def test_installed_extension_is_discovered_with_no_flags(installed):
    out = _run_in_subprocess(installed, """
        import json
        from pssparser.checkers import CheckerManager
        m = CheckerManager()
        m.discover()
        print(json.dumps({
            "issues": [d["code"] for d in m.load_diagnostics],
            "extensions": m.list_extensions(),
            "checkers": sorted(
                i["name"] for i in m.list_checkers() if not i["is_builtin"]
            ),
        }))
    """)
    data = json.loads(out)

    assert data["issues"] == []
    assert data["checkers"] == ["component-naming", "package-naming"]

    ext = data["extensions"][0]
    assert ext["name"] == "example-rules"
    assert ext["version"] == "0.1.0"
    assert ext["dist"] == "pss-rule-collection"
    assert ext["checkers"] == ["component-naming", "package-naming"]


def test_installed_extension_rules_actually_fire(installed, tmp_path):
    """Installed means active: the rules run with no command-line flags."""
    pss = tmp_path / "demo.pss"
    pss.write_text("package MyPkg {\n    component widget_c {}\n}\n")

    out = _run_in_subprocess(installed, f"""
        import json
        from pssparser.cli.commands import cmd_parse
        import io
        err = io.StringIO()
        rc = cmd_parse([{str(pss)!r}], stderr=err, color=False)
        print(json.dumps({{"rc": rc, "err": err.getvalue()}}))
    """)
    data = json.loads(out)

    assert data["rc"] == 0                      # warnings do not fail a run
    assert "PRC001" in data["err"]
    assert "PRC002" in data["err"]
    assert "widget_c" in data["err"]


def test_a_broken_sibling_does_not_disturb_a_healthy_extension(
    installed, tmp_path_factory
):
    """The other half of the gate: isolation between installed extensions."""
    target = str(tmp_path_factory.mktemp("target_mixed"))
    _install(_EXAMPLE, target)
    broken_src = _write_broken_extension(str(tmp_path_factory.mktemp("broken")))
    _install(broken_src, target)

    out = _run_in_subprocess(target, """
        import json
        from pssparser.checkers import CheckerManager
        m = CheckerManager()
        m.discover()
        print(json.dumps({
            "issues": m.load_diagnostics,
            "extensions": [e["name"] for e in m.list_extensions()],
            "checkers": sorted(
                i["name"] for i in m.list_checkers() if not i["is_builtin"]
            ),
        }))
    """)
    data = json.loads(out)

    # The broken one is reported...
    assert [d["code"] for d in data["issues"]] == ["PSS030"]
    assert "broken-rules" in data["issues"][0]["message"]
    assert "pss-broken-rules" in data["issues"][0]["message"]

    # ...and the healthy one still loaded completely.
    assert data["extensions"] == ["example-rules"]
    assert data["checkers"] == ["component-naming", "package-naming"]


def test_no_extensions_env_var_wins_over_a_real_install(installed):
    out = _run_in_subprocess(installed, """
        import json, os
        os.environ["PSSPARSER_NO_EXTENSIONS"] = "1"
        from pssparser.checkers import CheckerManager
        m = CheckerManager()
        m.discover()
        print(json.dumps(sorted(m._registered)))
    """)
    assert json.loads(out) == ["core"]
