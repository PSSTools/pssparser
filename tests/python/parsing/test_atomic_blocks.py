"""
Tests for PSS activity atomic blocks (LRM §12.3.8).

Covers: atomic block syntax, nesting in parallel/sequence,
linkage of traversal targets inside atomic, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_atomic_basic(parser):
    """Basic atomic block in activity"""
    code = """
component pss_top {
    action Step { rand int x; }
    action Main {
        Step s;
        activity {
            atomic {
                do s;
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "Main")
    assert has_symbol(comp, "Step")

    main = get_symbol(comp, "Main")
    loc = get_location(main.getTarget())
    assert loc is not None
    assert loc[0] == 4


def test_atomic_in_parallel(parser):
    """Atomic block inside parallel — classic critical-section pattern"""
    code = """
component pss_top {
    action Read { rand int addr; }
    action Write { rand int addr; }
    action Main {
        Read r;
        Write w;
        activity {
            parallel {
                atomic {
                    do r;
                    do w;
                }
                atomic {
                    do r;
                }
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    main = get_symbol(comp, "Main")
    assert main is not None
    assert has_symbol(main, "r")
    assert has_symbol(main, "w")


def test_atomic_with_multiple_traversals(parser):
    """Atomic block with several action traversals"""
    code = """
component pss_top {
    action A { rand int x; }
    action B { rand int y; }
    action C { rand int z; }
    action Main {
        A a;
        B b;
        C c;
        activity {
            atomic {
                do a;
                do b;
                do c;
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    main = get_symbol(comp, "Main")
    assert main is not None
    for name in ("a", "b", "c"):
        assert has_symbol(main, name), f"handle {name} not found"
