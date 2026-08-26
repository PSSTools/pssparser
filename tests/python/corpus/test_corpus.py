"""Whole-model gate: real PSS must parse, both per-file and all together.

The unit tests elsewhere in this suite each exercise one construct in a
minimal model.  That is exactly the shape of input that already works.  The
failures users actually hit come from *scale* -- many files, cross-file
references, one file opened on its own in an editor -- so this module parses
real corpora instead of snippets.

Two corpora, both optional:

``examples``
    The hand-written examples in ``pss-skills/skills/pss-language-ref``.  Each
    is correct PSS by construction, so any error is a parser defect.

``model``
    The ``src/pss`` model of the enclosing project.  Larger, cross-referencing,
    and representative of what a real user feeds the tool.

Both live outside this repository, so every test skips cleanly when they are
absent -- pssparser's own CI stays green standalone.  Runs are
out-of-process because a crash here is the expected failure mode today.

The per-file tests are the important ones.  Parsing a single file of a
multi-file model *should* report unresolved names and exit 1; today it can
segfault (plan phase 1.1), which is what blocks editor integration and
pre-commit hooks.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from isolation import run_isolated  # noqa: E402


# ---------------------------------------------------------------------------
# Corpus discovery
# ---------------------------------------------------------------------------

def _project_root():
    """Locate the enclosing project, if pssparser is vendored inside one."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "packages" / "pssparser").is_dir():
            return parent
    return None


_ROOT = _project_root()

_EXAMPLES = (
    _ROOT / "packages" / "pss-skills" / "skills" / "pss-language-ref" / "examples"
    if _ROOT else None
)
_MODEL = _ROOT / "src" / "pss" if _ROOT else None


def _pss_files(d, recursive=False):
    if d is None or not d.is_dir():
        return []
    return sorted(str(p) for p in (d.rglob if recursive else d.glob)("*.pss"))


EXAMPLE_FILES = _pss_files(_EXAMPLES)
MODEL_FILES = _pss_files(_MODEL, recursive=True)


#: Why a glob is the wrong input for a whole-model run, reported when the
#: derivation is unavailable so the skip does not read as "nothing to test".
_NO_ORDER = (
    "the model's file order could not be derived (dv-flow-libpss's "
    "pss.FileSet); a glob is not a substitute -- see _model_build_order"
)


def _model_build_order():
    """The model's files, in the order and selection its build uses.

    A glob is not usable here, for two reasons that have nothing to do with the
    parser.  Compile-time elaboration is order-*dependent* by specification --
    a ``compile if`` reads constants from previously-processed source units
    (PSS 3.1 19.1.2) -- so a config package that sorts after its users is a
    forward reference.  And ``wb_dma_cfg_pkg/`` holds two mutually-exclusive
    files declaring the same package, of which a build selects exactly one; a
    glob takes both and duplicates the constant.

    Both the order and that selection are stated in the model's ``pss.FileSet``
    task, so read them from there.  Deriving beats reading a checked-in
    filelist: the filelist this test used to read had gone stale against a
    renamed model, which is the failure mode a derivation cannot have.
    """
    if _MODEL is None:
        return []
    try:
        from dv_flow.libpss.file_set import derive_from_flow
    except ImportError:
        return []

    files, markers = derive_from_flow(str(_MODEL), "src")
    if any(sev == "error" for sev, _ in markers):
        return []
    return [str(_MODEL / f) for f in files]


MODEL_BUILD_FILES = _model_build_order()


def _ids(paths):
    return [os.path.basename(p) for p in paths]


#: Examples excluded from the gate, with the plan phase that readmits them.
#: Keep this list shrinking -- it is the visible cost of the open issues.
#:
#: Applied as a *strict* xfail, so an entry that starts passing fails the
#: suite and has to be removed deliberately. An imperative pytest.xfail()
#: call would be simpler but can never report XPASS, so a fixed example
#: would stay silently excluded -- which is the failure mode this list
#: exists to prevent.
EXAMPLE_EXCLUSIONS = {
    # Empty: every reference example parses. Both former entries
    # (resource_arbitration.pss, behavioral_coverage.pss) were readmitted
    # once lock/share resolution and the monitor activity grammar were
    # fixed. Add an entry only with a plan phase that removes it again.
}


def _example_params():
    out = []
    for path in EXAMPLE_FILES:
        name = os.path.basename(path)
        reason = EXAMPLE_EXCLUSIONS.get(name)
        marks = (
            [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        )
        out.append(pytest.param(path, id=name, marks=marks))
    return out


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not EXAMPLE_FILES, reason="pss-language-ref examples not present")
@pytest.mark.parametrize("path", _example_params())
def test_example_parses_alone(path):
    """Each reference example is correct PSS and must parse standalone."""
    name = os.path.basename(path)
    res = run_isolated([path])
    assert res.ok, "%s did not parse cleanly: %s" % (name, res.describe())


# ---------------------------------------------------------------------------
# The project model
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not MODEL_FILES, reason="src/pss model not present")
@pytest.mark.parametrize("path", MODEL_FILES, ids=_ids(MODEL_FILES))
def test_model_file_alone_does_not_crash(path):
    """One file of a multi-file model: unresolved names, never a crash.

    This is the normal state while editing, and the exit status is what an
    editor or pre-commit hook keys off.  Errors are fine here; signals are
    not.
    """
    res = run_isolated([path])
    assert not res.crashed, "%s crashed when parsed alone: %s" % (
        os.path.basename(path),
        res.describe(),
    )


@pytest.mark.skipif(not MODEL_BUILD_FILES, reason=_NO_ORDER)
def test_whole_model_parses():
    """The complete model, all files at once, must link with no errors.

    This was the last whole-model failure, and it resisted isolation for a
    long time: the symptom was ``Failed to find elem \\init`` at
    ``wb_dma_ops_c.pss:58``, an escaped-identifier method called through an
    array subscript inside a foreach, and every small reproduction of *that*
    shape linked clean.  It was never about escaped identifiers.  The cause
    was ``TaskBuildParamValList::probe`` walking a template argument's whole
    subtree instead of examining the argument itself -- so a generic supplied
    as an argument was mistaken for a reference to its own parameter, and the
    binding collapsed to the inner generic's argument.  See
    ``test_template_nesting.py``, which pins it in four lines of PSS.
    """
    res = run_isolated(MODEL_BUILD_FILES, timeout=300)
    assert res.ok, "the complete model did not parse: %s" % res.describe()


@pytest.mark.skipif(not MODEL_BUILD_FILES, reason=_NO_ORDER)
def test_whole_model_syntax_only():
    """Parse without linking -- isolates grammar coverage from resolution.

    Passing here while :func:`test_whole_model_parses` fails localizes the
    defect to the linker, which is exactly the split seen today.
    """
    res = run_isolated(MODEL_BUILD_FILES, args=["--syntax-only"], timeout=300)
    assert res.ok, "the complete model failed to *parse*: %s" % res.describe()
