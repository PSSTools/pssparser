"""``C-18`` -- the shared PSS corpus, swept here rather than downstream.

Why this module exists, stated plainly: the ``U-8`` grammar and lexer gaps
recorded below were not found by any test in this repository. They were found
by ``pssfmt``, which pointed a round-trip gate at a corpus assembled for a
*syntax highlighter* -- so it contained PSS 3.1 surface that no AST test here
had ever fed the parser. A defect in pssparser was discovered two repositories
away, by accident, long after it landed.

This module closes that loop. The corpus is now a shared dependency
(``pss-corpus``), and the sweep runs where the fix would be made.

Distinct from ``test_corpus.py``, next door, which parses two *other* corpora
(the ``pss-skills`` reference examples and an enclosing project's model) and
which skips when they are absent. This one does not skip -- see
:func:`test_the_corpus_is_present`.

Two contracts, one per bucket class:

``parses = true``
    Every file parses with zero syntax errors. Exceptions are named in
    :data:`KNOWN_UNPARSEABLE` and marked ``xfail(strict=True)``, so closing a
    gap turns its case green, fails the strict mark, and forces the entry out.

``parses = false``
    Every file is *rejected* -- and rejected with a diagnostic, never with a
    signal. Surviving bad input is the harder of the two promises and the one
    an editor or a pre-commit hook actually depends on.

Runs are out-of-process (``isolation.run_isolated``). A crash is a live failure
mode here, and an in-process sweep cannot report one: there is no interpreter
left to report it with, and the other ninety-one files lose their results too.
Roughly 0.1s per file, so the whole sweep is seconds, not minutes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from isolation import run_isolated  # noqa: E402


pytestmark = pytest.mark.corpus


# ---------------------------------------------------------------------------
# Discovery -- the shared contract, pss-corpus PLAN.md section 5.1
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Where the corpus was found, for diagnostics. ``"none"`` when there is none.
CORPUS_SOURCE = "none"

#: The corpus *repository* root, where ``manifest.toml`` lives -- distinct from
#: :data:`CORPUS_ROOT`, the subtree actually swept. ``None`` when the corpus is
#: a bare directory of ``.pss`` files with no repository around it.
CORPUS_REPO = None


def _sweep_root(path):
    """The subtree to sweep, given a corpus location.

    ``pss-corpus`` separates ``curated/`` from ``breadth/`` because they carry
    different promises: curated files have recorded provenance and a bucket
    policy, breadth material is bulk input of unknown validity. A consumer
    selects between them *with a path*, not with a filter it maintains itself,
    so breadth cannot leak into this gate merely by arriving.
    """
    curated = path / "curated"
    return curated if curated.is_dir() else path


def _find_corpus():
    """Locate the corpus, in decreasing order of how settled the location is.

    Duplicated in each consumer rather than shared through a package. It is
    twenty lines; a package to hold them would add a build, a release cadence
    and a version-skew failure mode to a repository whose entire value is
    having none of those.

    The sibling candidate is what makes a bare working tree usable with no
    ``ivpm update`` -- and it is the one that fires when pssparser is itself
    checked out under another project's ``packages/``, which is the normal
    arrangement while developing pssfmt against an unreleased parser.
    """
    global CORPUS_SOURCE, CORPUS_REPO

    override = os.environ.get("PSS_CORPUS")
    candidates = []
    if override:
        candidates.append(("PSS_CORPUS", Path(override)))
    candidates += [
        ("ivpm", _REPO_ROOT / "packages" / "pss-corpus"),
        ("sibling", _REPO_ROOT.parent / "pss-corpus"),
    ]
    for name, path in candidates:
        if not path.is_dir():
            continue
        root = _sweep_root(path)
        if any(root.rglob("*.pss")):
            CORPUS_SOURCE = "%s (%s)" % (name, root)
            CORPUS_REPO = path if (path / "manifest.toml").is_file() else None
            return root
    return None


CORPUS_ROOT = _find_corpus()
FILES = sorted(CORPUS_ROOT.rglob("*.pss")) if CORPUS_ROOT else []


#: Bucket policy used when there is no ``manifest.toml`` to read -- a bare
#: ``$PSS_CORPUS`` pointed at a scratch directory of ``.pss`` files.
#: :func:`test_the_manifest_agrees_with_the_fallback` pins the two together.
FALLBACK_BROKEN_BUCKETS = ("pathological",)


def _toml():
    """A TOML reader, or ``None`` on an interpreter that has neither.

    ``tomllib`` is stdlib only from 3.11 and this package supports 3.9.
    """
    try:
        import tomllib
        return tomllib
    except ModuleNotFoundError:
        try:
            import tomli
            return tomli
        except ModuleNotFoundError:
            return None


def _manifest_broken_buckets():
    """Bucket names the corpus itself declares as not-expected-to-parse.

    Read from the corpus rather than hardcoded here, so a new bucket arrives
    with its policy attached instead of needing a matching commit in each of
    three consumers. Returns ``None`` when the manifest cannot be read.
    """
    if CORPUS_REPO is None:
        return None
    toml = _toml()
    if toml is None:
        return None
    data = toml.loads((CORPUS_REPO / "manifest.toml").read_text(encoding="utf-8"))
    return tuple(sorted(
        name for name, spec in data.get("bucket", {}).items()
        if not spec.get("parses", True)))


BROKEN_BUCKETS = _manifest_broken_buckets() or FALLBACK_BROKEN_BUCKETS


# ---------------------------------------------------------------------------
# U-8 -- the gaps this corpus found, recorded where the fix would be made
# ---------------------------------------------------------------------------

#: Every open defect this sweep knows about, by identifier. Declared, rather
#: than derived from the tables below, so that deleting the last file which
#: exercises a defect cannot silently retire the defect itself.
#:
#: ``pssfmt``'s ``tests/corpus/test_parser_gaps.py`` holds a minimal reproducer
#: for each ``U-8`` entry, under the same identifiers (``C-20``). One fix
#: should flip markers in both repositories; identifiers are what make that
#: checkable rather than a matter of remembering.
#:
#: ``U-8a`` and ``U-8c`` were **withdrawn**, not fixed -- neither was ever a
#: parser defect, and both were misdiagnosed the same way (P7-C1):
#:
#: * ``U-8a`` (``action`` at package scope) -- ``package_body_item`` (B.1)
#:   admits only ``abstract_action_declaration``. A bare ``action`` there is a
#:   syntax error *by the standard*; accepting it would be the unsound
#:   direction.
#: * ``U-8c`` (``cover`` in an activity) -- ``activity_stmt`` (B.11) does not
#:   list ``cover_stmt``, which B.7 admits only as a ``component_body_item``.
#:
#: Both came from reading the three ``pss31/`` files as though the LRM's example
#: idiom were compilable PSS. It is not; see "Completing LRM examples" in
#: ``PROVENANCE.md``. The identifiers are retired rather than reused, so a
#: future ``U-8f`` cannot inherit a withdrawn one's history.
RECORDED_DEFECTS = {
    "U-8b": "`dist` constraints",
    "U-8e": "octal escape in a string literal (\"\\101\")",
    # Not a U-8: those are valid PSS the grammar will not accept. This is the
    # opposite direction, and it was found here rather than downstream.
    "U-9": "lexical errors do not reach the CLI exit status",
}

#: Corpus files that do not parse today, and why. Cause strings are shared
#: verbatim with ``pssfmt``'s ``KNOWN_UNPARSEABLE`` -- the same three files, the
#: same three identifiers, deliberately duplicated rather than imported, because
#: pssparser is upstream of pssfmt and must not depend on it to know its own
#: defects.
#:
#: Strict xfail: a fix makes the case XPASS, which fails the suite and forces
#: the entry to be removed here and in pssfmt together.
#:
#: ``U-8a`` was retired, not fixed: the three ``pss31/`` files were authored in
#: the LRM's example idiom, and a bare ``action`` at package scope is a syntax
#: error *by the standard* -- ``package_body_item`` (B.1) admits only
#: ``abstract_action_declaration``. There was never a parser defect here. The
#: files now declare their actions inside a component; see P7-C1 and the
#: "Completing LRM examples" rule in ``PROVENANCE.md``.
KNOWN_UNPARSEABLE = {
    "lexical/comments_and_strings.pss":
        "U-8e: octal escape in a string literal (\"\\101\")",
    "lexical/operators.pss":
        "U-8b: `dist` constraints. This file also contains deliberately "
        "ungrammatical operator torture (`a = -b` in a constraint), so it may "
        "not reach zero even once U-8b lands -- reclassify then, do not "
        "assume",
}


#: The inverse defect, and the one this sweep found on its first run: broken
#: input that pssparser *accepts*. Kept in its own table because it fails the
#: opposite promise -- ``KNOWN_UNPARSEABLE`` is the grammar being too narrow,
#: this is the front end being unsound.
#:
#: ``U-9`` is a new identifier, minted here. ``lone_backslash.pss`` is a lone
#: ``\`` on a line of its own, which begins an escaped identifier that no
#: whitespace terminates. The lexer sees it correctly and says so on stderr --
#: ``token recognition error at: '\n'`` -- and then the CLI reports "0 errors"
#: and exits 0. Lexical errors are not reaching the exit status.
#:
#: That matters well beyond this file. Exit status is the entire interface for
#: an editor, a pre-commit hook or ``pssfmt --check``; a file containing
#: characters the lexer could not tokenize is currently indistinguishable from
#: a clean one to every caller that does not scrape stderr. Every other file in
#: ``pathological/`` exits 1 only because it also trips a *parse* error, which
#: is what kept the hole hidden -- this file has no second error to mask it.
#:
#: Strict xfail, like the others: fixing the exit status turns the case green
#: and forces this entry out.
KNOWN_ACCEPTED = {
    "pathological/lone_backslash.pss":
        "U-9: lexical errors do not reach the CLI exit status -- the lexer "
        "reports `token recognition error` on stderr and the run still exits "
        "0 with `0 errors`",
}


def ident(path):
    return str(path.relative_to(CORPUS_ROOT)).replace("\\", "/") \
        if CORPUS_ROOT else str(path)


def _is_broken_bucket(path):
    return any(p in BROKEN_BUCKETS for p in path.relative_to(CORPUS_ROOT).parts)


def _must_parse():
    """The files required to parse, with the open gaps marked xfail."""
    out = []
    for path in FILES:
        if _is_broken_bucket(path):
            continue
        reason = KNOWN_UNPARSEABLE.get(ident(path))
        marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        out.append(pytest.param(path, id=ident(path), marks=marks))
    return out


def _must_be_rejected():
    """The files required to be rejected, with the open soundness hole marked.

    Note the asymmetry with :func:`_must_parse`: the xfail here covers only the
    *rejection* assertion. Crash-freedom is asserted separately and is never
    marked, because no defect on this list excuses a signal.
    """
    out = []
    for path in FILES:
        if not _is_broken_bucket(path):
            continue
        reason = KNOWN_ACCEPTED.get(ident(path))
        marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        out.append(pytest.param(path, id=ident(path), marks=marks))
    return out


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

def test_the_corpus_is_present():
    """``C-8``, and the load-bearing test in this file.

    Everything else here is parametrized over :data:`FILES`, so an absent
    corpus makes every one of them collect zero cases and the module reports
    success having parsed nothing. This is the one test that cannot vanish
    along with its input, which is why it is a failure and not a skip: a gate
    that skips when its subject is missing reports success in exactly the case
    it exists to catch.
    """
    assert CORPUS_SOURCE != "none", (
        "no PSS corpus found. It is a declared dev dependency and should be at "
        "packages/pss-corpus -- run `ivpm update -d default-dev`, clone "
        "psstools/pss-corpus there by hand, or set PSS_CORPUS.")
    assert len(FILES) >= 50, (
        "%d files from %s -- too few to be the curated corpus"
        % (len(FILES), CORPUS_SOURCE))


def test_the_manifest_agrees_with_the_fallback():
    """Two sources of bucket policy; pin them together or the fallback rots.

    The hardcoded tuple is used only when there is no manifest, which is the
    one configuration nobody runs day to day -- so nothing else would ever
    notice it going stale.
    """
    from_manifest = _manifest_broken_buckets()
    if from_manifest is None:
        if CORPUS_REPO is None:
            pytest.fail(
                "the corpus at %s has no manifest.toml. Every real corpus has "
                "one; this is a bare directory, and the sweep is running on "
                "the hardcoded fallback." % CORPUS_SOURCE)
        # A missing TOML reader, not a missing manifest. The sweep still runs
        # at full strength on the fallback, and every interpreter from 3.11 up
        # checks this agreement -- so skipping here loses a duplicate check
        # rather than the only one.
        pytest.skip(
            "no tomllib (3.11+) and no tomli on %s"
            % ".".join(str(v) for v in sys.version_info[:2]))
    assert from_manifest == FALLBACK_BROKEN_BUCKETS, (
        "manifest.toml declares %s as not parsing, the fallback says %s"
        % (list(from_manifest), list(FALLBACK_BROKEN_BUCKETS)))


@pytest.mark.parametrize("path", _must_parse())
def test_parses_cleanly(path):
    """Every curated file in a ``parses = true`` bucket, syntax-only.

    Syntax-only, and that is the substantive choice in this module. Most of
    the corpus is single files lifted out of multi-file models, so a linking
    run reports unresolved names for fifty-three of the ninety-two -- true,
    expected, and nothing to do with grammar coverage. Linking them here would
    mean either curating a build order the corpus does not carry, or accepting
    a gate whose failures are mostly noise. ``--syntax-only`` asks the question
    this sweep is for: can the parser *read* PSS 3.1 surface. Whole-model
    linking is already covered next door in ``test_corpus.py``.
    """
    res = run_isolated([str(path)], args=["--syntax-only"])
    assert res.ok, "%s did not parse cleanly: %s" % (ident(path), res.describe())


@pytest.mark.parametrize(
    "path", [pytest.param(p, id=ident(p)) for p in FILES if _is_broken_bucket(p)])
def test_broken_input_does_not_crash(path):
    """The ``parses = false`` buckets, first promise: survive.

    Deliberately unmarked and deliberately separate from the rejection check
    below. Half-typed source is the normal state in an editor, not an edge
    case, and no defect on :data:`KNOWN_ACCEPTED` is a reason to accept a
    signal. Folding the two assertions into one test would have put this one
    under that table's xfail.
    """
    res = run_isolated([str(path)], args=["--syntax-only"])
    assert not res.crashed, "%s crashed the parser: %s" % (
        ident(path), res.describe())


@pytest.mark.parametrize("path", _must_be_rejected())
def test_broken_input_is_rejected(path):
    """Second promise: say so. Surviving by accepting everything is not a pass.

    Exit status rather than stderr, because exit status is what every caller
    actually keys off -- and ``U-9`` is precisely the case where the two
    disagree.
    """
    res = run_isolated([str(path)], args=["--syntax-only"])
    assert res.rc == 1, (
        "%s is deliberately broken input and should be rejected with exit 1, "
        "got %s" % (ident(path), res.describe()))


# ---------------------------------------------------------------------------
# Guards on the bookkeeping above (C-20)
# ---------------------------------------------------------------------------

def test_every_recorded_gap_names_a_file_that_exists():
    """A stale entry is worse than no entry.

    It quietly stops covering a file that was renamed, while still reading as
    though it does -- and because the mark is an xfail, its disappearance
    removes a case rather than adding a failure.
    """
    present = {ident(p) for p in FILES}
    recorded = set(KNOWN_UNPARSEABLE) | set(KNOWN_ACCEPTED)
    assert recorded <= present, (
        "the defect tables name files that are not in the corpus: %s"
        % sorted(recorded - present))


def test_the_two_defect_tables_do_not_overlap():
    """A file cannot both fail to parse and be wrongly accepted.

    They are drawn from disjoint bucket classes, so an overlap means a bucket
    was reclassified in ``manifest.toml`` without the tables following -- in
    which case one of the two entries is now unreachable and its xfail is
    quietly covering nothing.
    """
    both = set(KNOWN_UNPARSEABLE) & set(KNOWN_ACCEPTED)
    assert not both, "recorded in both defect tables: %s" % sorted(both)


def test_the_recorded_defects_use_the_declared_identifiers():
    """``C-20``: the identifiers here are the ones pssfmt reproduces.

    Checked structurally rather than by importing pssfmt, which is downstream
    and absent from this repository's dependency graph by design. What this
    catches is a new defect recorded under a fresh name, or an identifier
    retired on one side only -- the two ways a shared vocabulary drifts.
    """
    reasons = list(KNOWN_UNPARSEABLE.values()) + list(KNOWN_ACCEPTED.values())
    used = {r.split(":", 1)[0].strip() for r in reasons}
    unknown = used - set(RECORDED_DEFECTS)
    assert not unknown, (
        "the defect tables cite identifiers not declared in RECORDED_DEFECTS: "
        "%s. Either declare them with a description, or use the existing "
        "identifier -- pssfmt's test_parser_gaps.py reproduces these by name."
        % sorted(unknown))

    # Every declared defect must be cited by at least one file, or the sweep is
    # not what is keeping it honest. (This once had to accommodate U-8c, which
    # owned no file of its own; U-8c has since been withdrawn as not-a-defect,
    # so the accommodation is gone and every entry now names a file directly.)
    cited = used | {d for d in RECORDED_DEFECTS if any(d in r for r in reasons)}
    assert set(RECORDED_DEFECTS) == cited, (
        "declared defects no corpus file exercises: %s. A defect the sweep "
        "cannot see is one that will be fixed without anyone noticing."
        % sorted(set(RECORDED_DEFECTS) - cited))
