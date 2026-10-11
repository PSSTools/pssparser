"""
The lint engine's regex engine (lint-core-plan.md C1.4).

CEL's `matches` is RE2 syntax with RE2's linear-time guarantee. The engine
(`src/lint/regex/`) is a Thompson NFA over a subset of that syntax, simulated
breadth-first; anything outside the subset is refused when the pattern is
compiled. Reached through the private hook `regex_search(pattern, text)`.

Correctness is checked three ways: hand-written vectors for each construct,
a differential test against Python's `re` on generated patterns from the
syntax the two share, and the step count on pathological patterns.
"""
import random
import re

import pytest


@pytest.fixture(scope="module")
def search(factory):
    hooks = factory._lintTestHooks()
    return hooks.regex_search


def _matches(search, pat, text):
    r = search(pat, text)
    assert r["ok"], r
    return r["match"]


# ------------------------------------------------------------- vectors ----

@pytest.mark.parametrize("pat,text,match", [
    # literals, unanchored search
    ("b+", "abbc", True), ("abc", "xabcx", True), ("abd", "abc", False), ("", "", True),
    ("", "abc", True),
    # anchors: $ is the end of text unless (?m), never before a final newline
    ("^b", "abc", False), ("^a", "abc", True), ("c$", "abc", True), ("c$", "abc\n", False),
    ("(?m)c$", "abc\n", True), ("(?m)^b$", "a\nb\nc", True), ("^b$", "a\nb\nc", False),
    ("\\Aa", "ab", True), ("\\Ab", "ab", False), ("b\\z", "ab", True), ("a\\z", "ab", False),
    ("(?m)\\Ab", "a\nb", False),
    # word boundaries
    ("\\bfoo\\b", "a foo b", True), ("\\bfoo\\b", "afoob", False), ("\\Boo\\B", "afoob", True),
    ("\\b", "", False), ("\\B", "", True), ("\\b", "a", True),
    # dot and flags
    ("a.c", "a\nc", False), ("(?s)a.c", "a\nc", True), ("a.c", "aéc", True),
    ("(?i)HELLO", "say hello", True), ("(?i:H)ELLO", "hELLO", True), ("(?i:H)ELLO", "hello", False),
    ("(?i)[a-c]+x", "ABCX", True), ("(?-i)a", "A", False), ("(?is)A.B", "a\nb", True),
    # classes
    ("[[:digit:]]{2,3}$", "ab123", True), ("[^a-z]", "abc1", True), ("[^a-z]", "abc", False),
    ("[a\\-z]", "-", True), ("[]a]", "]", True), ("[^]a]", "]", False), ("[\\d.]+", "1.5", True),
    ("\\d", "x9", True), ("\\D", "99", False), ("\\w+", "_a1", True), ("\\W", "abc", False),
    ("\\s", "a\tb", True), ("\\S", " \t", False), ("[[:^alpha:]]", "ab", False),
    ("[[:upper:]][[:lower:]]", "xAb", True), ("[[:xdigit:]]+$", "beef", True),
    ("[é]", "café", True), ("[^é]", "é", False), ("é+", "xééy", True), ("[α-ω]", "β", True),
    # escapes
    ("\\x41", "A", True), ("\\x{e9}", "é", True), ("\\x{1F600}", "😀", True), ("\\.", "a", False),
    ("\\n", "a\nb", True), ("\\t", "\t", True), ("\\\\", "\\", True),
    ("\\Q.*\\E", "abc", False), ("\\Q.*\\E", "a.*", True), ("a\\Q", "a", True),
    # groups, alternation
    ("(a)(b)?c", "ac", True), ("(?:ab)+$", "abab", True), ("(?P<n>a)b", "ab", True),
    ("(?<n>a)b", "ab", True), ("a|bc|", "zzz", True), ("x(a|bc)y", "xbcy", True),
    ("x(a|bc)y", "xby", False), ("(|a)b", "b", True),
    # repetition
    ("a{3}", "aa", False), ("a{3}", "aaa", True), ("a{2,}", "a", False), ("a{2,}", "aaaa", True),
    ("^a{1,2}$", "aaa", False), ("^a*?$", "aaa", True), ("^a+?b", "aab", True), ("x{", "x{", True),
    ("x{a}", "x{a}", True), ("x{1,", "x{1,", True), ("^(ab){0}c", "c", True), ("(?U)a+", "a", True),
])
def test_vectors(search, pat, text, match):
    assert _matches(search, pat, text) is match


# ------------------------------------------------------------ refusals ----

@pytest.mark.parametrize("pat,offset,msg", [
    ("a(?=b)", 1, "lookahead is not supported (RE2 syntax)"),
    ("a(?!b)", 1, "lookahead is not supported (RE2 syntax)"),
    ("(?<=a)b", 0, "lookbehind is not supported (RE2 syntax)"),
    ("(?<!a)b", 0, "lookbehind is not supported (RE2 syntax)"),
    ("(?>a)", 0, "atomic groups are not supported (RE2 syntax)"),
    ("(a)\\1", 3, "backreferences are not supported (RE2 syntax)"),
    ("\\pL", 0, "Unicode character classes (\\p, \\P) are not supported"),
    ("\\P{Greek}", 0, "Unicode character classes (\\p, \\P) are not supported"),
    ("a*+", 2, "possessive quantifiers are not supported (RE2 syntax)"),
    ("a**", 2, "bad repetition operator"),
    ("*a", 0, "missing argument to repetition operator '*'"),
    ("a|+", 2, "missing argument to repetition operator '+'"),
    ("a{2000}", 1, "counts above 1000 are not allowed"),
    ("a{3,2}", 1, "minimum is larger than maximum"),
    ("(a", 0, "missing closing ')'"),
    ("a)", 1, "unexpected ')'"),
    ("[a", 0, "missing closing ']'"),
    ("[z-a]", 1, "the end is before the start"),
    ("[[:nope:]]", 1, "invalid character class name"),
    ("a\\", 1, "trailing backslash"),
    ("\\q", 0, "invalid escape sequence '\\q'"),
    ("\\x4", 0, "two hexadecimal digits"),
    ("\\x{110000}", 0, "out of the Unicode range"),
    ("\\u00e9", 0, "invalid escape sequence '\\u'"),
    ("(?P<a-b>x)", 0, "invalid named group"),
    ("(?)", 0, "missing flags"),
    ("(?#c)", 0, "invalid or unsupported group syntax"),
    ("(" * 40 + "a" + ")" * 40, 32, "groups nest too deeply"),
])
def test_refused(search, pat, offset, msg):
    r = search(pat, "")
    assert not r["ok"]
    assert msg in r["error"]["message"]
    assert r["error"]["offset"] == offset


def test_size_limit(search):
    # Repetition multiplies the program: refused at compile time, not run.
    r = search("(a{1000}){1000}", "")
    assert not r["ok"]
    assert r["error"]["message"] == "regular expression is too large"


def test_nesting_limit_edge(search):
    assert search("(" * 32 + "a" + ")" * 32, "a")["ok"]


# --------------------------------------------------------- linear time ----

@pytest.mark.parametrize("pat,unit", [
    ("(a*)*b", "a"), ("(a|a)*b", "a"), ("(a+)+$", "a"), ("(x+x+)+y", "x"),
    ("^(\\w+\\s?)*$", "ab "), ("(a|aa)*c", "a"), ("(.*a){12}b", "a"),
])
def test_linear_time(search, pat, unit):
    # Charged per NFA state visited, the step count is the budget's measure.
    # Linear: 10x the text is 10x the steps, give or take the edges.
    s1 = search(pat, unit * 1000)["steps"]
    s2 = search(pat, unit * 10000)["steps"]
    assert 9.5 * s1 <= s2 <= 10.5 * s1
    # And a constant per character, bounded by the program size.
    size = search(pat, "")["size"]
    assert s2 <= 2 * size * len(unit * 10000)


# -------------------------------------------------------- differential ----

class _Gen:
    """Patterns from the syntax RE2 and Python's `re` agree on, over a small
    alphabet so that matches are common."""

    ATOMS = ["a", "b", "c", ".", "[ab]", "[^a]", "[a-c]", "\\d", "\\w", "\\s", "\\.", "x"]

    def __init__(self, rnd):
        self.r = rnd

    def gen(self, d=0):
        k = self.r.random()
        if d > 3 or k < 0.35:
            return self.r.choice(self.ATOMS)
        if k < 0.55:
            return self.gen(d + 1) + self.gen(d + 1)
        if k < 0.65:
            return "%s|%s" % (self.gen(d + 1), self.gen(d + 1))
        if k < 0.8:
            return "(%s)" % self.gen(d + 1) + self.r.choice(["*", "+", "?", "*?", "{2}", "{1,3}", ""])
        if k < 0.9:
            return "(?:%s)%s" % (self.gen(d + 1), self.r.choice(["*", "+", "?", "{0,2}"]))
        return self.r.choice(["^", "$", "\\b", "\\B"]) + self.gen(d + 1)

    def text(self):
        return "".join(self.r.choice("abcx1 .\n") for _ in range(self.r.randint(0, 10)))


def _py(pat):
    # RE2's `$` without (?m) is the end of the text; Python's also matches
    # before a final newline, so it becomes Python's `\Z`. With (?m) the two
    # agree.
    if not pat.startswith("(?m)"):
        pat = pat.replace("$", "\\Z")
    return re.compile(pat, re.ASCII)


def test_differential_against_python_re(search):
    rnd = random.Random(20261010)
    g = _Gen(rnd)
    bad = []
    n = 0
    for _ in range(1500):
        pat = g.gen()
        flags = rnd.choice(["", "", "(?i)", "(?s)", "(?m)"])
        pat = flags + pat
        py = _py(pat)
        for _ in range(4):
            t = g.text()
            if not t and "\\B" in pat:
                # RE2: \B matches in the empty text (no word character on
                # either side); Python's \B never matches it (before 3.14).
                continue
            ours = search(pat, t)
            assert ours["ok"], (pat, ours)
            if ours["match"] != bool(py.search(t)):
                bad.append((pat, t, ours["match"]))
            n += 1
    assert not bad, "%d of %d disagree, e.g. %r" % (len(bad), n, bad[:5])
