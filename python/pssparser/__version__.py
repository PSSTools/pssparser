import os

# THE TAG IS THE VERSION. CI substitutes the tag into BASE on a `v*` build,
# so a release is a tag and nothing else -- there is no version to bump here
# before tagging, and editing this value does not change what gets released.
#
# 0.0.0 is deliberately not a plausible release. It is the baseline for dev
# artifacts, which CI stamps as 0.0.0.<run-id>: lower than every real release
# under PEP 440, so a dev wheel can never be resolved in preference to one,
# and obviously wrong if it ever reaches a registry.
BASE = "0.0.0"
SUFFIX = ""

__version__ = (BASE, SUFFIX)

# Used by setup.py dynamic versioning
_pkg_version = BASE + SUFFIX


def get_version():
    """Return the full version string, appending git describe when in a source tree."""
    base, suffix = __version__
    version = base + suffix

    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    git_dir = os.path.join(src_dir, ".git")

    if os.path.isdir(git_dir):
        try:
            import subprocess
            out = subprocess.check_output(
                ["git", "describe", "--tags", "--dirty", "--always"],
                cwd=src_dir,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if out != base:
                return "%s+%s" % (version, out)
        except Exception:
            pass

    return version
