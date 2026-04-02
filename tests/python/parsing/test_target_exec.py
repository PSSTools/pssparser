"""
Tests for PSS target-template exec blocks (LRM §22.5).

Covers: exec body/header/init with language identifiers, exec file
directive, multiple language targets, linkage, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_exec_body_c(parser):
    """exec body with C language target"""
    code = """
component pss_top {
    action WriteReg {
        rand bit[32] addr;
        exec body C = "write_reg(0, 0);";
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "WriteReg")
    assert action is not None
    assert has_symbol(action, "addr")
    loc = get_location(action.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_exec_body_sv(parser):
    """exec body with SystemVerilog language target"""
    code = """
component pss_top {
    action UvmAction {
        exec body SV = "uvm_do_on(seq, sqr);";
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "UvmAction")


def test_exec_header_c(parser):
    """exec header with C language target"""
    code = """
component pss_top {
    action A {
        exec header C = "#include <stdint.h>";
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "A")


def test_exec_init_c(parser):
    """exec init with C language target"""
    code = """
component pss_top {
    action A {
        exec init C = "hw_init();";
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "A")


def test_exec_file(parser):
    """exec file directive"""
    code = """
component pss_top {
    action A {
        exec file "output.c" = "// auto-generated";
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "A")


def test_exec_multiple_targets(parser):
    """Action with exec blocks for multiple languages"""
    code = """
component pss_top {
    action MultiTarget {
        rand int val;
        exec body C = "process_c(0);";
        exec body SV = "process_sv();";
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "MultiTarget")
    assert action is not None
    assert has_symbol(action, "val")
