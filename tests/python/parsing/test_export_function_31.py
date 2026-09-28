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


# -- An instance function is an extension (PSS120) ---------------------------

def _markers(code):
    from test_helpers import parse_collect
    _, markers = parse_collect(code)
    return [(m["line"], m.get("code"), m["severity"]) for m in markers]


def test_exporting_an_instance_function_is_an_extension():
    """20.4.2 exports static functions only. A component's instance function
    is accepted with a warning at the export, and still bound."""
    assert _markers("""
component pss_top {
    int n;
    target function void bump(int k) { n += k; }
    export target function bump;
}
""") == [(5, "PSS120", "warning")]


def test_exporting_a_static_component_function_is_clean():
    assert _markers("""
component pss_top {
    static function int twice(int k) { return 2*k; }
    export target function twice;
}
""") == []


def test_exporting_a_package_function_is_clean():
    assert _markers("""
function int sq(int x) { return x*x; }
export target function sq;
component pss_top { }
""") == []


def test_an_inherited_instance_function_is_an_extension_too():
    """The export names what the component's scope finds: a base's
    instance function is still an instance function."""
    assert _markers("""
component base_c {
    target function void go() { }
}
component pss_top : base_c {
    export target function go;
}
""") == [(6, "PSS120", "warning")]


def test_an_extension_contributes_an_instance_function_export():
    assert _markers("""
component pss_top { }
extend component pss_top {
    target function void go() { }
    export target function go;
}
""") == [(5, "PSS120", "warning")]
