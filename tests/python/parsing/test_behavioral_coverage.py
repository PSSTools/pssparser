"""
Tests for PSS behavioral coverage and monitor features (LRM §19).

Covers: cover statements (reference and block), monitor declarations,
abstract monitors, monitor inheritance, monitor activities (sequence,
concat, schedule), monitor constraints, linkage, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_cover_statement_ref(parser):
    """Cover statement referencing an action type"""
    code = """
component pss_top {
    action A { rand int x; }
    cover A;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "A")
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_cover_statement_block(parser):
    """Cover statement with inline monitor body"""
    code = """
component pss_top {
    action A { rand int x; }
    cover {
        A a;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "A")


def test_labeled_cover_statement(parser):
    """Labeled cover statement"""
    code = """
component pss_top {
    action A { rand int x; }
    my_cover: cover A;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None


def test_abstract_monitor(parser):
    """Abstract monitor declaration"""
    code = """
component pss_top {
    action A { }
    abstract monitor AbsMon {
        A a;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "AbsMon")


def test_monitor_inheritance(parser):
    """Monitor extending another monitor"""
    code = """
component pss_top {
    action A { }
    monitor BaseMon {
        A a;
    }
    monitor DerivedMon : BaseMon {
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "BaseMon")
    assert has_symbol(comp, "DerivedMon")


def test_monitor_activity_sequence(parser):
    """Monitor with sequence activity"""
    code = """
component pss_top {
    action A { }
    action B { }
    monitor SeqMon {
        A a;
        B b;
        activity {
            sequence {
                do a;
                do b;
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "SeqMon")


def test_monitor_activity_concat(parser):
    """Monitor with concat activity"""
    code = """
component pss_top {
    action A { }
    monitor ConcatMon {
        A a;
        activity {
            concat {
                do a;
                do a;
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "ConcatMon")


def test_monitor_activity_schedule(parser):
    """Monitor with schedule activity"""
    code = """
component pss_top {
    action A { }
    action B { }
    monitor SchedMon {
        A a;
        B b;
        activity {
            schedule {
                do a;
                do b;
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "SchedMon")


def test_monitor_with_constraint(parser):
    """Monitor with constraint on action handle fields"""
    code = """
component pss_top {
    action A { rand int x; }
    monitor ConMon {
        A a;
        constraint a.x > 0;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "ConMon")


def test_monitor_with_covergroup(parser):
    """Monitor with inline covergroup declaration"""
    code = """
component pss_top {
    action A { rand int x; }
    monitor CovMon {
        A a;
        covergroup {
            coverpoint a.x;
        } cg_inst;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "CovMon")
