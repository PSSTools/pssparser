"""
Tests for PSS 3.1 export target function declarations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error, get_symbol


def test_export_function_in_package():
    pss = """
    package p {
        export target function do_work;
    }
    """
    root = assert_parse_ok(pss)
    pkg = get_symbol(root, "p")
    assert pkg is not None


def test_export_function_in_component():
    pss = """
    component C {
        export target function do_work;
    }
    """
    root = assert_parse_ok(pss)
    comp = get_symbol(root, "C")
    assert comp is not None


def test_export_function_requires_target_keyword():
    pss = """
    component C {
        export function do_work;
    }
    """
    assert_parse_error(pss)
