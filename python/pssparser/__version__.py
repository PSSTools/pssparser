import os
import re
import subprocess

# THE TAG IS THE VERSION. CI substitutes the tag into BASE on a `v*` build,
# so a release is a tag and nothing else -- there is no version to bump here
# before tagging, and editing this value does not change what gets released.
#
# 0.0.0 is deliberately not a plausible release. CI stamps dev artifacts as
# 0.0.0.<run-id>: lower than every real release under PEP 440, so a dev wheel
# can never be resolved in preference to one.
#
# An UNSTAMPED source tree (a developer checkout, `pip install -e`) is
# versioned from `git describe` instead, as a PEP 440 dev release of the next
# patch: v3.1.7-2-g1ec757b is 3.1.8.dev2+g1ec757b, with `.dirty` for a dirty
# tree. That is above 3.1.7, so a downstream floor (`pssparser>=3.1.0`) keeps
# the source build rather than replacing it from PyPI, and it is still a
# pre-release, so a resolver never prefers it over a release (sphinx-pss V1).
BASE = "0.0.0"
SUFFIX = ""

#: The version when nothing better is known: no stamp, no git, no tag.
FALLBACK = "0.0.0"

_DESCRIBE = re.compile(
    r"^v(?P<tag>\d+\.\d+\.\d+(?:rc\d+)?)-(?P<n>\d+)-g(?P<sha>[0-9a-f]+)(?P<dirty>-dirty)?$")
_PEP440 = re.compile(r"^\d+(\.\d+)*((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?(\+[a-z0-9.]+)?$")


def _next_release(tag):
    """The release after `tag`: 3.1.7 -> 3.1.8, 3.2.0rc1 -> 3.2.0rc2."""
    m = re.match(r"^(\d+\.\d+\.\d+)rc(\d+)$", tag)
    if m:
        return "%src%d" % (m.group(1), int(m.group(2)) + 1)
    major, minor, patch = tag.split(".")
    return "%s.%s.%d" % (major, minor, int(patch) + 1)


def _describe(src_dir):
    """`git describe` of `src_dir`, or None when there is no git or no tag."""
    if not os.path.exists(os.path.join(src_dir, ".git")):
        return None
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--long", "--dirty", "--match", "v[0-9]*"],
            cwd=src_dir, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def compute_version(src_dir, base=BASE, suffix=SUFFIX, env=None):
    """The version of the tree at `src_dir`.

    - `$PSSPARSER_VERSION`, when set (validated as PEP 440).
    - A CI-stamped tag build (`base` is not 0.0.0): `base` + `suffix`.
    - Otherwise `git describe`: an exact tag on a clean tree is that tag;
      anything else is `<next>.dev<n>+g<sha>[.dirty]`. A CI dev run
      (`suffix` is `.<run-id>`) with tags visible is `<next>.dev<run-id>`,
      which an index accepts (no `+local` label).
    - Otherwise `base` + `suffix`: 0.0.0, or 0.0.0.<run-id> in CI.
    """
    env = os.environ if env is None else env
    forced = env.get("PSSPARSER_VERSION")
    if forced:
        if not _PEP440.match(forced):
            raise ValueError("PSSPARSER_VERSION=%r is not a PEP 440 version" % forced)
        return forced

    if base != FALLBACK:
        return base + suffix

    desc = _describe(src_dir)
    m = _DESCRIBE.match(desc) if desc else None
    if m:
        tag, n, sha, dirty = m.group("tag"), int(m.group("n")), m.group("sha"), m.group("dirty")
        run_id = suffix[1:] if suffix.startswith(".") and suffix[1:].isdigit() else None
        if run_id is not None:
            return "%s.dev%s" % (_next_release(tag), run_id)
        if n == 0 and not dirty:
            return tag
        return "%s.dev%d+g%s%s" % (_next_release(tag), n, sha, ".dirty" if dirty else "")

    return base + suffix


def _src_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_version():
    """The version of this pssparser.

    An installed build reads the version setup.py recorded in `_version.py`,
    and never runs git. A checkout that was never built computes it.
    """
    try:
        from ._version import version
        return version
    except ImportError:
        return compute_version(_src_dir())


#: Kept as the (BASE, SUFFIX) tuple CI stamps; use get_version() for the
#: version string.
__version__ = (BASE, SUFFIX)
