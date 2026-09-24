"""Package aliases, `import p::q as a;` (symbol-resolution plan 6.4, F19).

LRM 18.1.4: an alias is a name-resolution shortcut for a package, visible only
in the lexical scope it is declared in. It introduces no entity: it cannot be
reached as `consumer_pkg::a`, a wildcard import of its package does not carry
it, and it does not make the target's own name visible. 18.3 c.2.i searches
aliases before explicit and wildcard imports; Ex. 273 needs the same in a
component (decision Q3).

Declaration errors (18.1.4, PSS043): two aliases of one name in one scope, and
an alias named like a package already declared in its namespace -- in this
source unit or an earlier one. A later unit may add such a package.
"""
from ..test_helpers import parse_collect
from .test_import_scope import markers_of


def errors(code):
    _, markers = parse_collect(code)
    return [m["message"] for m in markers if m["severity"] == "error"]


PKGS = """
package pkg1::a::b::c { struct my_s { rand int v1; } }
package pkg2::d::e::f { struct my_s { rand int v2; } }
"""


def test_ex259_aliases_name_their_packages():
    assert errors(PKGS + """
package consumer_pkg {
  import pkg1::a::b::c as p1;
  import pkg2::d::e::f as p2;
  struct s {
    rand p1::my_s               v1_1;
    rand pkg1::a::b::c::my_s    v1_2;
    rand p2::my_s               v2;
    constraint v1_1.v1 == v1_2.v1;
    constraint v2.v2 == 1;
  }
}
component pss_top { }
""") == []


def test_an_alias_of_a_nested_package_declared_alongside_it():
    """Repro a3: the alias target resolves from where the import is written."""
    assert errors("""
package P {
  package bar { struct b { rand int x; } }
  import bar as foo;
  struct t { rand foo::b f; constraint f.x == 1; }
}
component pss_top { }
""") == []


def test_ex273_an_alias_takes_precedence_over_a_wildcard_import():
    """P2 is the alias of P3::P4, not P1's P2 (field p3, not p1)."""
    assert errors("""
package P1 { package P2 { struct s { rand int p1; } } }
package P3 { package P4 { struct s { rand int p3; } } }
component pss_top {
  import P1::*;
  import P3::P4 as P2;
  action test { rand P2::s f; constraint f.p3 == 1; }
}
""") == []


def test_an_alias_does_not_make_the_targets_own_name_visible():
    """Repro d4."""
    errs = errors("""
package P3 { package P4 { struct s {} } }
component pss_top {
  import P3::P4 as P2;
  struct w { P4::s f; }
}
""")
    assert len(errs) == 1 and errs[0].startswith("unknown type 'P4'")


def test_an_alias_is_not_visible_in_another_package_statement():
    errs = errors(PKGS + """
package consumer_pkg {
  import pkg1::a::b::c as p1;
}
package consumer_pkg {
  struct s { p1::my_s v; }
}
component pss_top { }
""")
    assert len(errs) == 1 and "'p1'" in errs[0]


def test_an_alias_is_not_a_member_of_its_package():
    errs = errors(PKGS + """
package consumer_pkg {
  import pkg1::a::b::c as p1;
}
component pss_top { consumer_pkg::p1::my_s v; }
""")
    assert len(errs) == 1 and "'p1'" in errs[0]


def test_a_wildcard_import_does_not_carry_an_alias():
    errs = errors(PKGS + """
package consumer_pkg {
  import pkg1::a::b::c as p1;
}
component pss_top {
  import consumer_pkg::*;
  p1::my_s v;
}
""")
    assert len(errs) == 1 and "'p1'" in errs[0]


def test_an_import_and_an_alias_of_one_package_are_both_kept():
    """They used to be merged as duplicates, which dropped the alias."""
    assert errors("""
package A { struct s {} }
component pss_top {
  import A;
  import A as X;
  struct w { X::s f; A::s g; }
}
""") == []


def test_two_aliases_of_one_name_in_one_scope():
    """Repro d5 and Ex. 260: one error, and the first alias still resolves."""
    errs = errors("""
package A { struct s {} }
package B { struct t {} }
component pss_top {
  import A as X;
  import B as X;
  struct w { X::s f; }
}
""")
    assert errs == [
        "package alias 'X' is already declared in this scope; two aliases in "
        "one scope shall not share a name (18.1.4)"]


def test_the_same_alias_name_in_two_statements_is_legal():
    assert errors("""
package A { struct s {} }
package B { struct t {} }
package P { import A as X; struct u { X::s f; } }
package P { import B as X; struct v { X::t f; } }
component pss_top { }
""") == []


def test_ex260_an_alias_named_like_a_package_in_its_namespace():
    errs = errors("""
package P {
  package foo {}
  package bar {}
}
package P {
  import bar as foo;
  import foo as my_alias;
  import bar as my_alias;
}
component pss_top { }
""")
    assert errs == [
        "package alias 'foo' has the same name as a package declared in "
        "package 'P'; rename the alias (18.1.4)",
        "package alias 'my_alias' is already declared in this scope; two "
        "aliases in one scope shall not share a name (18.1.4)"]


def test_an_alias_named_like_a_global_package():
    errs = errors("""
package A { struct s {} }
package B { }
import A as B;
component pss_top { }
""")
    assert errs == [
        "package alias 'B' has the same name as a package declared in the "
        "global scope; rename the alias (18.1.4)"]


def test_a_later_source_unit_may_declare_a_package_with_the_alias_name():
    """18.1.4: legal when the package comes in a subsequent source unit."""
    lib = ("lib.pss", "package A { struct s {} }\n")
    use = ("use.pss", "import A as B;\ncomponent pss_top { }\n")
    later = ("later.pss", "package B { }\n")
    assert markers_of([lib, use, later]) == []
    assert markers_of([lib, later, use]) == [
        ("use.pss", 1,
         "package alias 'B' has the same name as a package declared in the "
         "global scope; rename the alias (18.1.4)",
         [("later.pss", 1, "package 'B' declared here")])]


def test_a_global_alias_applies_to_its_own_file_only():
    lib = ("lib.pss", "package A { struct s {} }\n")
    a = ("a.pss", "import A as X;\nstruct a_s { X::s f; }\n")
    b = ("b.pss", "component pss_top { X::s f; }\n")
    errs = markers_of([lib, a, b])
    assert len(errs) == 1 and errs[0][0] == "b.pss" and "'X'" in errs[0][2]
