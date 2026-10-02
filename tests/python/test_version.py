"""Source-tree versions (sphinx-pss request V1, 2026-09-28).

An unstamped tree used to report 0.0.0. Any downstream floor (`pssparser>=3.1.0`)
then rejected a source build, so `pip install -e sphinx-pss` replaced the
editable parser with PyPI's. It is now a PEP 440 dev release of the next patch,
derived from `git describe`. A CI-stamped tree, the only kind that is ever
published, is unchanged.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pssparser.__version__ import compute_version

try:
    from packaging.version import Version
except ImportError:  # pragma: no cover
    Version = None

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                   env={**os.environ,
                        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def _commit(repo, n=1):
    for _ in range(n):
        f = repo / "f.txt"
        f.write_text(f.read_text() + "x" if f.exists() else "x")
        _git(repo, "add", "f.txt")
        _git(repo, "commit", "-q", "-m", "c")


def _sha(repo):
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=repo).decode().strip()


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _commit(tmp_path)
    return tmp_path


def _v(repo, base="0.0.0", suffix="", **env):
    return compute_version(str(repo), base=base, suffix=suffix, env=env)


def _check_pep440(v, prerelease):
    if Version is None:
        return
    parsed = Version(v)
    assert parsed.is_prerelease == prerelease, v
    assert parsed > Version("3.1.7") or not prerelease, v


def test_an_exact_tag_is_the_release(repo):
    _git(repo, "tag", "v3.1.7")
    assert _v(repo) == "3.1.7"
    _check_pep440("3.1.7", prerelease=False)


def test_commits_past_a_tag_are_a_dev_release_of_the_next_patch(repo):
    _git(repo, "tag", "v3.1.7")
    _commit(repo, 2)
    v = _v(repo)
    assert v == "3.1.8.dev2+g%s" % _sha(repo)
    _check_pep440(v, prerelease=True)


def test_a_dirty_tree_says_so(repo):
    _git(repo, "tag", "v3.1.7")
    _commit(repo, 2)
    (repo / "f.txt").write_text("changed")
    assert _v(repo) == "3.1.8.dev2+g%s.dirty" % _sha(repo)


def test_a_dirty_tag_is_not_the_release(repo):
    _git(repo, "tag", "v3.1.7")
    (repo / "f.txt").write_text("changed")
    v = _v(repo)
    assert v == "3.1.8.dev0+g%s.dirty" % _sha(repo)
    _check_pep440(v, prerelease=True)


def test_past_a_release_candidate(repo):
    _git(repo, "tag", "v3.2.0rc1")
    _commit(repo, 3)
    v = _v(repo)
    assert v == "3.2.0rc2.dev3+g%s" % _sha(repo)
    if Version is not None:
        assert Version("3.2.0rc1") < Version(v) < Version("3.2.0rc2")


def test_no_tag_or_no_git_falls_back(repo, tmp_path_factory):
    assert _v(repo) == "0.0.0"
    assert _v(tmp_path_factory.mktemp("nogit")) == "0.0.0"


def test_other_tags_are_ignored(repo):
    _git(repo, "tag", "v3.1.7")
    _commit(repo)
    _git(repo, "tag", "foo")
    assert _v(repo).startswith("3.1.8.dev1+g")


def test_the_environment_overrides(repo):
    assert _v(repo, PSSPARSER_VERSION="3.1.8.dev123") == "3.1.8.dev123"
    with pytest.raises(ValueError):
        _v(repo, PSSPARSER_VERSION="not a version")


def test_a_ci_stamped_tag_build_is_unchanged(repo):
    _git(repo, "tag", "v3.1.7")
    _commit(repo, 2)
    assert _v(repo, base="3.2.0") == "3.2.0"


def test_a_ci_dev_run_is_index_legal(repo):
    """CI stamps SUFFIX=.<run-id>. With tags visible it is a dev release of
    the next patch; without them (a shallow checkout), the 0.0.0 form."""
    assert _v(repo, suffix=".4242") == "0.0.0.4242"
    _git(repo, "tag", "v3.1.7")
    _commit(repo)
    v = _v(repo, suffix=".4242")
    assert v == "3.1.8.dev4242"
    _check_pep440(v, prerelease=True)


def test_this_checkout_reports_a_real_version():
    src = Path(__file__).parent.parent.parent
    if not (src / ".git").exists():
        pytest.skip("not a git checkout (a wheel test)")
    v = compute_version(str(src), env={})
    if Version is not None:
        Version(v)
    tags = subprocess.run(["git", "tag", "--list", "v[0-9]*"], cwd=src,
                          capture_output=True, text=True).stdout.split()
    if tags:
        assert v != "0.0.0", v
