import os

BASE = "3.0.0"
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
