"""
Semantic tests for compile-time elaboration features.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from test_helpers import parse_pss, get_symbol, assert_parse_error


def test_compile_if_true_selects_true_branch():
    pss = """
    component C {
        compile if (true) {
            action A { }
        } else {
            action B { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None
    assert get_symbol(comp, "B") is None


def test_compile_if_false_selects_false_branch():
    pss = """
    component C {
        compile if (false) {
            action A { }
        } else {
            action B { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is None
    assert get_symbol(comp, "B") is not None


def test_compile_if_compile_has_type():
    pss = """
    component C {
        action A { }
        compile if (compile has (A)) {
            action B { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "B") is not None


def test_compile_if_compile_has_field():
    pss = """
    component C {
        struct S {
            bit[8] field1;
        }
        action A {
            S s;
            compile if (compile has (s.field1)) {
                rand bit[8] value;
            }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    action = get_symbol(comp, "A")
    assert action is not None
    assert get_symbol(action, "value") is not None


def test_compile_assert_failure_reports_error():
    pss = """
    component C {
        compile assert(false, "expected failure");
    }
    """
    assert_parse_error(pss, "compile assert failed")


def test_compile_assert_with_expression():
    pss = """
    component C {
        compile assert(1 + 1 == 2, "math");
        action A { }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_struct_body_compile_if_selects_branch():
    pss = """
    struct S {
        compile if (true) {
            int a;
        } else {
            int b;
        }
    }
    """
    root = parse_pss(pss)
    struct = get_symbol(root, "S")
    assert struct is not None
    assert get_symbol(struct, "a") is not None
    assert get_symbol(struct, "b") is None


def test_component_body_compile_if_selects_branch():
    pss = """
    component C {
        compile if (false) {
            action A { }
        } else {
            action B { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is None
    assert get_symbol(comp, "B") is not None


def test_annotation_body_compile_if_selects_branch():
    pss = """
    annotation ann_s {
        compile if (true) {
            int a;
        } else {
            int b;
        }
    }
    """
    root = parse_pss(pss)
    ann = get_symbol(root, "ann_s")
    assert ann is not None
    assert get_symbol(ann, "a") is not None
    assert get_symbol(ann, "b") is None


def test_compile_if_package_static_const():
    pss = """
    package config_pkg {
        static const int PROTOCOL_VER_1_2 = 1;
    }

    component C {
        import config_pkg::*;
        compile if (config_pkg::PROTOCOL_VER_1_2) {
            action A { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_if_wildcard_imported_static_const():
    pss = """
    package config_pkg {
        static const int FEATURE_ENABLED = 1;
    }

    component C {
        import config_pkg::*;
        compile if (FEATURE_ENABLED) {
            action A { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_assert_wildcard_imported_nested_package_static_const():
    pss = """
    package outer::inner {
        static const int FIELD1 = 1;
        static const int FIELD2 = FIELD1 + 1;
    }

    component C {
        import outer::inner::*;
        compile assert(FIELD2 == 2, "imported nested package const");
        action A { }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_if_alias_imported_static_const():
    pss = """
    package outer::inner {
        static const int FIELD1 = 1;
        static const int FIELD2 = FIELD1 + 1;
    }

    component C {
        import outer::inner as cfg;
        compile if (cfg::FIELD2 == 2) {
            action A { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_assert_static_const_identifier():
    pss = """
    component C {
        static const int FIELD1 = 1;
        compile assert(FIELD1, "FIELD1 must be set");
        action A { }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_if_static_const_expression_identifier():
    pss = """
    component C {
        static const int FIELD1 = 1;
        static const int FIELD2 = FIELD1 + 1;
        compile if (FIELD2 == 2) {
            action A { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_assert_nested_package_static_const_expression():
    pss = """
    package outer::inner {
        static const int FIELD1 = 1;
        static const int FIELD2 = FIELD1 + 1;
    }

    component C {
        compile assert(outer::inner::FIELD2 == 2, "nested package const");
        action A { }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "A") is not None


def test_compile_if_enum_item_expression():
    pss = """
    component C {
        enum E {
            A = 1,
            B = A + 1
        }
        compile if (E::B == 2) {
            action Enabled { }
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "C")
    assert comp is not None
    assert get_symbol(comp, "Enabled") is not None


# -- literal forms in a compile-time condition (P1-G1c) -----------------------
#
# Compile-time evaluation used to have a literal reader of its own, and it
# disagreed with the one the AST is built from: it read `8'hFF` as 8 (strtoll
# stops at the quote) and `0b1010` as 0 (the leading `0` routed it to the octal
# branch). Nothing reported it -- the condition just evaluated false and the
# wrong branch was elaborated.
#
# Both now go through `parseIntegerLiteral`. Every form B.19 spells is listed
# here, because the failure mode of having two readers is precisely that one of
# them is missing a form nobody thought to check.

@pytest.mark.parametrize("cond", [
    "255 == 255",
    "1_000 == 1000",
    "0xFF == 255",
    "0XFF == 255",
    "0777 == 511",
    "0b1010 == 10",
    "0B1010 == 10",
    "8'hFF == 255",
    "8'd99 == 99",
    "4'b1010 == 10",
    "8'o777 == 511",
    "'hFF == 255",
    "8'hF_F == 255",
    "1_6'hFF == 255",
])
def test_compile_if_reads_a_literal_condition(cond):
    pss = """
    component C {
        compile if (%s) {
            action Yes { }
        } else {
            action No { }
        }
    }
    """ % cond
    comp = get_symbol(parse_pss(pss), "C")
    assert get_symbol(comp, "Yes") is not None, "%r took the else branch" % cond
