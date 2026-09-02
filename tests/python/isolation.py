"""Out-of-process parser invocation, for tests that must survive a crash.

A segfault or an uncaught C++ exception in the parser takes the whole process
down.  In-process helpers therefore cannot test for crash-freedom: a bare
``try/except`` around ``Parser.link()`` never runs, because there is no
interpreter left to run it.  Anything asserting "invalid input must not crash"
has to spawn a subprocess and inspect its exit status.

Exit-status convention (see ``IsolatedResult.crashed``):

===========  ==========================================================
``rc == 0``  clean parse and link
``rc == 1``  errors reported normally -- the healthy failure mode
``rc < 0``   killed by a signal; ``-rc`` is the signal number (SIGSEGV
             is 11, so a segfault shows up as ``rc == -11``)
``rc >= 2``  abort, uncaught exception, or an internal failure
===========  ==========================================================

Note the sign.  ``subprocess`` reports signal death as a *negative*
returncode, whereas a shell reports ``128 + signum``.  A check written as
``rc >= 128`` -- the natural thing to write, and what the original issue-repro
script used -- silently classifies every segfault as a normal rejection.  Use
:attr:`IsolatedResult.crashed`, which handles both conventions.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union


#: A source file: either a path, or a (name, text) pair to be materialized.
Source = Union[str, Tuple[str, str]]


#: This repository's importable ``pssparser``, as an absolute path.
_REPO_PYTHON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "python")


def _parent_package_root():
    """The directory the *parent* process imported ``pssparser`` from.

    This is the pin, and it is deliberately not ``_REPO_PYTHON``.  The
    invariant that matters is **the child must import the same parser the
    parent is testing**, and which copy that is depends on how the suite was
    invoked:

    * On a developer machine (``PYTHONPATH=python pytest ...``) the parent
      imports the working tree, so this returns ``<repo>/python`` and the child
      gets the working tree -- the P7-X1 guarantee, unchanged.
    * In CI the parent imports an **installed wheel** from a clean venv, on
      purpose: the point of that step is to test the artifact that would ship.
      The working tree is not importable there at all, because the compiled
      extension is built into ``build/`` rather than in place.  This returns
      site-packages, and the child agrees with the parent.

    Pinning ``_REPO_PYTHON`` unconditionally got the second case exactly
    backwards.  The source tree shadowed the wheel, ``import pssparser.core``
    raised ``ModuleNotFoundError`` in every child, and all ~590 out-of-process
    tests -- the corpus sweep, the linking suite, every CLI exit-status case --
    failed at interpreter startup.  That is what turned the v3.1.0 tag build
    red and blocked the release.

    Falls back to ``_REPO_PYTHON`` if ``pssparser`` has no locatable
    ``__file__`` (a namespace package, or a frozen build), which preserves the
    developer-machine behaviour in the case this cannot resolve.
    """
    try:
        import pssparser
        init = getattr(pssparser, "__file__", None)
        if init:
            return os.path.dirname(os.path.dirname(os.path.abspath(init)))
    except ImportError:
        pass
    return _REPO_PYTHON


def _child_env():
    """The subprocess environment, with the parent's parser pinned first.

    Every run here uses ``cwd=workdir``, a temporary directory.  The suite is
    normally invoked as ``PYTHONPATH=python pytest ...`` -- a **relative** path,
    which resolves against the repository root in the parent and against the
    temporary directory (i.e. nowhere) in the child.  The child then falls back
    to whatever ``pssparser`` is on the ambient ``sys.path``.

    That is not hypothetical.  On a developer machine with a sibling project
    installed -- an ``easy-install.pth`` naming another checkout's
    ``packages/pssparser/python`` is the common case -- every out-of-process
    test silently exercised *that* copy instead of the working tree.  The
    corpus sweep, whose entire job is to notice parser gaps, reported green
    against a parser nobody had just built.  Nothing failed; the gate simply
    stopped being about this repository.

    Prepending :func:`_parent_package_root` makes the child test what the
    parent tested, regardless of cwd, of how the suite was invoked, or of what
    else is installed.
    """
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    pin = _parent_package_root()
    env["PYTHONPATH"] = (pin + os.pathsep + existing) if existing else pin
    return env


@dataclass
class IsolatedResult:
    """Outcome of one out-of-process parser run."""

    rc: int
    stdout: str
    stderr: str
    files: List[str]

    @property
    def output(self) -> str:
        return self.stdout + self.stderr

    @property
    def crashed(self) -> bool:
        """True when the process died from a signal, under either convention."""
        return self.rc < 0 or self.rc >= 128

    @property
    def signal(self) -> Optional[int]:
        """The killing signal number, or None if it exited normally."""
        if self.rc < 0:
            return -self.rc
        if self.rc >= 128:
            return self.rc - 128
        return None

    @property
    def ok(self) -> bool:
        """True when the run parsed and linked with no errors."""
        return self.rc == 0

    def describe(self) -> str:
        """A diagnostic string for assertion messages."""
        if self.crashed:
            what = "killed by signal %d" % self.signal
        else:
            what = "exit %d" % self.rc
        body = self.output.strip()
        return "%s\n--- output ---\n%s" % (what, body if body else "(no output)")


def run_isolated(
    sources: Union[str, Sequence[Source]],
    *,
    args: Sequence[str] = (),
    timeout: int = 120,
    tmp_path=None,
) -> IsolatedResult:
    """Run the parser CLI on *sources* in a subprocess.

    *sources* is PSS text, a path, or a sequence of paths and/or
    ``(filename, text)`` pairs.  Text sources are written into *tmp_path*
    (or a fresh temporary directory) before the run.

    Never raises on a parse failure -- inspect the returned result.  A timeout
    is reported as ``rc = -9`` (i.e. as a crash), since a parser that hangs is
    no more usable than one that dies.
    """
    holder = None
    if tmp_path is None:
        holder = tempfile.TemporaryDirectory()
        workdir = holder.name
    else:
        workdir = str(tmp_path)

    try:
        if isinstance(sources, str):
            sources = [sources]

        paths: List[str] = []
        for i, src in enumerate(sources):
            if isinstance(src, tuple):
                name, text = src
            elif os.path.exists(src):
                paths.append(str(src))
                continue
            else:
                # bare PSS text
                name, text = ("case_%d.pss" % i), src
            p = os.path.join(workdir, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fp:
                fp.write(text)
            paths.append(p)

        cmd = [sys.executable, "-m", "pssparser", *args, *paths]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir,
                env=_child_env(),
            )
        except subprocess.TimeoutExpired as exc:
            return IsolatedResult(
                rc=-9,
                stdout=exc.stdout or "",
                stderr="timed out after %ds" % timeout,
                files=paths,
            )

        return IsolatedResult(
            rc=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            files=paths,
        )
    finally:
        if holder is not None:
            holder.cleanup()


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def assert_no_crash(sources, *, description: str = "", **kw) -> IsolatedResult:
    """Assert the parser exits normally, whether or not it reports errors.

    This is the contract every input must satisfy, including malformed and
    semantically invalid ones: a diagnostic the user can act on, never a
    signal.
    """
    res = run_isolated(sources, **kw)
    assert not res.crashed, "parser crashed%s: %s" % (
        (" (%s)" % description) if description else "",
        res.describe(),
    )
    return res


def assert_clean(sources, **kw) -> IsolatedResult:
    """Assert the parser accepts *sources* with no errors at all."""
    res = run_isolated(sources, **kw)
    assert res.ok, "expected a clean parse, got %s" % res.describe()
    return res


def assert_rejects(sources, expected: Optional[str] = None, **kw) -> IsolatedResult:
    """Assert a normal rejection (exit 1), optionally matching *expected* text.

    Distinct from :func:`assert_no_crash`: this demands the *diagnostic*, not
    merely survival.  Use it to pin the error a crash should have been.
    """
    res = run_isolated(sources, **kw)
    assert not res.crashed, "expected a diagnostic, got a crash: %s" % res.describe()
    assert res.rc == 1, "expected exit 1 (errors reported), got %s" % res.describe()
    if expected is not None:
        assert expected in res.output, "expected %r in output, got %s" % (
            expected,
            res.describe(),
        )
    return res
