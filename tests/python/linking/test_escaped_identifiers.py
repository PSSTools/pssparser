"""Escaped identifiers: ``\\cpu3`` names the same thing as ``cpu3``.

LRM 4.3 is explicit about what the backslash is and is not:

    Neither the leading backslash character nor the terminating white space is
    considered to be part of the identifier.  Therefore, an escaped identifier
    ``\\cpu3`` is treated the same as a non-escaped identifier ``cpu3``.

So the backslash is *spelling*, not name.  It used to be kept as part of the
name, which made ``\\cpu3`` and ``cpu3`` two distinct identifiers.  Nothing in
the project model noticed, because every escaped name there is spelled escaped
at both its declaration and its uses -- correct by consistency rather than by
rule, and silently wrong the moment the two spellings differ.

The tests below therefore cross the spellings deliberately: declare escaped and
reference plain, and the reverse.  A resolver that merely stores the raw token
text passes neither.

Note what is *not* a defect here: an escaped identifier runs to the next
whitespace, so ``int \\cpu3;`` names the field ``cpu3;`` and swallows the
terminator.  That is what the LRM specifies (and what SystemVerilog does), so
the trailing space is required, not optional.  ``test_terminating_whitespace_is
_required`` pins that rather than leaving it to look like an oversight.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from isolation import assert_clean, run_isolated  # noqa: E402

from ..test_helpers import parse_pss
from ..template_helpers import lookup


# ---------------------------------------------------------------------------
# The identity rule: spelling does not change the name
# ---------------------------------------------------------------------------

def test_escaped_declaration_is_visible_under_the_plain_name():
    """The LRM's own example: declare ``\\cpu3``, reference ``cpu3``."""
    assert_clean(
        r"package p { component C { int \cpu3 ; exec init_down { cpu3 = 1; } } }")


def test_plain_declaration_is_visible_under_the_escaped_name():
    """The converse: declare ``cpu3``, reference ``\\cpu3``."""
    assert_clean(
        r"package p { component C { int cpu3; exec init_down { \cpu3 = 1; } } }")


def test_escaped_declaration_and_escaped_reference():
    """Both spelled escaped -- the shape the project model actually uses.

    This one passed even when the backslash was part of the name, which is
    exactly why the defect stayed invisible for so long.
    """
    assert_clean(
        r"package p { component C { int \cpu3 ; exec init_down { \cpu3 = 1; } } }")


def test_the_stored_name_has_no_backslash():
    """Assert the name directly, not just that resolution happens to work.

    Resolution succeeding is consistent with storing ``\\my_s`` everywhere and
    matching it against itself.  Looking the type up under its *plain* name is
    what distinguishes a normalized name from a consistently-mangled one.
    """
    root = parse_pss(r"package p { struct \my_s { int f; } }")
    node = lookup(root, "p::my_s")
    assert node is not None


@pytest.mark.parametrize(
    "decl,ref",
    [
        (r"\my_s", "my_s"),
        ("my_s", r"\my_s "),
        (r"\my_s", r"\my_s "),
    ],
    ids=["escaped-decl", "escaped-ref", "both-escaped"],
)
def test_type_names_resolve_across_spellings(decl, ref):
    assert_clean(
        r"package p { struct %s { int f; } component C { %s x; } }" % (decl, ref))


@pytest.mark.parametrize(
    "decl,call",
    [
        (r"\init ", r"\init "),
        (r"\init ", "init"),
        ("init_f", r"\init_f "),
    ],
    ids=["escaped-both", "escaped-decl", "escaped-call"],
)
def test_function_names_resolve_across_spellings(decl, call):
    """``\\init`` is the model's real case: escaping a pre-3.1 keyword."""
    assert_clean(
        r"package p { function void %s(int a); "
        r"component C { exec init_down { %s(1); } } }" % (decl, call))


# ---------------------------------------------------------------------------
# What escaping is *for*
# ---------------------------------------------------------------------------

def test_escaping_admits_a_name_that_would_otherwise_be_a_keyword():
    """The entire point of the construct.

    ``component`` cannot be written bare as a field name; escaped, it is an
    ordinary identifier.  This is the same reason the project model writes
    ``\\init`` -- ``init`` was a keyword before PSS 3.1.
    """
    assert_clean(
        r"package p { component C { int \component ; "
        r"exec init_down { \component = 1; } } }")


def test_punctuation_is_legal_inside_an_escaped_name():
    """LRM 4.3 lists ``\\busa+index`` among its legal examples.

    Every printable character up to the terminating whitespace is part of the
    name, including characters that could never appear in a bare identifier.
    """
    assert_clean(
        r"package p { component C { int \busa+index ; "
        r"exec init_down { \busa+index = 1; } } }")


def test_terminating_whitespace_is_required():
    """``int \\cpu3;`` swallows the semicolon -- and that is correct.

    The name runs to the next whitespace, so this declares a field called
    ``cpu3;`` and then reaches ``}`` with no terminator.  Rejecting it is
    conformant; the test exists so the requirement is recorded rather than
    rediscovered as a suspected bug.
    """
    res = run_isolated(r"package p { component C { int \cpu3; } }")
    assert not res.ok, (
        "an escaped identifier must be terminated by whitespace, so this "
        "should not have parsed: %s" % res.describe())
    assert not res.crashed, res.describe()
