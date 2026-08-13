from .parser import Parser, ParseException
from .__version__ import __version__, get_version

def get_deps():
    return []

def get_libs():
    return ["pssparser"]

def get_libdirs():
    import os
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    return [pkg_dir]

def get_incdirs():
    import os
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(pkg_dir, "include")):
        return [os.path.join(pkg_dir, "include")]
    else:
        root_dir = os.path.abspath(os.path.join(pkg_dir, "../.."))
        return [os.path.join(root_dir, "src", "include")]


def get_stdlib_dir():
    """Directory holding the standard-library ``.pss`` sources.

    The parser compiles these in, so parsing never needs them.  A tool that
    *documents* or cross-references the core library does: it needs the source
    text, and in an installed wheel there is nowhere else to look.

    Mirrors :func:`get_incdirs`: the installed location first, the source tree
    second.
    """
    import os
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    installed = os.path.join(pkg_dir, "stdlib")
    if os.path.isdir(installed):
        return installed
    root_dir = os.path.abspath(os.path.join(pkg_dir, "../.."))
    return os.path.join(root_dir, "src", "stdlib")


def get_stdlib_files():
    """The standard-library ``.pss`` sources, sorted by name.

    Returns an empty list when the directory is absent rather than raising, so
    a caller can degrade to "no core-library reference" instead of failing.
    """
    import glob
    import os
    d = get_stdlib_dir()
    if not os.path.isdir(d):
        return []
    return sorted(glob.glob(os.path.join(d, "*.pss")))
