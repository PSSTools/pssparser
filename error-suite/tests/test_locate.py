"""The approximate lexer behind `--tolerance token:N`."""
from __future__ import annotations

import pytest

from pss_errsuite.locate import Tolerance, token_distance, token_positions

SRC = "struct s {\n    int a\n    int b;\n}\n"


def test_token_positions_skip_whitespace_and_comments():
    src = "int /* c */ a; // trailing\nint b;\n"
    assert token_positions(src) == [
        (1, 1), (1, 13), (1, 14), (2, 1), (2, 5), (2, 6)]


def test_based_literals_are_one_token():
    assert token_positions("bit[8] a = 8'h20;") == [
        (1, 1), (1, 4), (1, 5), (1, 6), (1, 8), (1, 10), (1, 12), (1, 17)]


def test_strings_are_one_token_even_with_spaces():
    assert token_positions('a = "x y z";') == [
        (1, 1), (1, 3), (1, 5), (1, 12)]


def test_distance_counts_tokens_not_columns():
    # Distance is "how many token starts lie between these two positions".
    # From just past `int a` (2:10) to the `int` that opens the next line
    # (3:5) there are none -- which is why a missing ';' reported at the head
    # of the following line counts as located under every token policy.  The
    # column gap between them is irrelevant, and so is how long the
    # identifiers happen to be.
    assert token_distance(SRC, (2, 10), (3, 5)) == 0
    # Two tokens further on (`b`, then `;`) is two.
    assert token_distance(SRC, (2, 10), (3, 10)) == 2


def test_distance_is_symmetric():
    assert token_distance(SRC, (3, 10), (2, 10)) == 2


@pytest.mark.parametrize("spec", ["exact", "line", "token:0", "token:5"])
def test_tolerance_round_trips_its_spec(spec):
    assert Tolerance(spec).spec == spec


@pytest.mark.parametrize("spec", ["", "tokens:2", "token:x", "close enough"])
def test_bad_tolerance_spec_is_rejected(spec):
    with pytest.raises(ValueError):
        Tolerance(spec)


def test_no_location_is_never_accepted():
    assert not Tolerance("line").accepts(SRC, (2, 5), None)


def test_line_tolerance_ignores_the_column():
    assert Tolerance("line").accepts(SRC, (2, 5), (2, 99))
    assert not Tolerance("line").accepts(SRC, (2, 5), (3, 5))


def test_a_line_only_location_falls_back_to_line_comparison():
    """Some tools report a line and no column.  Under `token:N` that cannot be
    measured in tokens, so it is judged on the line -- generously, since the
    missing column is the tool's limitation and not evidence of error."""
    assert Tolerance("token:2").accepts(SRC, (2, 5), (2, None))
    assert not Tolerance("token:2").accepts(SRC, (2, 5), (3, None))
