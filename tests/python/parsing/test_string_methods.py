"""
Tests for PSS string methods and sub-string operations (LRM §7.6).

Covers: len, size, find, rfind, substr, to_upper, to_lower,
starts_with, ends_with, trim, string domain declarations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_string_len(parser):
    """String .len() method"""
    code = """
component pss_top {
    action A {
        string s;
        int n;
        exec post_solve { n = s.len(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert has_symbol(action, "s")
    assert has_symbol(action, "n")


def test_string_size(parser):
    """String .size() method"""
    code = """
component pss_top {
    action A {
        string s;
        int n;
        exec post_solve { n = s.size(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_find(parser):
    """String .find() method"""
    code = """
component pss_top {
    action A {
        string s;
        int pos;
        exec post_solve { pos = s.find("needle"); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_rfind(parser):
    """String .rfind() method"""
    code = """
component pss_top {
    action A {
        string s;
        int pos;
        exec post_solve { pos = s.rfind("x"); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_substr(parser):
    """String .substr() method"""
    code = """
component pss_top {
    action A {
        string s;
        string r;
        exec post_solve { r = s.substr(0, 3); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_to_upper(parser):
    """String .to_upper() method"""
    code = """
component pss_top {
    action A {
        string s;
        string r;
        exec post_solve { r = s.to_upper(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_to_lower(parser):
    """String .to_lower() method"""
    code = """
component pss_top {
    action A {
        string s;
        string r;
        exec post_solve { r = s.to_lower(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_starts_with(parser):
    """String .starts_with() method"""
    code = """
component pss_top {
    action A {
        string s;
        bool r;
        exec post_solve { r = s.starts_with("prefix"); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_ends_with(parser):
    """String .ends_with() method"""
    code = """
component pss_top {
    action A {
        string s;
        bool r;
        exec post_solve { r = s.ends_with("suffix"); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_trim(parser):
    """String .trim() method"""
    code = """
component pss_top {
    action A {
        string s;
        string r;
        exec post_solve { r = s.trim(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_string_domain(parser):
    """String with domain constraint"""
    code = """
struct config_s {
    string in ["fast", "slow", "auto"] mode;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "config_s")
    assert sym is not None
    assert has_symbol(sym, "mode")
    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2
