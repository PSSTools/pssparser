"""Imports apply only where they are written (symbol-resolution plan 6.3a).

LRM 18.1.3, decision Q5: an import applies inside the `package` statement,
component declaration or `extend` statement that contains it, or -- in the
global scope -- to the rest of its file. It is not re-exported to another
statement that opens the same namespace, nor to another file. A name that only
such an import provides is an error, and the error names the import.
"""
import pssparser

from ..test_helpers import parse_collect
from .test_activity_scopes import assert_links_and_binds


def errors(code):
    _, markers = parse_collect(code)
    return [m["message"] for m in markers if m["severity"] == "error"]


def markers_of(files):
    """(file, line, message, related) of every error, linking `files` in order."""
    p = pssparser.Parser()
    try:
        p.parses(files)
        p.link()
        markers = p.markers
    except Exception as e:
        markers = getattr(e, "markers", None)
        if markers is None:
            raise
    return [(m.get("file", ""), m["line"], m["message"],
             [(r.get("file", ""), r["line"], r["label"]) for r in m.get("related", [])])
            for m in markers if m["severity"] == "error"]


def leak(kind, name, imp):
    return (f"unknown {kind} '{name}'; 'import {imp};' provides it, but an "
            "import applies only inside the statement it is written in, or to "
            f"its own file (18.1.3) -- add 'import {imp};' here")


LIB = ("lib.pss", """
package lib {
  struct s { rand int a; }
  const int K = 4;
}
""")


# ---------------------------------------------------------------------------
# What an import reaches
# ---------------------------------------------------------------------------

def test_an_import_in_an_extension_reaches_the_extensions_members(tmp_path):
    """ND-3 (b1): the extension's own fields and nested types see it."""
    assert_links_and_binds(tmp_path, """
package lib { struct s { rand int a; } }
component pss_top { }
extend component pss_top {
  import lib::*;
  s f;
  action A { s g; constraint g.a == 1; }
}
""")


def test_a_global_import_reaches_the_rest_of_its_file():
    assert markers_of([LIB, ("a.pss", """
import lib::*;
component pss_top { s f; }
""")]) == []


def test_the_same_import_in_two_files_applies_in_each():
    """Each file's import is its own: the second is not dropped as a
    duplicate of the first."""
    assert markers_of([LIB,
        ("a.pss", "import lib::*;\nstruct a_s { rand s f; }\n"),
        ("b.pss", "import lib::*;\ncomponent pss_top { s f; }\n")]) == []


def test_an_extend_enum_item_is_found_through_its_package():
    """Ex. 248: importing the package that extends an enum makes the items it
    adds visible, though they live in the extended enum."""
    assert errors("""
package defs { enum tag_e { A }; }
package more { import defs::*; extend enum tag_e { B }; }
component pss_top {
  import defs::*;
  action act { rand tag_e t; }
}
extend component pss_top {
  import more::*;
  action use { act a; constraint a.t == B; }
}
""") == []


def test_an_import_in_a_generic_components_extension_reaches_its_specializations():
    assert errors("""
package lib { struct s { rand int a; } }
component c<int N = 1> { }
extend component c {
  import lib::*;
  struct w { rand s f; constraint f.a == N; }
}
component pss_top { c<2> i; c<3> j; }
""") == []


# ---------------------------------------------------------------------------
# What it does not reach: each is an error that names the import
# ---------------------------------------------------------------------------

def test_a_global_import_does_not_reach_another_file():
    assert markers_of([LIB,
        ("a.pss", "import lib::*;\nstruct a_s { }\n"),
        ("b.pss", "component pss_top { s f; }\n")]) == [
        ("b.pss", 1, leak("type", "s", "lib::*"), [("a.pss", 1, "imported here")])]


def test_an_import_does_not_reach_another_statement_of_the_same_package():
    assert errors("""
package lib { struct s { rand int a; } }
package p { import lib::*; }
package p { struct t { rand s f; } }
component pss_top { }
""") == [leak("type", "s", "lib::*")]


def test_a_component_import_does_not_reach_an_extension():
    assert errors("""
package lib { struct s { rand int a; } }
component pss_top { import lib::*; }
extend component pss_top { s f; }
""") == [leak("type", "s", "lib::*")]


def test_an_extension_import_does_not_reach_the_component_declaration():
    assert errors("""
package lib { const int K = 4; }
component pss_top {
  action a { rand int x; constraint x == K; }
}
extend component pss_top { import lib::*; }
""") == [leak("identifier", "K", "lib::*")]


def test_a_named_import_is_named_in_the_error():
    assert errors("""
package lib { struct s { rand int a; } }
package p { import lib::s; }
package p { struct t { rand s f; } }
component pss_top { }
""") == [leak("type", "s", "lib::s")]
