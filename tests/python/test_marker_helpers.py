"""
Self-tests for the marker (diagnostic) assertion helpers in test_helpers.

These exist because the helpers are themselves test infrastructure: several
PSS 3.1 items are specified as *warnings that still parse*, and are only
testable through this layer. A silently-broken helper would turn those tests
into no-ops, so the helpers get their own coverage of hit, miss, and each
filter dimension.

The PSS fragments below are chosen because they exercise diagnostics that
already exist today:

* ``duplicate declaration of 'a'`` -- PSS003, severity *warning*, emitted by
  the linker while the parse still succeeds. This is the only construct in the
  current implementation with the shape PSS 3.1 deprecations will take.
* ``unknown type 'Nope'`` -- PSS002, severity *error*, aborts the link.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_helpers import (  # noqa: E402
    parse_collect,
    find_markers,
    assert_marker,
    assert_no_marker,
    assert_parse_ok_with_warning,
    assert_no_errors,
)
from pssparser import Parser  # noqa: E402


# PSS that links successfully but emits a warning
DUP_WARNING = "component C { int a; int a; }"

# PSS that fails to link with an error
UNKNOWN_TYPE_ERROR = "component C { Nope x; }"

# PSS that is entirely clean
CLEAN = "component C { int a; }"


# =============================================================================
# parse_collect
# =============================================================================

def test_parse_collect_clean_returns_root_and_no_markers():
    root, markers = parse_collect(CLEAN)
    assert root is not None
    assert markers == []


def test_parse_collect_warning_returns_root_and_marker():
    """A warning must not suppress the root -- the parse still succeeded."""
    root, markers = parse_collect(DUP_WARNING)
    assert root is not None
    assert len(markers) == 1
    assert markers[0]["severity"] == "warning"


def test_parse_collect_error_returns_none_and_marker():
    """An error yields no root, but the markers must still be recoverable."""
    root, markers = parse_collect(UNKNOWN_TYPE_ERROR)
    assert root is None
    assert any(m["severity"] == "error" for m in markers)


def test_parse_collect_does_not_raise_on_error():
    parse_collect(UNKNOWN_TYPE_ERROR)  # must not raise


def test_parse_collect_assigns_marker_codes():
    _, markers = parse_collect(UNKNOWN_TYPE_ERROR)
    assert markers[0]["code"] == "PSS002"


def test_parse_collect_marker_has_location():
    _, markers = parse_collect(UNKNOWN_TYPE_ERROR)
    m = markers[0]
    assert m["file"] == "test.pss"
    assert m["line"] == 1
    assert m["col"] > 0


def test_parse_collect_honors_filename():
    _, markers = parse_collect(UNKNOWN_TYPE_ERROR, filename="other.pss")
    assert markers[0]["file"] == "other.pss"


def test_parse_collect_accepts_explicit_parser():
    parser = Parser()
    root, markers = parse_collect(CLEAN, parser=parser)
    assert root is not None
    assert markers == []


# =============================================================================
# find_markers filters
# =============================================================================

MARKERS = [
    {"severity": "error", "message": "unknown type 'Foo'", "code": "PSS002"},
    {"severity": "warning", "message": "duplicate declaration of 'a'", "code": "PSS003"},
    {"severity": "warning", "message": "something else", "code": None},
]


def test_find_markers_no_filter_returns_all():
    assert find_markers(MARKERS) == MARKERS


def test_find_markers_by_id():
    assert find_markers(MARKERS, marker_id="PSS002") == [MARKERS[0]]


def test_find_markers_by_severity():
    assert find_markers(MARKERS, severity="warning") == MARKERS[1:]


def test_find_markers_by_text_is_case_insensitive():
    assert find_markers(MARKERS, text="DUPLICATE") == [MARKERS[1]]


def test_find_markers_filters_are_conjunctive():
    assert find_markers(MARKERS, severity="warning", marker_id="PSS002") == []


def test_find_markers_miss_returns_empty():
    assert find_markers(MARKERS, marker_id="PSS999") == []


# =============================================================================
# assert_marker
# =============================================================================

def test_assert_marker_by_id():
    m = assert_marker(UNKNOWN_TYPE_ERROR, marker_id="PSS002")
    assert m["code"] == "PSS002"


def test_assert_marker_by_severity():
    assert_marker(UNKNOWN_TYPE_ERROR, severity="error")


def test_assert_marker_by_text():
    assert_marker(UNKNOWN_TYPE_ERROR, text="unknown type")


def test_assert_marker_returns_the_matching_marker():
    m = assert_marker(DUP_WARNING, severity="warning")
    assert "duplicate" in m["message"]


def test_assert_marker_fails_when_absent():
    with pytest.raises(AssertionError, match="Expected a marker matching"):
        assert_marker(CLEAN, severity="error")


def test_assert_marker_failure_lists_actual_markers():
    """The failure message must show what *was* emitted, or it is undiagnosable."""
    with pytest.raises(AssertionError, match="unknown type"):
        assert_marker(UNKNOWN_TYPE_ERROR, marker_id="PSS999")


def test_assert_marker_fails_on_wrong_severity():
    with pytest.raises(AssertionError):
        assert_marker(DUP_WARNING, severity="error")


def test_assert_marker_requires_a_criterion():
    """An unconstrained assertion is always vacuous -- reject it."""
    with pytest.raises(AssertionError, match="at least one of"):
        assert_marker(UNKNOWN_TYPE_ERROR)


def test_assert_marker_count_match():
    assert_marker(DUP_WARNING, severity="warning", count=1)


def test_assert_marker_count_mismatch_fails():
    with pytest.raises(AssertionError, match="Expected 2 markers"):
        assert_marker(DUP_WARNING, severity="warning", count=2)


# =============================================================================
# assert_no_marker
# =============================================================================

def test_assert_no_marker_on_clean_source():
    assert_no_marker(CLEAN, severity="error")
    assert_no_marker(CLEAN, severity="warning")


def test_assert_no_marker_ignores_non_matching_markers():
    """A warning present must not defeat an assertion about errors."""
    assert_no_marker(DUP_WARNING, severity="error")


def test_assert_no_marker_fails_when_present():
    with pytest.raises(AssertionError, match="Expected no matching marker"):
        assert_no_marker(UNKNOWN_TYPE_ERROR, severity="error")


def test_assert_no_marker_by_id():
    assert_no_marker(DUP_WARNING, marker_id="PSS002")
    with pytest.raises(AssertionError):
        assert_no_marker(DUP_WARNING, marker_id="PSS003")


def test_assert_no_marker_requires_a_criterion():
    with pytest.raises(AssertionError, match="at least one of"):
        assert_no_marker(CLEAN)


# =============================================================================
# assert_parse_ok_with_warning
# =============================================================================

def test_assert_parse_ok_with_warning_happy_path():
    root = assert_parse_ok_with_warning(DUP_WARNING, marker_id="PSS003")
    assert root is not None


def test_assert_parse_ok_with_warning_matches_by_text():
    assert_parse_ok_with_warning(DUP_WARNING, text="duplicate declaration")


def test_assert_parse_ok_with_warning_fails_without_warning():
    """Half the assertion: the parse succeeded but nothing warned."""
    with pytest.raises(AssertionError, match="expected warning was not emitted"):
        assert_parse_ok_with_warning(CLEAN, marker_id="PSS003")


def test_assert_parse_ok_with_warning_fails_on_error():
    """The other half: something warned, but the parse did not survive."""
    with pytest.raises(AssertionError, match="Expected a successful parse"):
        assert_parse_ok_with_warning(UNKNOWN_TYPE_ERROR, marker_id="PSS002")


# =============================================================================
# assert_no_errors
# =============================================================================

def test_assert_no_errors_passes_on_clean_parse():
    parser = Parser()
    parser.parses([("test.pss", CLEAN)])
    parser.link()
    assert_no_errors(parser)


def test_assert_no_errors_ignores_warnings():
    parser = Parser()
    parser.parses([("test.pss", DUP_WARNING)])
    parser.link()
    assert_no_errors(parser)


def test_assert_no_errors_fails_when_errors_present():
    """Guards the regression this replaced: the stub passed unconditionally."""
    parser = Parser()
    with pytest.raises(Exception) as exc_info:
        parser.parses([("test.pss", UNKNOWN_TYPE_ERROR)])
        parser.link()
    assert getattr(exc_info.value, "markers", None)

    with pytest.raises(AssertionError, match="Expected no errors"):
        assert_no_errors(parser)


# =============================================================================
# Regression guard: linker warnings survive a successful link
# =============================================================================

def test_link_phase_warnings_are_collected_on_success():
    """
    Parser.link() previously merged its markers only on the error path, so a
    link-phase warning accompanying a successful link was discarded. Every
    warning-only PSS 3.1 check depends on this not regressing.
    """
    parser = Parser()
    parser.parses([("test.pss", DUP_WARNING)])
    root = parser.link()

    assert root is not None
    assert any(m["severity"] == "warning" for m in parser.markers), \
        "link-phase warning was dropped on the success path"
