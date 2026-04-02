"""
Tests for PSS pool declarations and bind directives (LRM §15).

Covers: pool declarations (sized and unsized), bind statements
(wildcard and specific), pool in component context, linkage, locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_pool_unsized(parser):
    """Unsized pool declaration in component"""
    code = """
resource CPU { };
component pss_top {
    pool CPU cpus;
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "CPU") is not None
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_pool_sized(parser):
    """Sized pool declaration"""
    code = """
resource CPU { };
component pss_top {
    pool [4] CPU cpus;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None


def test_bind_wildcard(parser):
    """Bind pool with wildcard"""
    code = """
resource CPU { };
component pss_top {
    pool CPU cpus;
    action Work { lock CPU cpu; }
    bind cpus *;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "Work")


def test_bind_specific(parser):
    """Bind pool to specific action field"""
    code = """
resource CPU { };
component pss_top {
    pool CPU cpus;
    action Work { lock CPU cpu; }
    bind cpus {Work.cpu};
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "Work")
