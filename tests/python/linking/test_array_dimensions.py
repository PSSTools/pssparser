"""A declared array's size expression, resolved where it is written.

CL-N2.  ``bit[32] a[N]`` is not a reference like the others: AstBuilderInt
rewrites it into the builtin generic ``array<bit[32], N>``, and ``array`` is
declared in BuiltinsFactory's own global scope rather than in the user's
symbol tree.  The dimension was the one template argument that arrives as an
**already-parsed expression** rather than as a type identifier, and the
expression form was not resolved at the use site at all -- so the unresolved
expression was copied into the specialization and looked up in the generic's
declaring scope, which for ``array`` is the builtins.

The old symptom was a root-only lookup with a suggestion naming a *package*::

    bit[32] a1[N];      // unknown identifier 'N'; did you mean 'p'?

Every case below failed that way, and each of them is an ordinary constant
that resolves perfectly well in the same scope when written anywhere else --
in a constraint, in an initializer, as a ``bit[N]`` width.

Two cautions for anyone extending this file.

* **Vary the element type.**  ``array<bit[32], N>`` and ``array<bit[32], PN>``
  compare *equal* and share one specialization, because
  ``TaskCompareParamLists::valueParamDfltEqual`` returns true for any
  expression form it does not recognize (its own defect, xfailed in
  ``test_template_identity.py``).  Two broken dimensions with the same element
  type therefore report *one* error, and a change that halves an error count
  may have merged specializations rather than resolved anything.
* **The qualified form was never actually fine.**  The original write-up
  recorded ``a4[c_c::N]`` as working; it only looked that way because it
  collapsed into a preceding specialization.  On its own it failed too.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# The cases that failed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,src", [
    ("component-scope static const", """
        package p {
            component c_c {
                static const int N = 4;
                bit[32] a[N];
            }
        }
    """),
    ("package-scope const, used in a component", """
        package p {
            const int PN = 4;
            component c_c {
                bit[32] a[PN];
            }
        }
    """),
    ("package-scope const, used in a struct", """
        package p {
            const int PN = 4;
            struct s_s {
                bit[32] a[PN];
            }
        }
    """),
    ("struct-scope static const", """
        package p {
            struct s_s {
                static const int SN = 3;
                bit[32] a[SN];
            }
        }
    """),
    ("const imported from another package", """
        package sizes { const int PKG_N = 4; }
        package p {
            import sizes::*;
            component c_c {
                bit[32] a[PKG_N];
            }
        }
    """),
    ("qualified by the enclosing component", """
        package p {
            component c_c {
                static const int N = 4;
                bit[32] a[c_c::N];
            }
        }
    """),
    ("qualified by another package", """
        package sizes { const int PKG_N = 4; }
        package p {
            component c_c {
                bit[32] a[sizes::PKG_N];
            }
        }
    """),
    ("inside a function body", """
        package p {
            component c_c {
                static const int N = 4;
                function void f() {
                    bit[32] a[N];
                }
            }
        }
    """),
])
def test_an_array_dimension_resolves_in_the_scope_that_declares_it(label, src):
    assert_clean([("t.pss", src)])


def test_every_dimension_in_one_scope_resolves():
    """The mixed case, with distinct element types so nothing can collapse.

    This is the shape that first reported the defect, and the one that caught
    the stack overflow described below: resolving ``c_c::N`` by way of
    ``TaskResolveRefs::visitExprRefPathStatic`` ran a TaskIsPyRef probe that
    walked back into the very field being resolved, recursing until the stack
    ran out.  It needs an action present to trigger, hence ``x_a``.
    """
    assert_clean([("t.pss", """
        package sizes { const int PKG_N = 4; }
        package p {
            import sizes::*;
            struct s_s {
                static const int SN = 3;
                bit[4] sa[SN];
            }
            component c_c {
                static const int N = 5;
                bit[32] a1[N];
                bit[16] a2[PKG_N];
                bit[8]  a3[sizes::PKG_N];
                bit[2]  a4[c_c::N];
                function void f() {
                    bit[64] la[N];
                    bit[63] lb[PKG_N];
                }
                action x_a { rand int i; constraint i < N; }
            }
        }
    """)])


def test_a_dimension_naming_the_enclosing_generics_parameter_still_rebinds():
    """The guard on the other half of the fix.

    Carrying a resolved target through ``TaskCopyAst`` is switched on for a
    template *argument* only.  A reference in a generic's **body** must be
    re-resolved against each specialization, so if
    ``setPreserveExprTargets`` were left on for the whole copy, ``a[N]`` below
    would freeze at the unspecialized declaration's ``N`` and every
    specialization of ``S`` would share one dimension.
    """
    assert_clean([("t.pss", """
        package p {
            struct S <int N = 2> {
                bit[8]  a[N];
                bit[16] b[N];
            }
            component c_c {
                S<4> s4;
                S<8> s8;
                S<>  sd;
            }
        }
    """)])


# ---------------------------------------------------------------------------
# ...and the cases that must still fail
# ---------------------------------------------------------------------------

def test_an_unknown_dimension_is_still_reported():
    """Resolving at the use site must not turn a real error into silence."""
    assert_rejects([("t.pss", """
        package p {
            component c_c {
                bit[32] a[NOSUCH];
            }
        }
    """)], "unknown identifier 'NOSUCH'")


def test_an_unknown_qualifier_is_still_reported():
    assert_rejects([("t.pss", """
        package p {
            component c_c {
                bit[32] a[nosuchscope::N];
            }
        }
    """)], "failed to resolve symbol nosuchscope")


def test_an_unknown_dimension_is_reported_once():
    """Not twice.

    The dimension is now resolved at the use site *and* carried into the
    specialization.  A failure at the use site is deliberately silent so the
    single diagnostic keeps coming from where it always did; if that guard is
    removed this test reports the name twice.
    """
    res = assert_rejects([("t.pss", """
        package p {
            component c_c {
                bit[32] a[NOSUCH];
            }
        }
    """)])
    # Counting the message, not the name: the name also appears in the echoed
    # source line under it.
    assert res.output.count("unknown identifier 'NOSUCH'") == 1, res.describe()
