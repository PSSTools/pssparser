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


# ---------------------------------------------------------------------------
# gen-wasm: the AST wire format
# ---------------------------------------------------------------------------
#
# One generator emits both halves of this format, which is the point of it --
# a serializer and a deserializer from different schema revisions put fields in
# the wrong slots silently. That same property is why the round-trip test in
# `ts/test/serialize.test.ts` cannot see a *symmetric* defect: both halves agree
# whether or not either is right. So the cases below assert on the emitted text,
# where the two halves can be compared against each other and against the
# schema.
#
# `ts/test/ast-parity.test.ts` is the counterpart with independent ground truth.

def _gen_wasm(doc):
    """Generate both halves for `doc` and return {filename: content}."""
    from astbuilder.gen_wasm import GenWasm
    ast = _load(doc)
    with tempfile.TemporaryDirectory() as d:
        cpp, ts = os.path.join(d, "cpp"), os.path.join(d, "ts")
        GenWasm(cpp, ts, None).generate(ast)
        out = {}
        for sub in (cpp, ts):
            for f in os.listdir(sub):
                with open(os.path.join(sub, f)) as fp:
                    out[f] = fp.read()
        return out


def _visit_body(section, cls):
    """The body of `visit<cls>` within one generated visitor class.

    Split on the closing brace at the method's own indent rather than on the
    first `}`: the emitted guard is `if (!enter(i, 3)) { return; }` all on one
    line, so a naive split stops before any field.
    """
    head = "    void visit%s(I%s *i) override {\n" % (cls, cls)
    assert head in section, "no visit%s in this visitor" % cls
    return section.split(head)[1].split("\n    }\n")[0]


SCHEMA_WASM = """
classes:
- Base:
    - data:
        - name : string
        - flag :
            type: bool
            is_ctor: false
- Derived:
    - super: Base
    - data:
        - child :
            type: UP<Base>
            is_ctor: false
        - back:
            type: P<Base>
            is_ctor: false
        - kids:
            type: list<UP<Base>>
            is_ctor: false
        - table:
            type: map<string,int32_t>
            is_ctor: false
        - where:
            type: Loc
            is_ctor: false
structs:
- Loc:
    - data:
        - line : int32_t
        - col : int32_t
"""


def test_both_halves_are_emitted():
    out = _gen_wasm(SCHEMA_WASM)
    assert set(out) == {"AstSerializer.h", "AstSerializer.cpp", "deserialize.ts"}


def test_inherited_fields_are_written_base_first():
    """The reader assigns into a constructed object and the writer reads off
    accessors, so the only requirement is that the two agree -- but they must
    agree, and base-first is the order both are generated in."""
    cpp = _gen_wasm(SCHEMA_WASM)["AstSerializer.cpp"]
    body = _visit_body(cpp.split("class AstWriter")[1], "Derived")
    assert body.index("getName()") < body.index("getFlag()") < body.index("getChild()")


def test_scalar_widths_match_between_the_halves():
    """The reader has no per-node offset to resynchronise on: one field read at
    the wrong width corrupts every node after it. Same widths, same order."""
    out = _gen_wasm(SCHEMA_WASM)
    cpp_body = _visit_body(out["AstSerializer.cpp"].split("class AstWriter")[1], "Derived")
    ts_body = out["deserialize.ts"].split("// Derived\n")[1].split("},")[0]

    # `str` then `b` on the C++ side; `str()` then `bool()` on the TS side.
    assert cpp_body.index("buf.str(") < cpp_body.index("buf.b(")
    assert ts_body.index("r.str()") < ts_body.index("r.bool()")


def test_owning_pointers_are_traversed_and_raw_pointers_are_not():
    """Ownership decides the walk, not the `visit:` flag. A raw pointer's target
    is owned elsewhere in the tree; recursing through it would assign a second
    id to a node that already has one, or wander into another compilation
    unit."""
    cpp = _gen_wasm(SCHEMA_WASM)["AstSerializer.cpp"]
    body = _visit_body(cpp.split("class AstIndexer")[1].split("class AstWriter")[0], "Derived")
    assert "getChild()" in body, "owning UP<> field is not traversed"
    assert "getKids()" in body, "owning list element is not traversed"
    assert "getBack()" not in body, "raw pointer is traversed; it must not be"


def test_every_reference_is_written_as_an_id_including_raw_ones():
    cpp = _gen_wasm(SCHEMA_WASM)["AstSerializer.cpp"]
    body = _visit_body(cpp.split("class AstWriter")[1], "Derived")
    assert "buf.i32(idOf(i->getChild()));" in body
    assert "buf.i32(idOf(i->getBack()));" in body


def test_maps_are_emitted_in_key_order():
    """std::unordered_map iteration order is an implementation detail. Emitting
    it verbatim would make the buffer non-reproducible and the resulting JS
    Map's insertion order arbitrary."""
    cpp = _gen_wasm(SCHEMA_WASM)["AstSerializer.cpp"]
    assert "std::sort(" in cpp
    assert "return a->first < b->first;" in cpp


def test_struct_fields_are_inlined_by_value_on_both_sides():
    out = _gen_wasm(SCHEMA_WASM)
    assert "buf.i32(i->getWhere().line);" in out["AstSerializer.cpp"]
    assert "buf.i32(i->getWhere().col);" in out["AstSerializer.cpp"]
    # One mk<Name>() call: JS evaluates arguments left to right, so the reads
    # happen in declaration order, which is the order they were written in.
    assert "mkLoc(r.i32(), r.i32())" in out["deserialize.ts"]


def test_class_tags_agree_between_the_halves():
    """The tag is an index into ast.classes on both sides. If they disagreed,
    every node would be constructed as the wrong class."""
    out = _gen_wasm(SCHEMA_WASM)
    ast = _load(SCHEMA_WASM)
    for i, c in enumerate(ast.classes):
        assert "if (!enter(i, %d)) { return; }" % i in out["AstSerializer.cpp"]
    ctors = out["deserialize.ts"].split("const CTORS")[1].split("];")[0]
    assert [l.strip().rstrip(",") for l in ctors.splitlines() if l.strip().startswith("cls.")] == \
        ["cls." + c.name for c in ast.classes]


def test_schema_hash_is_not_emitted_here():
    """Owned by scripts/gen_schema_hash.py, which already runs in the WASM
    configure step and the TS build. Two producers of one file is the failure
    the hash exists to catch."""
    out = _gen_wasm(SCHEMA_WASM)
    assert not any("schema_hash" in f or "schemaHash" in f for f in out)


def test_unsupported_struct_field_is_a_generator_error_not_bad_output():
    """A struct holding a pointer has no encoding here -- structs are written
    inline by value and carry no id. Failing loudly beats emitting code that
    compiles and decodes garbage."""
    from astbuilder.gen_wasm import GenWasmError
    doc = """
classes:
- C1:
    - data:
        - s : Bad
structs:
- Bad:
    - data:
        - p : UP<C1>
"""
    with pytest.raises(GenWasmError):
        _gen_wasm(doc)
