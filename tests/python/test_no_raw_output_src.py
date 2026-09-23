"""INV-2, source half: the parser and linker write nothing to stdout/stderr.

A diagnostic that is printed instead of reported is invisible to every
consumer of the marker list, uncounted in the exit status, and -- because the
dmgr macros print to *stdout* -- it corrupts ``--json`` output. Every such
site in ``src/`` has been converted: to a marker, to a PSS000 internal error
(``InternalError`` / ``ResolveContext::internalError``), or to ``DEBUG``,
which prints only when debug output is enabled. See
docs/design/symbol-resolution-plan.md INV-2 and WS0.4.

This lint keeps it that way. ``DEBUG_ERROR`` and ``DEBUG_FATAL`` are banned
outright: the first prints unconditionally, the second throws a bare
``std::runtime_error``. Use ``DEBUG`` for tracing and ``InternalError`` for a
state that should not happen.

The runtime half -- nothing printed while parsing and linking real inputs --
is ``test_no_crash_no_raw_output.py``.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

#: Constructs that write to the terminal, or that exist to.
_BANNED = re.compile(
    r"\bfprintf\s*\(\s*std(?:out|err)\b"
    r"|(?<![\w.])printf\s*\("
    r"|\bstd::c(?:out|err)\b"
    r"|(?<![\w.])puts\s*\("
    r"|\bDEBUG_ERROR\b"
    r"|\bDEBUG_FATAL\b"
    r"|\*\s*\(\s*\(\s*u?int\d+_t\s*\*\s*\)\s*0\s*\)"   # deliberate null write
)

#: "path:line" entries allowed to match. Should stay empty: a site that needs
#: an exemption almost always wants InternalError instead.
_ALLOWLIST: set = set()

#: Generated or third-party code under src/ that this project does not own.
_SKIP_DIRS = {"antlr4", "gen"}


def _strip_comments(text: str) -> str:
    """Blank out comments, preserving line numbers and string literals."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _sources():
    for p in sorted(SRC.rglob("*")):
        if p.suffix not in (".cpp", ".h", ".hpp", ".cc"):
            continue
        if _SKIP_DIRS & set(p.relative_to(SRC).parts):
            continue
        yield p


def test_no_raw_output_in_src():
    offenders = []
    for p in _sources():
        code = _strip_comments(p.read_text(errors="replace"))
        for lineno, line in enumerate(code.splitlines(), 1):
            if _BANNED.search(line):
                key = "%s:%d" % (p.relative_to(ROOT), lineno)
                if key not in _ALLOWLIST:
                    offenders.append("%s: %s" % (key, line.strip()))
    assert not offenders, (
        "raw terminal output in src/ -- report a marker, throw InternalError, "
        "or use DEBUG:\n  " + "\n  ".join(offenders))


def test_the_lint_sees_what_it_should():
    """Guard the regex and comment stripper against silently matching nothing."""
    hits = [
        'fprintf(stdout, "x");',
        'fprintf( stderr , "x");',
        'printf("x");',
        'std::cout << 1;',
        'DEBUG_ERROR("x");',
        'DEBUG_FATAL("x");',
        '*((uint32_t *)0) = 1;',
    ]
    misses = [
        'snprintf(buf, sizeof(buf), "x");',
        'vsnprintf(buf, sizeof(buf), fmt, ap);',
        'DEBUG("x");',
        'm_obj.printf(x);',
    ]
    for h in hits:
        assert _BANNED.search(_strip_comments(h)), h
    for m in misses:
        assert not _BANNED.search(_strip_comments(m)), m
    assert not _BANNED.search(_strip_comments('// DEBUG_ERROR("x");'))
    assert not _BANNED.search(_strip_comments('/* printf("x"); */'))
