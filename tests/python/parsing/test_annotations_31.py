"""
Tests for PSS 3.1 annotation declarations and extensions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error, get_symbol


def test_annotation_declaration_basic():
    pss = """
    annotation desc_s {
        string desc;
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "desc_s") is not None


def test_annotation_declaration_with_super_and_params():
    pss = """
    annotation base_s {
        string desc;
    }

    annotation rich_s<int W=1> : base_s {
        static const int width = W;
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "base_s") is not None
    assert get_symbol(root, "rich_s") is not None


def test_extend_annotation_basic():
    pss = """
    annotation desc_s {
        string desc;
    }

    extend annotation desc_s {
        static const int version = 1;
    }
    """
    root = assert_parse_ok(pss)
    assert root is not None


def test_annotation_application_positional_and_named():
    pss = """
    annotation desc_s {
        string desc;
        string owner;
    }

    @desc_s("block", owner="dv")
    component C {
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "desc_s") is not None
    assert get_symbol(root, "C") is not None


def test_annotation_compile_if_in_body():
    pss = """
    annotation cfg_s {
        compile if (true) {
            string name;
        }
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "cfg_s") is not None


def test_extend_annotation_requires_target():
    pss = """
    extend annotation {
        static const int version = 1;
    }
    """
    assert_parse_error(pss)
