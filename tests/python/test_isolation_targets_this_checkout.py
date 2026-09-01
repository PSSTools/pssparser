"""``P7-X1``: the out-of-process harness must exercise *this* working tree.

Every out-of-process test -- the whole corpus sweep, every crash-freedom case,
every CLI exit-status case -- runs through :func:`isolation.run_isolated`, which
spawns ``python -m pssparser`` with ``cwd`` set to a temporary directory.  The
suite is normally invoked as ``PYTHONPATH=python pytest ...``: a *relative*
path, which resolves against the repository root in the parent process and
against the temporary directory in the child.  It therefore resolves to nothing
in the child, which falls back to whatever ``pssparser`` the ambient
``sys.path`` provides.

This was not a theoretical hazard.  With a sibling project installed -- an
``easy-install.pth`` naming another checkout's ``packages/pssparser/python``
is the ordinary arrangement here -- the child imported *that* parser.  A
grammar fix in this tree was invisible to the sweep, and a corpus file repaired
against the fix failed with the pre-fix diagnostic.  Nothing errored; the gate
simply stopped being about this repository, and would have stayed that way.

The failure mode is silent by construction, so it needs a test of its own: no
parser behaviour is wrong in either checkout, and the two are similar enough
that results usually agree.  They disagree exactly when this repository has
changed -- which is the only time the sweep matters.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from isolation import _REPO_PYTHON, _child_env, run_isolated  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_pinned_path_is_this_repository():
    """The pin is computed from ``__file__``, so a move must not silently miss."""
    assert Path(_REPO_PYTHON) == REPO_ROOT / "python", (
        "isolation._REPO_PYTHON no longer names this repository's python/ "
        "directory (%s); the file was probably moved without updating the "
        "parents[] depth." % _REPO_PYTHON)
    assert (Path(_REPO_PYTHON) / "pssparser" / "__init__.py").is_file(), (
        "%s does not contain an importable pssparser" % _REPO_PYTHON)


def test_the_child_env_puts_this_checkout_first():
    """Prepended, not appended: an ambient install must lose, not win."""
    entries = _child_env()["PYTHONPATH"].split(os.pathsep)
    assert entries[0] == _REPO_PYTHON, (
        "this checkout must come first on the child's PYTHONPATH, or an "
        "ambient install shadows it; got %r" % (entries,))


def test_an_isolated_run_imports_this_checkout():
    """The end-to-end assertion, and the one that actually caught this.

    Asks the child where it found ``pssparser``, rather than inferring it from
    the environment -- the environment is what was wrong, so it cannot also be
    the evidence.
    """
    import subprocess
    proc = subprocess.run(
        [sys.executable, "-c",
         "import pssparser, sys; sys.stdout.write(pssparser.__file__)"],
        capture_output=True, text=True, cwd=os.path.dirname(os.devnull) or "/",
        env=_child_env(), timeout=60)
    assert proc.returncode == 0, proc.stderr
    found = Path(proc.stdout.strip()).resolve()
    assert found == (REPO_ROOT / "python" / "pssparser" / "__init__.py").resolve(), (
        "an isolated child imported a different pssparser: %s. Every "
        "out-of-process gate in this suite was testing that copy." % found)


def test_an_isolated_run_sees_a_grammar_change_made_here():
    """A behavioural probe, not a path assertion.

    ``exec file`` in a *component* body (Example 309) is accepted by this tree
    and was rejected before P7-G3.  It is a cheap stand-in for "the child is
    running the parser that was just built": if the child ever reverts to an
    older or foreign copy, this is the shape of failure it will produce.
    """
    res = run_isolated(
        'package p { component C { exec file "f.txt" = "x"; } }',
        args=["--syntax-only"])
    assert res.rc == 0, (
        "an isolated child rejected source this tree accepts in-process, which "
        "means it is not running this tree's parser: %s" % res.describe())
