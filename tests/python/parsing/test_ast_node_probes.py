"""AST-node probes for the AST-coverage effort (docs/ast-coverage-plan.md).

Unlike the sibling parsing tests, which only assert ``assert_parse_ok`` plus
symbol presence, these probes walk the *pre-link* AST (``parser._files``) and
assert that each construct actually produces the expected AST node with the
expected fields. They are the regression net for the grammar / AST-builder
changes that plan introduces.

A test asserting only ``assert_parse_ok`` is not coverage of a language
feature: the monitor subsystem stayed green for its whole life with every
monitor activity body empty. That is what these probes exist to catch.

Constructs that the parser does NOT yet surface are marked
``xfail(strict=True)`` with a ``# COVERAGE:`` note naming the plan item that
fixes them. When the fix lands, the test XPASSes -> strict xfail turns that
into a hard failure, which is the signal to drop the marker. Do not delete an
xfail marker without making its body pass.

The ``# DETOX ...`` notes below are a historical record of the earlier
pssparser-detox effort, whose plan document no longer exists; every one of
them is closed. New notes use ``# COVERAGE:``.

The companion file ``test_unrepresented_constructs.py`` asserts the *other*
side of the same contract: that an unimplemented construct is at least loud
(PSS116) rather than silent. A construct closed here should lose its case
there in the same commit.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss  # noqa: E402


# ---------------------------------------------------------------------------
# Pre-link AST walking helpers
# ---------------------------------------------------------------------------

def _find_nodes(parser, type_name):
    """Return all pre-link AST nodes whose class name == type_name.

    Walks ``parser._files`` (skipping index 0, the builtin/stdlib scope). Note
    that ``children()`` does *not* descend into constraint-statement lists, so we
    also follow ``numConstraints()``/``getConstraint()`` on constraint scopes.
    """
    found = []
    seen = set()

    def visit(node):
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        if type(node).__name__ == type_name:
            found.append(node)
        try:
            kids = list(node.children())
        except Exception:
            kids = []
        for k in kids:
            visit(k)
        # Constraint scopes (ConstraintBlock, ConstraintStmtForeach/Forall, ...)
        # expose their body via numConstraints()/getConstraint(), not children().
        if hasattr(node, "numConstraints") and hasattr(node, "getConstraint"):
            try:
                n = node.numConstraints()
            except Exception:
                n = 0
            for i in range(n):
                visit(node.getConstraint(i))

    for scope in parser._files[1:]:
        visit(scope)
    return found


def _parse_only(code, parser):
    """Parse without linking; return the parser (for pre-link AST inspection)."""
    parser.parses([("test.pss", code)])
    return parser


# ---------------------------------------------------------------------------
# 1. forall  ->  ConstraintStmtForall   (DETOX Phase A1 / builder gap)
# ---------------------------------------------------------------------------
# Grammar accepts `forall`, but visitForall_constraint_item is a TODO stub in
# AstBuilderInt.cpp, so no ConstraintStmtForall node is built today.

FORALL_SRC = """
struct S { rand int v; }
component pss_top {
    action A {
        rand S arr[4];
        constraint c { forall (it : S in arr) { it.v < 10; } }
    }
}
"""


def test_forall_builds_node(parser):
    # DETOX B0 (DONE): `forall` builds a ConstraintStmtForall and links cleanly.
    # The historical infinite-recursion was a cyclic AST traversal (forall ->
    # symtab -> getConstraint() back-pointer), fixed by `visit: false` on
    # ConstraintStmtForall.symtab in ast/constraint.yaml. Iterator member access
    # resolves via the iterator field placed at getConstraints()[0].
    p = _parse_only(FORALL_SRC, parser)
    nodes = _find_nodes(p, "ConstraintStmtForall")
    assert len(nodes) == 1
    fa = nodes[0]
    # iterator_id, type_id, ref_path are the populated fields
    assert fa.getIterator_id().getId() == "it"
    assert fa.getType_id() is not None
    assert fa.getRef_path() is not None
    # body constraint(s) preserved (iterator field at [0] + the body expr)
    assert fa.numConstraints() >= 1


# ---------------------------------------------------------------------------
# 4. do X with {}  ->  ActivityActionTypeTraversal.with_c   (DETOX Phase A2)
# ---------------------------------------------------------------------------
# This one already works: the inline constraint is captured in the AST today.

DO_WITH_SRC = """
component pss_top {
    action A { rand int x; }
    action B { A a; activity { do A with { x < 5; x > 0; } } }
}
"""


def test_do_with_inline_constraints_present(parser):
    p = _parse_only(DO_WITH_SRC, parser)
    travs = _find_nodes(p, "ActivityActionTypeTraversal")
    assert len(travs) == 1
    with_c = travs[0].getWith_c()
    assert with_c is not None, "do..with{} inline constraints dropped"
    assert with_c.numConstraints() == 2


# ---------------------------------------------------------------------------
# 5. pool [N]  ->  (no AST node today)   (DETOX Phase B1)
# ---------------------------------------------------------------------------
# The pool declaration is fully absorbed during build; no AST node carries the
# size N. There is no ComponentPool AST class yet, so we probe by asserting the
# component body has a child node mentioning the pool. Marked xfail until B1.

POOL_SRC = """
buffer Buf { int x; }
component pss_top {
    pool [4] Buf bufp;
    bind bufp *;
}
"""


def test_pool_size_reaches_ast(parser):
    # DETOX B1: pool now builds a FieldPool node carrying the size literal.
    p = _parse_only(POOL_SRC, parser)
    pools = _find_nodes(p, "FieldPool")
    assert len(pools) == 1
    fp = pools[0]
    assert fp.getName().getId() == "bufp"
    assert fp.getType() is not None
    size = fp.getSize()
    assert size is not None and size.getValue() == 4


def test_pool_unsized_has_no_size(parser):
    # An unsized pool builds the node with size==None.
    p = _parse_only("buffer Buf { int x; } component pss_top { pool Buf bufp; }", parser)
    pools = _find_nodes(p, "FieldPool")
    assert len(pools) == 1
    assert pools[0].getSize() is None


# ---------------------------------------------------------------------------
# 6. bind pool *;  ->  ComponentBind AST node   (DETOX Phase B1b — DONE)
# ---------------------------------------------------------------------------
# The component-level `bind` directive builds a ComponentBind node carrying the
# pool path, the wildcard flag, and one ComponentBindTarget per entry. Targets
# are structural but unresolved (no ref resolution), so link() stays loop-free.
#
# COVERAGE 5.6 (DONE): targets used to be raw dotted text, which lost the
# `[0..3]` index selections entirely and collapsed a mixed list `{a.x, *}` to a
# flag plus a partial list. See test_bind_target_paths_are_structured below.

BIND_SRC = """
buffer Buf { int x; }
component pss_top {
    pool Buf p;
    bind p *;
    pool Buf q;
    bind q { producer.out, consumer.inp };
    action producer { output Buf out; }
    action consumer { input Buf inp; }
}
"""


def _bind_target_text(t):
    """Render a ComponentBindTarget back to its dotted source form.

    This is what the AST used to store *instead* of structure. Reconstructing
    it from the nodes proves the structure is a superset of the old text.
    """
    if t.getIs_wildcard():
        return "*"
    parts = [e.getId().getId() for e in t.getPathList()]
    parts.append(".".join(e.getId().getId() for e in t.getType_id().getElems()))
    parts.append(t.getField().getId())
    return ".".join(parts)


def _ranges(rl):
    """[(lhs, rhs)] for a domain-open-range-list; rhs is None for a single."""
    if rl is None:
        return None
    return [(v.getLhs().getValue(),
             None if v.getSingle() else v.getRhs().getValue())
            for v in rl.getValues()]


def test_bind_builds_node(parser):
    p = _parse_only(BIND_SRC, parser)
    binds = _find_nodes(p, "ComponentBind")
    assert len(binds) == 2
    by_pool = {b.getPool_path(): b for b in binds}

    wild = by_pool["p"]
    assert wild.getIs_wildcard() is True
    # The wildcard is a target like any other, not the absence of one.
    assert [t.getIs_wildcard() for t in wild.getTargets()] == [True]

    targeted = by_pool["q"]
    assert targeted.getIs_wildcard() is False
    assert [_bind_target_text(t) for t in targeted.getTargets()] == [
        "producer.out", "consumer.inp"]


BIND_PATHS_SRC = """
buffer Buf { int x; }
component leaf { action prod { output Buf out; } }
component pss_top {
    leaf sub[4];
    pool Buf p;
    bind p { sub[0..3].prod.out };
    pool Buf q;
    bind q { prod.out, * };
    pool Buf r;
    bind r { prod.out[2] };
    action prod { output Buf out; }
}
"""


def test_bind_target_paths_are_structured(parser):
    """The `[0..3]` on a component-path element must be readable as a range."""
    p = _parse_only(BIND_PATHS_SRC, parser)
    by_pool = {b.getPool_path(): b for b in _find_nodes(p, "ComponentBind")}

    (target,) = by_pool["p"].getTargets()
    (elem,) = target.getPathList()
    assert elem.getId().getId() == "sub"
    assert _ranges(elem.getRange()) == [(0, 3)]
    # The bind item itself is separate from the component path.
    assert [e.getId().getId() for e in target.getType_id().getElems()] == ["prod"]
    assert target.getField().getId() == "out"
    assert target.getRange() is None


def test_bind_mixed_list_keeps_every_entry(parser):
    """`{ prod.out, * }` is two targets in order, not one target plus a flag."""
    p = _parse_only(BIND_PATHS_SRC, parser)
    by_pool = {b.getPool_path(): b for b in _find_nodes(p, "ComponentBind")}

    bind = by_pool["q"]
    assert [_bind_target_text(t) for t in bind.getTargets()] == ["prod.out", "*"]
    # is_wildcard survives as a summary of the list, not a substitute for it.
    assert bind.getIs_wildcard() is True


def test_bind_item_index_is_captured(parser):
    """An index on the bind item (`prod.out[2]`) is distinct from a path index."""
    p = _parse_only(BIND_PATHS_SRC, parser)
    by_pool = {b.getPool_path(): b for b in _find_nodes(p, "ComponentBind")}

    (target,) = by_pool["r"].getTargets()
    assert target.getPathList() == []
    assert _ranges(target.getRange()) == [(2, None)]


def test_bind_link_is_loop_free(parser):
    # De-risk gate: building the bind node must not make link() hang or fail.
    p = _parse_only(BIND_SRC, parser)
    root = p.link()
    assert root is not None


# ---------------------------------------------------------------------------
# 2/3. covergroup + cross  ->  Covergroup AST node   (DETOX Phase B2 — DONE)
# ---------------------------------------------------------------------------
# The inline covergroup with coverpoints + cross builds a Covergroup node with
# CovergroupCoverpoint / CovergroupCross children.

COVERGROUP_SRC = """
component pss_top {
    action A {
        rand int x; rand int y;
        covergroup {
            cp_x : coverpoint x;
            cp_y : coverpoint y;
            cr : cross cp_x, cp_y;
        } cg_inst;
    }
}
"""


def test_covergroup_builds_node(parser):
    p = _parse_only(COVERGROUP_SRC, parser)
    cgs = _find_nodes(p, "Covergroup")
    assert len(cgs) == 1
    cg = cgs[0]
    assert cg.getName().getId() == "cg_inst"
    # Use the singular accessors (plural list accessors wrap via accept -> None)
    cp_names = [cg.getCoverpoint(i).getName().getId() for i in range(cg.numCoverpoints())]
    assert cp_names == ["cp_x", "cp_y"]
    assert cg.numCrosses() == 1
    cx = cg.getCrosse(0)
    assert cx.getName().getId() == "cr"
    xnames = [cx.getCoverpoint_name(j).getId() for j in range(cx.numCoverpoint_names())]
    assert xnames == ["cp_x", "cp_y"]


# ---------------------------------------------------------------------------
# 7. fill  ->  rejected by design   (DETOX Phase C1 — DONE)
# ---------------------------------------------------------------------------
# `fill` is a non-LRM Perspec extension and was deliberately dropped (C1): it is
# not a keyword and never becomes an AST node. The native parser rejects it; the
# pssc front end turns that into a friendly diagnostic (tested in pssc). This
# probe just pins the grammar-level rejection so nobody silently re-adds it.

FILL_SRC = """
component pss_top {
    action A { activity { fill { do B; } } }
    action B {}
}
"""


def test_fill_is_rejected(parser):
    from pssparser import ParseException
    with pytest.raises(ParseException):
        _parse_only(FILL_SRC, parser)


# ---------------------------------------------------------------------------
# List accessors return real nodes
# ---------------------------------------------------------------------------
#
# The generated getChildren() appended the *return value* of accept(), which
# is void -- so it yielded a list of None while getChild(i), which reads
# of._obj after accepting, worked. Every documented traversal idiom went
# through getChildren(), so none of them worked.

def test_get_children_returns_nodes():
    from pssparser import Parser

    p = Parser()
    p.parses([("m.pss", "component pss_top { action A { int x; } action B { } }\n")])
    root = p.link()

    unit = None
    for i in range(root.numUnits()):
        u = root.getUnit(i)
        if u is not None and u.getFileid() == 1:
            unit = u
    assert unit is not None

    kids = unit.getChildren()
    assert kids, "getChildren() returned nothing"
    assert all(k is not None for k in kids), \
        "getChildren() yielded None: %r" % (kids,)


def test_get_children_agrees_with_get_child():
    """The two accessors must return the same nodes in the same order."""
    from pssparser import Parser

    p = Parser()
    p.parses([("m.pss", "component pss_top { action A { } action B { } }\n")])
    root = p.link()

    unit = next(
        root.getUnit(i) for i in range(root.numUnits())
        if root.getUnit(i) is not None and root.getUnit(i).getFileid() == 1
    )
    comp = unit.getChildren()[0]

    by_list = [type(c).__name__ for c in comp.getChildren()]
    by_index = [type(comp.getChild(i)).__name__ for i in range(comp.numChildren())]
    assert by_list == by_index, (by_list, by_index)


# ---------------------------------------------------------------------------
# access modifier groups  ->  Field.attr   (COVERAGE plan item 2.2)
# ---------------------------------------------------------------------------
# `private:` is a *label*: it sets the access modifier for every subsequent
# declaration in the scope. Before 2.2 the label was discarded entirely, so
# fields after it were built with attr == 0 and read as public -- a consumer
# enforcing access saw no violation. The group form and the inline form must
# now produce identical attrs.

def _fields_by_name(parser, src):
    p = _parse_only(src, parser)
    return {f.getName().getId(): f for f in _find_nodes(p, "Field")}


def test_access_group_and_inline_forms_agree(parser):
    from pssparser.ast import FieldAttr

    # Both forms declare x and y, so a single parse would collide the names in
    # the flat dict; probe each form separately.
    grouped = _fields_by_name(
        parser, "package p { struct s { private: int x; protected: int y; } }")
    inline = _fields_by_name(
        parser, "package p { struct s { private int x; protected int y; } }")
    for name in ("x", "y"):
        assert int(grouped[name].getAttr()) == int(inline[name].getAttr()), \
            "group and inline access modifiers disagree for %s" % name
    assert int(grouped["x"].getAttr()) & int(FieldAttr.Private)
    assert int(grouped["y"].getAttr()) & int(FieldAttr.Protected)


def test_inline_access_modifier_overrides_the_group_label(parser):
    """`public int b;` under `private:` is public -- the inline form wins."""
    fields = _fields_by_name(
        parser, "package p { struct s { private: int a; public int b; int c; } }")
    assert int(fields["a"].getAttr()) != 0, "the label was dropped"
    assert int(fields["b"].getAttr()) == 0, "inline `public` did not override"
    assert int(fields["c"].getAttr()) == int(fields["a"].getAttr()), \
        "the label stopped applying after an inline override"


def test_access_group_does_not_leak_into_a_nested_scope(parser):
    """A label applies to its own scope only, not to a type declared inside."""
    fields = _fields_by_name(
        parser,
        "component outer { private: int cf; action nested { int af; } }")
    assert int(fields["cf"].getAttr()) != 0
    assert int(fields["af"].getAttr()) == 0, \
        "the enclosing `private:` leaked into the nested action"


# ---------------------------------------------------------------------------
# default constraints  ->  ConstraintStmtDefault(Disable)   (plan item 2.3)
# ---------------------------------------------------------------------------
# Both AST classes existed and neither visitor built anything. The standard
# library's own addr_reg_pkg.pss uses `default permanent == false;`, so this
# gap was live on every parse.

DEFAULT_CONSTRAINT_SRC = """
package p {
    struct s {
        rand int x;
        rand int y;
        constraint c { default x == 3; default disable y; }
    }
}
"""


def test_default_constraints_build_nodes(parser):
    p = _parse_only(DEFAULT_CONSTRAINT_SRC, parser)

    defaults = _find_nodes(p, "ConstraintStmtDefault")
    assert len(defaults) == 1
    d = defaults[0]
    assert [e.getId().getId() for e in d.getHid().getElems()] == ["x"]
    assert d.getExpr() is not None, "the default value expression was dropped"

    disables = _find_nodes(p, "ConstraintStmtDefaultDisable")
    assert len(disables) == 1
    assert [e.getId().getId() for e in disables[0].getHid().getElems()] == ["y"]


def test_default_constraints_are_ordered_within_the_block(parser):
    """setIndex must place the statements in source order alongside siblings."""
    p = _parse_only("""
package p {
    struct s {
        rand int x;
        constraint c { x > 0; default x == 3; x < 9; }
    }
}
""", parser)
    blocks = [b for b in _find_nodes(p, "ConstraintBlock")
              if b.numConstraints() == 3]
    assert blocks, "expected one 3-statement constraint block"
    kinds = [type(blocks[0].getConstraint(i)).__name__ for i in range(3)]
    assert kinds == ["ConstraintStmtExpr", "ConstraintStmtDefault",
                     "ConstraintStmtExpr"], kinds


# ---------------------------------------------------------------------------
# import function  ->  FunctionImportType / lang   (plan items 2.6, 5.2)
# ---------------------------------------------------------------------------
# The two-step form (`import function pkg::f;`) hit a literally empty branch,
# so FunctionImportType -- which exists -- was never constructed. The one-step
# form was built with "" for lang no matter what the source said.

IMPORT_FUNCTION_SRC = """
package p {
    function void f();
    import function p::f;
    import C function void g();
    import target C2 function void h();
    import function void plain();
}
"""


def test_two_step_import_builds_function_import_type(parser):
    p = _parse_only(IMPORT_FUNCTION_SRC, parser)
    types = _find_nodes(p, "FunctionImportType")
    assert len(types) == 1, "two-step `import function pkg::f;` built nothing"
    t = types[0].getType()
    assert t is not None
    assert [e.getId().getId() for e in t.getElems()] == ["p", "f"]


def test_import_function_language_is_captured(parser):
    from pssparser.ast import PlatQual

    p = _parse_only(IMPORT_FUNCTION_SRC, parser)
    protos = {n.getLang(): n for n in _find_nodes(p, "FunctionImportProto")}
    assert "C" in protos, "the language identifier was dropped"
    assert protos["C"].getPlat() == PlatQual.PlatQual_None
    assert protos["C2"].getPlat() == PlatQual.PlatQual_Target
    assert "" in protos, "an import with no language should carry no language"


# ---------------------------------------------------------------------------
# monitor handle declaration  ->  ActionHandleField   (plan item 2.7)
# ---------------------------------------------------------------------------
# `monitor_handle_declaration` and `action_handle_declaration` had the same
# shape, so the monitor alternative was unreachable and its builder hook could
# never fire. The grammar no longer claims a distinction no parser can make:
# both forms take the action production and build an ActionHandleField, and
# which kind of handle it is follows from resolving the type at link.
#
# The probe that matters is therefore not "which node class" -- it is that the
# declared name and type survive, since that is what a consumer needs to
# resolve the handle at all.

MONITOR_HANDLE_SRC = """
component c {
    action A { }
    monitor m1 { }
    monitor m2 {
        A a1;
        m1 h1, h2[4];
    }
}
"""


def test_monitor_handle_declaration_builds_a_handle_field(parser):
    p = _parse_only(MONITOR_HANDLE_SRC, parser)
    handles = {h.getName().getId(): h
               for h in _find_nodes(p, "ActionHandleField")}
    assert set(handles) == {"a1", "h1", "h2"}

    # The monitor handle names its monitor type, not something invented for it.
    h1_type = handles["h1"].getType()
    assert [e.getId().getId() for e in h1_type.getType_id().getElems()] == ["m1"]

    # An action handle in the same body is indistinguishable at this level --
    # that is the point: only resolving the type separates the two.
    a1_type = handles["a1"].getType()
    assert [e.getId().getId() for e in a1_type.getType_id().getElems()] == ["A"]


def test_monitor_handle_declaration_is_not_reported_as_a_gap(parser):
    """The construct is represented, so it must not claim to be unrepresented."""
    p = _parse_only(MONITOR_HANDLE_SRC, parser)
    unrepresented = [m for m in p.markers
                     if "not represented in the AST" in m["message"]]
    assert not unrepresented, \
        "\n".join(m["message"] for m in unrepresented)
