"""Lookup diagnostics that start as warnings (symbol-resolution plan 6.5).

- **Declaration-site import rules (18.1.3).** An explicit import shall not
  name something the importing namespace declares (CH17-30, PSS052), nor
  take a name another explicit import in the same scope takes from another
  package (CH17-31, PSS052); imports come first in their scope (CH17-34,
  PSS053).
- **Extension-member visibility (17.2.3, L-05).** A member an extension in
  package p adds to a type is visible in p, and elsewhere only where p is
  wildcard-imported (PSS051); where two packages each add one of a name, a
  reference binds to its own package's, else to the imported one, and two
  imported ones are ambiguous (PSS017).

Every new diagnostic is a warning for now (plan §8), except the ambiguity,
which 17.2.3 makes an error to reference and which used to bind silently to
whichever extension was merged first.
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"]) for m in ms]


def messages(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"], m["message"]) for m in ms]


def bindings(code, *names):
    """(name, line of use, line its declaration's name is on) per use."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.text, o.line, o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text in names and not o.is_declaration]


# -- CH17-30 / CH17-31: explicit-import conflicts (PSS052) ----------------------

def test_an_explicit_import_of_a_name_the_package_declares():
    code = """\
package lib { struct s { } }
package p {
  import lib::s;
  struct s { }
}
"""
    assert messages(code) == [(
        "PSS052", 3,
        "'import lib::s;' names 's', which package 'p' already declares; an "
        "explicit import shall not name a declaration of the importing "
        "namespace (18.1.3)")]


def test_the_importing_namespace_is_every_statement_of_the_package():
    code = """\
package lib { struct s { } }
package p { struct s { } }
package p { import lib::s; }
"""
    assert markers(code) == [("PSS052", 3)]


def test_a_component_import_against_the_component_s_members():
    code = """\
package lib { struct s { } }
component c { import lib::s; struct s { } }
"""
    assert markers(code) == [("PSS052", 2)]


def test_two_explicit_imports_of_one_name_unused():
    code = """\
package lib1 { struct s { } }
package lib2 { struct s { } }
package p {
  import lib1::s;
  import lib2::s;
}
"""
    assert messages(code) == [(
        "PSS052", 5,
        "'s' is already imported explicitly in this scope, by 'import "
        "lib1::s;'; the same name shall not be imported explicitly from two "
        "packages (18.1.3)")]


def test_two_explicit_imports_of_one_name_used():
    """The use is still the error it was; the import pair is a warning."""
    code = """\
package lib1 { struct s { } }
package lib2 { struct s { } }
package p {
  import lib1::s;
  import lib2::s;
  struct t { s f; }
}
"""
    assert markers(code) == [("PSS052", 5), ("PSS017", 6)]


def test_explicit_imports_that_do_not_conflict():
    code = """\
package lib1 { struct s { } }
package lib2 { struct s { } }
package p { import lib1::s; import lib1::s; }
package p { import lib2::s; }
package q { import lib1::*; struct s { } }
"""
    # The same declaration twice; another statement of the package (each
    # import applies only in its own); a wildcard import and a local.
    assert markers(code) == []


# -- CH17-34: imports come first (PSS053) ---------------------------------------

def test_an_import_after_a_declaration_in_a_package_and_a_component():
    code = """\
package lib { struct s { } }
package p {
  struct t { }
  import lib::*;
}
component pss_top {
  int x;
  import lib::*;
}
"""
    assert messages(code) == [
        ("PSS053", 4,
         "'import lib::*;' follows a declaration; imports shall come first in "
         "a package, a component, an extension or a file (18.1.3)"),
        ("PSS053", 8,
         "'import lib::*;' follows a declaration; imports shall come first in "
         "a package, a component, an extension or a file (18.1.3)")]


def test_an_import_after_a_declaration_in_the_global_scope():
    code = """\
package lib { struct s { } }
struct t { }
import lib::*;
component pss_top { s f; }
"""
    assert markers(code) == [("PSS053", 3)]


def test_an_import_after_a_declaration_in_a_component_extension():
    code = """\
package lib { struct s { } }
component c { }
extend component c {
  int x;
  import lib::*;
}
"""
    assert markers(code) == [("PSS053", 5)]


def test_imports_first_is_legal():
    code = """\
import lib::*;
package lib { struct s { } }
package p {
  import lib::*;
  import lib::s;
  struct t { s f; }
}
component pss_top { import lib::*; s f; }
"""
    assert markers(code) == []


def test_a_scope_with_a_compile_if_is_not_checked():
    """A `compile if` may precede an import, and its taken branch is spliced
    into the scope with no position left to tell it apart."""
    code = """\
package lib { struct s { } }
package p {
  compile if (1) { struct t { } }
  import lib::*;
}
"""
    assert markers(code) == []


# -- 17.2.3: extension-member visibility (PSS051) -------------------------------

def test_an_extension_member_used_without_its_package():
    code = """\
struct S { rand int a; }
package p { extend struct S { rand int b; } }
component pss_top {
  action A { rand S v; constraint v.b == 1; }
}
"""
    assert messages(code) == [(
        "PSS051", 4,
        "'b' is declared by an extension of 'S' in package 'p', which is not "
        "visible here (17.2.3); add 'import p::*;'")]
    # It still binds, as it always has.
    assert bindings(code, "b") == [("b", 4, 2)]


def test_an_extension_member_used_from_another_package():
    code = """\
struct S { rand int a; }
package p { extend struct S { rand int b; } }
package q {
  struct T { rand S s; constraint s.b == 1; }
}
"""
    assert markers(code) == [("PSS051", 4)]


def test_an_extension_member_visible_through_a_wildcard_import():
    code = """\
struct S { rand int a; }
package p { extend struct S { rand int b; } }
component pss_top {
  import p::*;
  action A { rand S v; constraint v.b == 1; }
}
"""
    assert markers(code) == []


def test_an_extension_member_is_visible_in_its_own_package():
    code = """\
struct S { rand int a; }
package p {
  extend struct S { rand int b; }
  struct T { rand S s; constraint s.b == 1; }
}
package p { struct U { rand S s; constraint s.b == 1; } }
package p::inner { struct V { rand S s; constraint s.b == 1; } }
"""
    # Every statement of p, and a package inside it.
    assert markers(code) == []


def test_global_and_same_package_extensions_are_visible_everywhere():
    code = """\
struct S { rand int a; }
extend struct S { rand int g; }
package p {
  struct P { rand int a; }
  extend struct P { rand int b; }
}
package q {
  struct T { rand S s; rand p::P t; constraint s.g == 1; constraint t.b == 1; }
}
"""
    assert markers(code) == []


def test_an_enum_item_an_extension_adds():
    code = """\
enum E { A }
package p { extend enum E { B } }
component pss_top {
  action T { rand E e; constraint e == B; }
}
component c2 {
  import p::*;
  action T { rand E e; constraint e == B; }
}
"""
    assert messages(code) == [(
        "PSS051", 4,
        "'B' is an item an extension of 'E' in package 'p' adds, which is not "
        "visible here (17.2.3); add 'import p::*;'")]


def test_an_import_in_another_file_does_not_make_it_visible():
    p = pssparser.Parser()
    p.parses([
        ("a.pss", "import p::*;\n"
                  "struct S { rand int a; }\n"
                  "package p { extend struct S { rand int b; } }\n"),
        ("b.pss", "component pss_top {\n"
                  "  action A { rand S v; constraint v.b == 1; }\n"
                  "}\n"),
    ])
    p.link()
    assert [(m["file"], m["line"], m["message"].split(" (")[0])
            for m in p.markers] == [
        ("b.pss", 2, "'b' is declared by an extension of 'S' in package "
                     "'p', which is not visible here")]


# -- 17.2.3: a name two packages' extensions share ------------------------------

SHARED = """\
struct S { rand int a; }
package p { extend struct S { rand int b; } }
package q { extend struct S { rand int b; constraint b == 2; } }
package r { import p::*; struct T { rand S s; constraint s.b == 1; } }
package q { struct U { rand S s; constraint s.b == 1; } }
package r { import q::*; struct V { rand S s; constraint s.b == 1; } }
"""


def test_a_shared_name_binds_by_package():
    assert markers(SHARED) == []
    assert bindings(SHARED, "b") == [
        ("b", 3, 3),        # inside q's extension: q's own
        ("b", 4, 2),        # r imports p
        ("b", 5, 3),        # q's own, in another statement of q
        ("b", 6, 3),        # r imports q
    ]


def test_the_own_package_shadows_an_imported_one():
    code = SHARED + """\
package q { import p::*; struct W { rand S s; constraint s.b == 1; } }
"""
    assert markers(code) == []
    assert bindings(code, "b")[-1] == ("b", 7, 3)


def test_a_shared_name_two_imports_provide_is_ambiguous():
    code = SHARED + """\
package w { import p::*; import q::*; struct X { rand S s; constraint s.b == 1; } }
"""
    assert messages(code) == [(
        "PSS017", 7,
        "ambiguous reference to 'b': extensions of 'S' in package 'p' and "
        "package 'q' each declare it, and each package is imported here "
        "(17.2.3); import only one")]


def test_a_shared_name_neither_package_makes_visible():
    code = SHARED + """\
package w { struct X { rand S s; constraint s.b == 1; } }
"""
    assert messages(code) == [(
        "PSS051", 7,
        "'b' is declared by an extension of 'S' in package 'p' and package "
        "'q', none of which is visible here (17.2.3); add 'import p::*;'")]
