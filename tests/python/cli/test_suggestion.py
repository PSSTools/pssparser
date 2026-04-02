"""Unit tests for pssparser.cli.suggestion."""
import pytest
from pssparser.cli.suggestion import extract_suggestion, levenshtein, suggest


# -- extract_suggestion -----------------------------------------------------

class TestExtractSuggestion:
    def test_basic(self):
        msg = "unknown type 'Pont'; did you mean 'Point'?"
        assert extract_suggestion(msg) == "Point"

    def test_no_suggestion(self):
        msg = "unknown type 'CompletelyUnknownXYZ'"
        assert extract_suggestion(msg) is None

    def test_without_question_mark(self):
        msg = "unknown type 'Pont'; did you mean 'Point'"
        assert extract_suggestion(msg) == "Point"

    def test_identifier_message(self):
        msg = "unknown identifier 'bogus'; did you mean 'bonus'?"
        assert extract_suggestion(msg) == "bonus"


# -- levenshtein ------------------------------------------------------------

class TestLevenshtein:
    def test_identical(self):
        assert levenshtein("abc", "abc") == 0

    def test_empty(self):
        assert levenshtein("", "abc") == 3
        assert levenshtein("abc", "") == 3

    def test_both_empty(self):
        assert levenshtein("", "") == 0

    def test_single_insert(self):
        assert levenshtein("abc", "abcd") == 1

    def test_single_delete(self):
        assert levenshtein("abcd", "abc") == 1

    def test_single_sub(self):
        assert levenshtein("abc", "aXc") == 1

    def test_case_counts(self):
        assert levenshtein("ABC", "abc") == 3

    def test_transposition(self):
        # Levenshtein (not Damerau): swap = 2 edits
        assert levenshtein("ab", "ba") == 2

    def test_realistic_typo(self):
        assert levenshtein("DataPacket", "DataPaket") == 1


# -- suggest ----------------------------------------------------------------

class TestSuggest:
    def test_close_match(self):
        assert suggest("Pont", ["Point", "Line", "Circle"]) == "Point"

    def test_no_match_beyond_threshold(self):
        assert suggest("xyz", ["abcdefgh", "ijklmnop"]) is None

    def test_exact_match_skipped(self):
        # edit distance 0 is the same string -- should not suggest itself
        assert suggest("Point", ["Point", "Line"]) is None

    def test_custom_max_dist(self):
        # "ab" -> "abc" distance 1, but max_dist=0 rejects it
        assert suggest("ab", ["abc"], max_dist=0) is None
        assert suggest("ab", ["abc"], max_dist=1) == "abc"

    def test_case_tiebreak(self):
        # "Abc" -> "Abx" (dist 1), "abc" (dist 1, case-insensitive match).
        # Tiebreak prefers the case-insensitive match.
        result = suggest("Abc", ["Abx", "abc"])
        assert result == "abc"

    def test_empty_candidates(self):
        assert suggest("abc", []) is None
