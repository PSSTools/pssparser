"""
Unit tests for the AST code generator (pyastbuilder).

These drive the generator directly on a small schema and inspect the emitted
source. They live in pssparser's suite because pyastbuilder has no working test
suite of its own -- its single test module had bit-rotted to the point of
failing at import, and still fails at HEAD once that is repaired.

Behavioural tests through a parsed AST cannot cover all of this. In particular,
`Annotation.is_standalone` is the *only* non-ctor `bool` in pssparser's whole
schema that does not carry an explicit `init:`; every other member happens to
follow that convention, so the uninitialized-member defect is invisible from
outside until someone adds a member that does not. Asserting on the generated
text is what actually pins the fix.

See docs/design/pss31-implementation-plan.md for the defect write-ups.
"""
import io
import os
import tempfile

import pytest

from astbuilder.ast import Ast
from astbuilder.parser import Parser as AstParser
from astbuilder.linker import Linker
from astbuilder.gen_cpp import GenCPP


def _load(doc):
    ast = Ast()
    AstParser(ast).parse(io.StringIO(doc))
    Linker().link(ast)
    return ast


def _gen_cpp(doc):
    """Generate C++ for `doc` and return {filename: content}."""
    ast = _load(doc)
    with tempfile.TemporaryDirectory() as d:
        GenCPP(d, "testast", None, None).generate(ast)
        out = {}
        for root, _, files in os.walk(d):
            for f in files:
                with open(os.path.join(root, f)) as fp:
                    out[f] = fp.read()
        return out


# ---------------------------------------------------------------------------
# Member initialization
# ---------------------------------------------------------------------------
#
# Generated constructors initialize only the `is_ctor` members, and the ctor
# body assigns only members carrying an explicit `init:`. Everything else was
# left reading whatever was on the heap.

SCHEMA_UNINIT = """
classes:
- C1:
    - data:
        - ctor_i : int32_t
        - plain_b :
            type: bool
            is_ctor: false
        - plain_i :
            type: int32_t
            is_ctor: false
        - plain_s :
            type: string
            is_ctor: false
        - init_b :
            type: bool
            is_ctor: false
            init: true
"""


def test_non_ctor_bool_member_is_default_initialized():
    src = _gen_cpp(SCHEMA_UNINIT)["C1.h"]
    assert "bool m_plain_b = false;" in src, src


def test_non_ctor_integer_member_is_default_initialized():
    src = _gen_cpp(SCHEMA_UNINIT)["C1.h"]
    assert "int32_t m_plain_i = 0;" in src, src


def test_class_typed_member_gets_no_initializer():
    """std::string already default-constructs; an initializer would be noise."""
    src = _gen_cpp(SCHEMA_UNINIT)["C1.h"]
    assert "std::string m_plain_s;" in src, src


def test_member_with_explicit_init_is_left_to_the_constructor_body():
    """
    A declaration initializer would be redundant with the ctor-body assignment,
    and would silently disagree with it if the two ever diverged.
    """
    out = _gen_cpp(SCHEMA_UNINIT)
    assert "bool m_init_b;" in out["C1.h"], out["C1.h"]
    assert "m_init_b = true;" in out["C1.cpp"], out["C1.cpp"]


def test_ctor_member_is_not_double_initialized():
    """A ctor parameter is set in the init list; it must not also be defaulted."""
    out = _gen_cpp(SCHEMA_UNINIT)
    assert "int32_t m_ctor_i;" in out["C1.h"], out["C1.h"]
    assert "m_ctor_i(ctor_i)" in out["C1.cpp"], out["C1.cpp"]


# ---------------------------------------------------------------------------
# Floating-point scalar members
# ---------------------------------------------------------------------------
#
# `TypeKind` covered string, bool and the sized integers only, so a `double`
# member failed generation outright with "user-defined type double is not
# declared".

SCHEMA_FLOAT = """
classes:
- C1:
    - data:
        - d : double
        - f : float
        - d2 :
            type: double
            is_ctor: false
"""


@pytest.mark.parametrize("decl", ["double m_d;", "float m_f;"])
def test_floating_point_members_generate(decl):
    src = _gen_cpp(SCHEMA_FLOAT)["C1.h"]
    assert decl in src, src


def test_non_ctor_floating_point_member_is_default_initialized():
    src = _gen_cpp(SCHEMA_FLOAT)["C1.h"]
    assert "double m_d2 = 0.0;" in src, src


def test_floating_point_accessors_generate():
    src = _gen_cpp(SCHEMA_FLOAT)["C1.h"]
    assert "getD()" in src, src
    assert "setD(" in src, src


# ---------------------------------------------------------------------------
# Plural list accessors
# ---------------------------------------------------------------------------
#
# The generated `getXs()` emitted `ret.append(__ep.accept(of._hndl))`, but
# `accept()` returns void -- so every list-of-node property returned a list of
# None while the singular `getX(i)` worked.

SCHEMA_LIST = """
classes:
- C1:
    - data:
        - f1 : int32_t
- C2:
    - data:
        - items: list<UP<C1>>
"""


def _gen_pyx(doc):
    from astbuilder.pyext_gen import PyExtGen
    ast = _load(doc)
    with tempfile.TemporaryDirectory() as d:
        PyExtGen(d, "ast", "test.ast", None, None).generate(ast)
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".pyx"):
                    with open(os.path.join(root, f)) as fp:
                        return fp.read()
    raise AssertionError("no .pyx generated")


def test_plural_accessor_reads_the_object_back_off_the_factory():
    pyx = _gen_pyx(SCHEMA_LIST)
    assert "ret.append(of._obj)" in pyx, \
        "plural accessor does not append the constructed wrapper"


def test_plural_accessor_does_not_append_the_result_of_accept():
    """`accept()` returns void, so its result is always None."""
    pyx = _gen_pyx(SCHEMA_LIST)
    assert "ret.append(__ep.accept(" not in pyx, \
        "plural accessor still appends the (void) result of accept()"
