"""The lossless-tokenization contract, from Python.

The C++ tests (``tests/src/TestFmtTokenStream.cpp``) prove the mechanism.
These prove that the binding did not lose anything on the way across, and they
run the guarantee over real PSS rather than fragments.
"""

import io

import pytest

from pssparser import tokens


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

SOURCES = [
    "",
    "component c { }",
    "component c { }\n",
    "component c {\r\n    int x;\r\n}\r\n",
    "component c {\r    int x;\r}\r",
    "// leading\ncomponent c { /* in */ int x; // trailing\n}\n",
    "component c {   \n\tint x;\t\n}\n",
    "component c { string s = \"a\\\"b\"; }\n",
    "// → 漢字\ncomponent c { }\n",
    "component c { $ ` § int x; }\n",
    "﻿component c { }\n",
    "\x01\x02\x03 }}}} ][ '''' \"\"\"\" ####\n",
    "component c { /* never closed\nint x;\n",
]


@pytest.mark.parametrize("src", SOURCES, ids=range(len(SOURCES)))
def test_tokens_concatenate_to_the_input(src):
    assert tokens.tokenize(src).text == src


@pytest.mark.parametrize("src", SOURCES, ids=range(len(SOURCES)))
def test_offsets_index_the_source_directly(src):
    # start/stop count code points, which is what a Python str counts.  This
    # is the property that lets a caller work in offsets instead of carrying
    # the token text around.
    for t in tokens.tokenize(src):
        assert src[t.start:t.stop + 1] == t.text, t


@pytest.mark.parametrize("src", SOURCES, ids=range(len(SOURCES)))
def test_tokens_tile_the_input_without_gap_or_overlap(src):
    expect = 0
    for i, t in enumerate(tokens.tokenize(src)):
        assert t.index == i
        assert t.start == expect, "gap or overlap at token %d" % i
        expect = t.stop + 1


@pytest.mark.parametrize("src", SOURCES, ids=range(len(SOURCES)))
def test_lines_and_columns_agree_with_the_source(src):
    lines = src.split("\n")
    for t in tokens.tokenize(src):
        assert 1 <= t.line <= len(lines), t
        assert lines[t.line - 1][t.col:t.col + len(t.text.split("\n")[0])] == \
            t.text.split("\n")[0], t


# ---------------------------------------------------------------------------
# The guarantee over real PSS
# ---------------------------------------------------------------------------

def _stdlib_files():
    import pssparser
    return pssparser.get_stdlib_files()


@pytest.mark.parametrize(
    "path", _stdlib_files(), ids=lambda p: p.rsplit("/", 1)[-1])
def test_stdlib_round_trips(path):
    """The core library, byte for byte.

    Small, but it is real PSS written by hand rather than assembled to make a
    test pass, and it is the only such corpus that ships in this repository.
    """
    with open(path, "rb") as fp:
        data = fp.read()

    ts = tokens.tokenize(data)
    assert ts.text.encode("utf-8") == data
    assert ts.num_errors == 0, "core library should lex cleanly"


# ---------------------------------------------------------------------------
# Input forms
# ---------------------------------------------------------------------------

def test_accepts_str_bytes_and_file_objects():
    src = "component c { }\n"
    expected = tokens.tokenize(src).text

    assert tokens.tokenize(src.encode("utf-8")).text == expected
    assert tokens.tokenize(io.BytesIO(src.encode("utf-8"))).text == expected


def test_rejects_input_that_is_not_source():
    with pytest.raises(TypeError):
        tokens.tokenize(42)


def test_invalid_utf8_raises_unicode_decode_error():
    # The C++ layer degrades rather than throwing; the binding turns that into
    # the exception Python already has for this, so a caller's existing
    # `except UnicodeDecodeError` keeps working.
    with pytest.raises(UnicodeDecodeError):
        tokens.tokenize(b"// caf\xe9\ncomponent c { }\n")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def test_trivia_arrives_on_its_own_channels():
    ts = tokens.tokenize("int /* m */ x; // s\n")
    channels = set(t.channel for t in ts)
    assert channels == {
        tokens.CHANNEL_DEFAULT,
        tokens.CHANNEL_WS,
        tokens.CHANNEL_SL_COMMENT,
        tokens.CHANNEL_ML_COMMENT,
    }


def test_code_returns_what_the_parser_would_see():
    ts = tokens.tokenize("int /* m */ x; // s\n")
    assert [t.text for t in ts.code()] == ["int", "x", ";"]


def test_error_tokens_are_not_trivia():
    # Deliberate: a consumer that skips trivia must still see unrecognized
    # text, because ignoring it is exactly how characters get dropped.
    ts = tokens.tokenize("int $ x;")
    err = [t for t in ts if t.is_error]
    assert len(err) == 1
    assert err[0].text == "$"
    assert not err[0].is_trivia
    assert err[0].type == tokens.TYPE_ERROR_CHAR
    assert ts.num_errors == 1


def test_byte_order_mark_is_its_own_token():
    ts = tokens.tokenize("﻿component c { }\n")
    assert ts[0].type == tokens.TYPE_BOM
    assert ts[0].channel == tokens.CHANNEL_BOM
    assert ts[0].text == "﻿"
    assert ts[0].is_trivia
    # A BOM is not damage.
    assert ts.num_errors == 0


def test_tokens_are_immutable():
    t = tokens.tokenize("int x;")[0]
    with pytest.raises(AttributeError):
        t.text = "changed"


def test_stream_is_a_sequence():
    ts = tokens.tokenize("int x;")
    assert len(ts) == len(list(ts))
    assert ts[0] is list(ts)[0]
