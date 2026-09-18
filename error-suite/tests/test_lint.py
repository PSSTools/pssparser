"""Message lints, lifted from pssparser's own G3/G6/G7 checks.

Applied to another tool's output these are observations, not failures -- but
the predicates have to behave identically in both callers, which is why there
is one implementation and this module tests it directly.
"""
from __future__ import annotations

import pytest

from pss_errsuite.lint import (G3_JARGON, G6_NO_CODE, G7_LENGTH, G7_NEWLINE,
                               L_BARE_TOKEN, L_NO_LOCATION, jargon_violation,
                               lint_message)


@pytest.mark.parametrize("message", [
    "mismatched input ';' expecting ID",
    "no viable alternative at input 'struct'",
    "extraneous input '}' expecting {'::', ID}",
    "expecting {'::', ID, ESCAPED_ID}",
])
def test_antlr_phrasing_is_jargon(message):
    assert jargon_violation(message)


@pytest.mark.parametrize("message", [
    "expected ';' before '}'",
    "unknown type 'gadget_s'",
    "expected '{' before '}'",          # the historical false positive
    "duplicate declaration of 'a'; previously declared here",
])
def test_good_messages_are_not_jargon(message):
    assert not jargon_violation(message)


def test_lexer_token_names_are_jargon_when_the_caller_supplies_them():
    """Rule names like `expression` are ordinary English and deliberately not
    matched; upper-case token names are unambiguous."""
    assert jargon_violation("unexpected ESCAPED_ID here", ["ESCAPED_ID", "ID"])
    assert not jargon_violation("unexpected expression here",
                                ["ESCAPED_ID", "ID"])


def test_length_and_newline():
    assert lint_message("x" * 121) == [G7_LENGTH]
    assert G7_NEWLINE in lint_message("two\nlines")


def test_bare_token_or_rule_name():
    assert L_BARE_TOKEN in lint_message("';'")
    assert L_BARE_TOKEN in lint_message("ID")
    assert L_BARE_TOKEN not in lint_message("expected ';'")


def test_missing_location_and_code_are_lints():
    out = lint_message("something went wrong", has_location=False,
                       has_code=False)
    assert L_NO_LOCATION in out and G6_NO_CODE in out


def test_a_good_message_lints_clean():
    assert lint_message("cannot assign 'string' to field 'a' of type 'bit[8]'"
                        ) == []


def test_diagnostic_wrapper_reads_location_and_code_off_the_diagnostic():
    from pss_errsuite.adapters.base import Diagnostic
    from pss_errsuite.lint import lint_diagnostic
    d = Diagnostic(severity="error", message="mismatched input ';'",
                   file="a.pss", line=1, col=1, code="X1")
    assert lint_diagnostic(d) == [G3_JARGON]
    d2 = Diagnostic(severity="error", message="fine")
    assert set(lint_diagnostic(d2)) == {L_NO_LOCATION, G6_NO_CODE}
