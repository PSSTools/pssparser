"""
Tests for PSS 3.1 component `instance` qualifier support.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error, get_symbol
from pssparser import ast as pss_ast


def test_component_instance_scalar_field():
    pss = """
    component sub_c { }
    component C {
        // 9.1.5.3 a: `instance` only on a component reference (PSS149).
        instance ref sub_c value;
    }
    """
    root = assert_parse_ok(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    field = get_symbol(comp, "value")
    assert field is not None
    assert field.getAttr() & pss_ast.FieldAttr.Instance


def test_component_instance_user_defined_field():
    pss = """
    component S {
        int x;
    }

    component C {
        protected instance ref S cfg;
    }
    """
    root = assert_parse_ok(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    field = get_symbol(comp, "cfg")
    assert field is not None
    assert field.getAttr() & pss_ast.FieldAttr.Instance
    assert field.getAttr() & pss_ast.FieldAttr.Protected


def test_component_instance_cannot_combine_with_static_const():
    pss = """
    component C {
        instance static const int value = 1;
    }
    """
    assert_parse_error(pss)
