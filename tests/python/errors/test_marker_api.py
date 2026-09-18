"""Tests for the widened marker dict: extent, related, id (E-1)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect, find_markers  # noqa: E402


def test_syntax_error_has_positive_extent():
    _root, markers = parse_collect('struct S { int x }')
    errs = find_markers(markers, severity="error")
    assert len(errs) == 1
    assert errs[0]["extent"] > 0


def test_marker_dict_has_related_key_even_when_empty():
    _root, markers = parse_collect('struct S { int x }')
    errs = find_markers(markers, severity="error")
    assert "related" in errs[0]
    assert isinstance(errs[0]["related"], list)


def test_marker_id_is_a_stable_pss_code():
    _root, markers = parse_collect('struct S { int x }')
    errs = find_markers(markers, severity="error")
    assert errs[0]["code"].startswith("PSS")


def test_full_marker_dict_has_nine_keys():
    """`fix` is the ninth, and is present only when there is one to offer.

    A missing ';' has one -- insert the character -- so this input carries it.
    A marker with no machine-applicable repair omits the key entirely rather
    than carrying an empty one; see `test_marker_without_a_fix_omits_the_key`.
    """
    _root, markers = parse_collect('struct S { int x }')
    errs = find_markers(markers, severity="error")
    expected = {
        "severity", "message", "file", "line", "col", "extent", "related",
        "code", "fix",
    }
    assert set(errs[0].keys()) == expected
    assert errs[0]["fix"]["replacement"] == ";"
    # An insertion, not a replacement: the ';' goes *between* two characters,
    # so the span it covers is empty.
    assert errs[0]["fix"]["extent"] == 0


def test_marker_without_a_fix_omits_the_key():
    _root, markers = parse_collect('struct { int x; }')
    errs = find_markers(markers, severity="error")
    # "expected identifier" -- there is no way to invent the name the user
    # meant, so no fix is offered rather than a guess.
    assert "fix" not in errs[0]
