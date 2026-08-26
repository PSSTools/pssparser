"""Characterization tests: what the PSS lexer actually does.

These are not tests of correctness.  They record present behavior for the
cases a source-formatting tool has to reason about, so that a later change to
``PSSLexer.g4`` shows up here as a failing test rather than downstream as a
mangled file.  If one of these fails, the question to ask is "was that change
intended", not "what did I break".

Each group notes what depends on the answer.
"""

import pytest

from pssparser import tokens


def types(src, channel=None):
    """(type_name, text) for each token, optionally filtered to *channel*."""
    return [(t.type_name, t.text) for t in tokens.tokenize(src)
            if channel is None or t.channel == channel]


def only(src, text):
    """The single token whose text is *text*."""
    matches = [t for t in tokens.tokenize(src) if t.text == text]
    assert len(matches) == 1, "expected exactly one %r, got %r" % (text, matches)
    return matches[0]


# ---------------------------------------------------------------------------
# `//@` -- the annotation-comment hazard, and its resolution
# ---------------------------------------------------------------------------
#
# A `TOK_COMMENT_AT: '//@'` rule used to exist in the grammar for a
# comment-form annotation.  It was unreachable -- SL_COMMENT matches longer and
# wins -- and it has since been removed outright, because the LRM defines no
# such annotation.
#
# For a formatter this is good news and worth pinning: `//@doc(...)` is an
# ordinary comment on the comment channel, with no special handling anywhere.
# Were it ever restored as a default-channel token, a formatter that treats
# comments as reflowable trivia would start rewriting annotations.

def test_at_comment_is_an_ordinary_single_line_comment():
    for src in ("//@doc(x)\n", "int y; //@doc(x)\n", "// @doc(x)\n"):
        toks = [t for t in tokens.tokenize(src) if t.type_name == "SL_COMMENT"]
        assert len(toks) == 1, src
        assert toks[0].channel == tokens.CHANNEL_SL_COMMENT, src


def test_no_comment_at_token_type_exists():
    # The sentinel for the rule's return.  If this fails, §4.2 of the formatter
    # design is live again and its hazard analysis has to be reinstated.
    assert not any(t.type_name == "TOK_COMMENT_AT"
                   for t in tokens.tokenize("//@doc(x)\nint y;\n"))


def test_at_comment_inside_a_string_is_string_content():
    t = only('string s = "//@ x";', '"//@ x"')
    assert t.type_name == "DOUBLE_QUOTED_STRING"
    assert t.channel == tokens.CHANNEL_DEFAULT


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def test_single_line_comment_owns_its_newline():
    # Consequential.  Blank-line counting after a trailing comment is off by
    # one unless the consumer knows the newline is inside the comment token
    # rather than in the whitespace run that follows it.
    assert only("// c\nint x;", "// c\n").type_name == "SL_COMMENT"


def test_single_line_comment_at_eof_needs_no_newline():
    assert only("int x; // end", "// end").type_name == "SL_COMMENT"


def test_block_comments_do_not_nest():
    # `/* a /* b */ c */` ends at the FIRST `*/`.  A formatter must not assume
    # it can wrap arbitrary code in a block comment, and a "comment out this
    # region" feature built on that assumption produces broken source.
    assert types("/* a /* b */ c */", tokens.CHANNEL_ML_COMMENT) == [
        ("ML_COMMENT", "/* a /* b */")]
    assert types("/* a /* b */ c */", tokens.CHANNEL_DEFAULT) == [
        ("ID", "c"), ("TOK_ASTERISK", "*"), ("TOK_DIV", "/")]


def test_unterminated_block_comment_lexes_as_operators():
    """The most dangerous case in this file.

    `/* a` with no close does **not** produce an error token.  It produces
    `TOK_DIV`, `TOK_ASTERISK`, `ID` -- three perfectly ordinary tokens, and
    ``num_errors`` stays 0.

    A formatter must therefore not use ``num_errors`` as its "is this file
    sane" check: this input reports clean, and any rule that changes spacing
    around `/` or `*` would turn `/*` into `/ *` and silently uncomment the
    rest of the file.  Detecting it needs the parser, not the lexer.
    """
    ts = tokens.tokenize("/* a")
    assert ts.num_errors == 0
    assert [t.type_name for t in ts.code()] == [
        "TOK_DIV", "TOK_ASTERISK", "ID"]


def test_tabs_inside_comments_are_preserved():
    assert only("//\tx\n", "//\tx\n").text == "//\tx\n"


# ---------------------------------------------------------------------------
# Line endings and file boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eol", ["\n", "\r\n", "\r"])
def test_every_line_ending_round_trips(eol):
    src = "int x;%sint y;%s" % (eol, eol)
    assert tokens.tokenize(src).text == src


def test_crlf_stays_inside_one_whitespace_token():
    # It matters that CR and LF are not split across tokens: a formatter that
    # rewrites whitespace replaces the token wholesale, and a lone surviving
    # CR would be a stray byte in the output.
    assert only("int\r\nx", "\r\n").type_name == "WS"


def test_line_numbering_counts_lf_not_cr():
    # ANTLR advances the line on LF only, so under lone-CR endings every token
    # reports line 1.  A formatter that reports diagnostics by line has to know
    # this; the formatter itself does not care, because it works in offsets.
    ts = tokens.tokenize("int x;\rint y;\r")
    assert set(t.line for t in ts) == {1}


def test_absent_final_newline_is_absent_in_the_tokens():
    assert tokens.tokenize("int x;").text == "int x;"
    assert tokens.tokenize("int x;\n").text == "int x;\n"


def test_leading_byte_order_mark_is_a_token_of_its_own():
    ts = tokens.tokenize("﻿int x;")
    assert ts[0].type_name == "BOM"
    assert ts[0].text == "﻿"
    # Offsets after it are shifted by one code point, and so are columns on
    # line 1 -- the BOM occupies a position in the file like anything else.
    assert ts[1].start == 1
    assert ts[1].col == 1


def test_byte_order_mark_elsewhere_is_not_a_bom():
    # Only a leading BOM is an encoding artifact.  One in the middle of a file
    # is a stray character, and is reported as one.
    ts = tokens.tokenize("int ﻿ x;")
    assert [t.type_name for t in ts if t.is_error] == ["ERROR_CHAR"]
    assert ts.num_errors == 1


# ---------------------------------------------------------------------------
# Escaped identifiers
# ---------------------------------------------------------------------------
#
# `ESCAPED_ID : '\\' ('!'..'~')+ ~[ \r\t\n]*` -- a backslash, then
# printable characters, terminated by whitespace.  The terminating whitespace
# is NOT part of the token, which means a formatter may not delete it: doing so
# would run the identifier into whatever follows.

def test_escaped_identifier_is_one_token():
    assert only("int \\abc def;", "\\abc").type_name == "ESCAPED_ID"


def test_escaped_identifier_may_contain_punctuation():
    assert only("component \\$weird-id$ { }", "\\$weird-id$").type_name == \
        "ESCAPED_ID"


@pytest.mark.parametrize("ws", [" ", "\n", "\t", "\r"])
def test_escaped_identifier_is_terminated_by_whitespace(ws):
    # The whitespace terminator is load-bearing: `\abc def` and `\abcdef` are
    # different programs, so the space after an ESCAPED_ID is not optional.
    src = "int \\abc%sdef;" % ws
    ts = tokens.tokenize(src)
    assert [t.text for t in ts.code()] == ["int", "\\abc", "def", ";"]
    assert ts.text == src


# ---------------------------------------------------------------------------
# Triple-quoted strings and `exec` target templates
# ---------------------------------------------------------------------------
#
# This group answers the question that decides whether a formatter can treat
# target-template payloads as verbatim at all.  The answer is yes: the payload
# arrives as ONE token whose text is byte-identical to the source.  Nothing
# inside it is tokenized, so nothing inside it can be reformatted by accident,
# and preserving it is a matter of emitting the token unchanged.

def test_exec_target_template_payload_is_a_single_token():
    src = ('component c {\n'
           '  exec body C = """\n'
           '     printf("hi %d", {{x}});\n'
           '  """;\n'
           '}\n')
    payload = [t for t in tokens.tokenize(src)
               if t.type_name == "TRIPLE_DOUBLE_QUOTED_STRING"]
    assert len(payload) == 1
    assert payload[0].text == ('"""\n'
                               '     printf("hi %d", {{x}});\n'
                               '  """')


def test_triple_quoted_content_is_byte_identical():
    for body in ["", "x", "a\nb", "  indented  ", "\t\ttabs", "'quotes'",
                 '"one" ""two', "// not a comment", "/* not a comment */"]:
        src = 'a = """%s""";' % body
        assert only(src, '"""%s"""' % body).text == '"""%s"""' % body


def test_backslash_does_not_escape_a_closing_triple_quote():
    # PSS 4.7: a triple-quoted string has no escape character.  `"""x\"""`
    # therefore ends at the `"""`, with content `x\`.
    assert only('a = """x\\""";', '"""x\\"""').type_name == \
        "TRIPLE_DOUBLE_QUOTED_STRING"


def test_ordinary_string_escapes_are_inside_the_token():
    assert only('s = "a\\"b";', '"a\\"b"').type_name == "DOUBLE_QUOTED_STRING"


# ---------------------------------------------------------------------------
# `compile if`
# ---------------------------------------------------------------------------

def test_both_compile_if_branches_are_tokenized():
    # The reason to tokenize rather than read the AST: AST construction
    # evaluates the condition and discards the losing branch.  A formatter must
    # reproduce both, so it must never see that evaluation happen.
    src = ('compile if (false) {\n'
           '  component taken { }\n'
           '} else {\n'
           '  component not_taken { }\n'
           '}\n')
    texts = [t.text for t in tokens.tokenize(src)]
    assert "taken" in texts
    assert "not_taken" in texts
