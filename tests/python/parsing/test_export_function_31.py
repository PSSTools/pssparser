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
        function void do_work() { }
        export target function do_work;
    }
    """
    root = assert_parse_ok(pss)
    pkg = get_symbol(root, "p")
    assert pkg is not None


def test_export_function_in_component():
    pss = """
    component C {
        static function void do_work() { }
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


def test_export_function_names_a_declared_function():
    """20.4.2: the exported name is a function declared elsewhere (F-N12)."""
    assert_parse_error("""
    component C {
        export target function no_such_fn;
    }
    """, "unknown function 'no_such_fn'")


def test_export_function_names_a_function_not_a_field():
    assert_parse_error("""
    component C {
        int do_work;
        export target function do_work;
    }
    """, "'do_work' is not a function")
