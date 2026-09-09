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
from test_helpers import parse_collect, parse_pss  # noqa: E402
import pssparser.ast as ast  # noqa: E402


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


_SKIP_ACCESSORS = frozenset([
    # Climbing these leaves the subtree: `parent` goes up, and `target` is the
    # linked tree's back-pointer into the AST.
    "getParent", "getTarget",
])


def _find_nodes_deep(parser, type_name):
    """Like _find_nodes, but reaches nodes that are not scope children.

    ``children()`` exists only on scopes, so it cannot reach an expression
    inside a constraint, a field's type, or a statement inside a function body.
    This walks every zero-argument ``getX()`` and every ``numX()``/``getX(i)``
    pair instead, which reaches all of them.

    Kept separate from ``_find_nodes`` rather than replacing it: the probes
    above assert exact counts against the scope-child view, and widening what
    they see would change what they mean.
    """
    found = []
    seen = set()
    # Every accessor call mints a fresh Python wrapper. Dropping one frees the
    # address, which the next wrapper is then free to reuse -- so an id()-keyed
    # `seen` starts reporting unvisited nodes as visited. Holding a reference to
    # each wrapper keeps the ids distinct for the length of the walk.
    alive = []

    def visit(node):
        if node is None or id(node) in seen:
            return
        alive.append(node)
        seen.add(id(node))
        if type(node).__name__ == type_name:
            found.append(node)
        for name in dir(node):
            if not name.startswith("get") or name in _SKIP_ACCESSORS:
                continue
            attr = getattr(node, name, None)
            if not callable(attr):
                continue
            # getX(i) paired with a count accessor: walk the list. The
            # generated names do not agree on plurality -- ConstraintBlock has
            # getConstraint(i)/numConstraints(), DataTypeString has
            # getIn_range(i)/numIn_range() -- so try both spellings.
            stem = name[3:]
            counter = None
            for cand in ("num" + stem, "num" + stem + "s", "num" + stem.rstrip("s")):
                c = getattr(node, cand, None)
                if callable(c):
                    counter = c
                    break
            if callable(counter):
                try:
                    n = counter()
                except Exception:
                    continue
                for i in range(n):
                    try:
                        visit(attr(i))
                    except Exception:
                        pass
                continue
            try:
                visit(attr())
            except Exception:
                pass
        try:
            kids = list(node.children())
        except Exception:
            kids = []
        for k in kids:
            visit(k)

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


# ---------------------------------------------------------------------------
# 9. Monitor activity bodies  (plan items 3.1-3.5, 3.7)
# ---------------------------------------------------------------------------
# Every braced monitor activity form used to build an empty node: the statement
# loop in each visitor was commented out. `concat` and `overlap` additionally
# built a MonitorActivitySequence, making the three indistinguishable.
#
# These probes assert the two things whose absence let that survive for so
# long: that a body is non-empty, and that the node class matches the keyword.

MONITOR_ACTIVITY_SRC = """
component c {
    action A { rand int v; }
    monitor M1 { }
    monitor M {
        A a;
        M1 h;
        constraint cb { a.v < 9; }
        activity {
            lbl: sequence { a; }
            concat { a; }
            overlap { a; }
            sched: schedule { a; }
            select { a; a; }
            eventually a;
            h;
            do M1;
            constraint { a.v < 4; }
            a;
        }
    }
}
"""


def _monitor_activity(parser):
    (decl,) = _find_nodes(parser, "MonitorActivityDecl")
    return decl


def test_monitor_activity_body_is_not_empty(parser):
    """The single assertion that would have caught this years ago."""
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    decl = _monitor_activity(p)
    assert len(decl.getChildren()) == 10


def test_monitor_activity_block_forms_are_distinguishable(parser):
    """`sequence`, `concat`, `overlap`, `schedule` and `select` are five classes.

    All five were built as -- or alongside -- MonitorActivitySequence, so a
    consumer could not tell a strict ordering from a gapless one.
    """
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    decl = _monitor_activity(p)
    kinds = [type(c).__name__ for c in decl.getChildren()]
    assert kinds[:6] == [
        "MonitorActivitySequence",
        "MonitorActivityConcat",
        "MonitorActivityOverlap",
        "MonitorActivitySchedule",
        "MonitorActivitySelect",
        "MonitorActivityEventually",
    ]


def test_monitor_activity_blocks_carry_their_statements(parser):
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    decl = _monitor_activity(p)
    for blk in decl.getChildren()[:4]:
        assert len(blk.getChildren()) == 1, type(blk).__name__
    # `select` requires at least two alternatives.
    assert len(decl.getChildren()[4].getChildren()) == 2


def test_monitor_activity_labels_are_attached(parser):
    """A label belongs to the block it prefixes, not to a nested one."""
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    decl = _monitor_activity(p)
    seq, concat, _, sched = decl.getChildren()[:4]
    assert seq.getLabel().getId() == "lbl"
    assert sched.getLabel().getId() == "sched"
    assert concat.getLabel() is None


def test_monitor_eventually_carries_its_operand(parser):
    """`eventually` was built with a null body -- and a null `condition` field
    for an expression the grammar has no place for."""
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    ev = decl_children = _monitor_activity(p).getChildren()[5]
    assert ev.getBody() is not None
    assert type(ev.getBody()).__name__ == "ActivityActionHandleTraversal"


def test_monitor_traversal_names_its_target(parser):
    """A monitor traversal is an *action* traversal node, and names its target.

    `MonitorActivityMonitorTraversal` built a node with a hard-coded null
    target, so it named nothing. It is gone: its grammar rule was spelled
    identically to `activity_action_traversal_stmt`, which precedes it, so it
    was never reached. Nothing in the syntax says whether `h;` traverses an
    action handle or a monitor handle -- only resolving the type does.
    """
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    by_handle, by_type = _monitor_activity(p).getChildren()[6:8]

    assert type(by_handle).__name__ == "ActivityActionHandleTraversal"
    assert [e.getId().getId()
            for e in by_handle.getTarget().getHier_id().getElems()] == ["h"]

    assert type(by_type).__name__ == "ActivityActionTypeTraversal"
    assert [e.getId().getId()
            for e in by_type.getTarget().getType_id().getElems()] == ["M1"]


def test_empty_monitor_traversal_subscript_is_rejected():
    """`h[];` parsed cleanly, because the removed rule mistranscribed the LRM.

    LRM B.11 has one optional subscript around a *required* expression;
    the grammar had an optional expression inside an optional subscript.
    """
    _, markers = parse_collect(
        "component c { monitor M1 { } monitor M { M1 h; activity { h[]; } } }")
    assert [m for m in markers if m["severity"] == "error"]


def test_monitor_activity_constraint_is_a_statement(parser):
    """A `constraint` among the activity statements keeps its position."""
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    c = _monitor_activity(p).getChildren()[8]
    assert type(c).__name__ == "MonitorConstraint"
    assert c.getConstraint() is not None


def test_monitor_body_constraint_is_an_ordinary_constraint_block(parser):
    """A constraint in the monitor *body* is not a MonitorConstraint.

    It builds the same ConstraintBlock an action or struct builds, so every
    constraint consumer sees one node kind rather than two.
    """
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    blocks = [b for b in _find_nodes(p, "ConstraintBlock")
              if b.getName() == "cb"]
    assert len(blocks) == 1


def test_monitor_handle_resolves_in_a_monitor_constraint():
    """The handle must be in the monitor's symbol table.

    ActionHandleField had no visitor in TaskBuildSymbolTree, so it reached the
    generic scope-child path: appended to the scope's children, never named.
    Nothing noticed while monitor bodies were dropped, because an action-body
    `A a;` is a plain Field -- ActionHandleField is only reachable from a
    monitor body or an activity.
    """
    parse_pss(
        "component c { action A { rand int v; }"
        " monitor M { A a; constraint c1 { a.v < 4; } } }")
    parse_pss(
        "component c { action A { rand int v; }"
        " action B { activity { A h; h; } constraint k { h.v < 4; } } }")


def test_monitor_activity_is_not_reported_as_a_gap(parser):
    p = _parse_only(MONITOR_ACTIVITY_SRC, parser)
    unrepresented = [m for m in p.markers
                     if "not represented in the AST" in m["message"]]
    assert not unrepresented, \
        "\n".join(m["message"] for m in unrepresented)


# ---------------------------------------------------------------------------
# 10. Cover statements (plan item 3.6)
# ---------------------------------------------------------------------------
# `cover` was the last monitor construct that parsed and built nothing.
# CoverStmtInline and CoverStmtReference existed for it, but both were shaped
# for a syntax PSS does not have: the reference form held an ExprRefPath, as if
# `cover` named a monitor *instance*, and the inline form held a single node
# rather than a body. LRM B.12 gives two forms, both component_body_items, both
# optionally labeled.

COVER_SRC = """
component pss_top {
    action A { rand int len; }

    monitor M {
        A a;
        activity { a; }
    }

    cover M;
    hs: cover M;

    cover {
        A a;
        constraint { a.len > 0; }
        activity { a; }
    }

    inline_cov: cover {
        A a;
        activity { a; }
    }
}
"""


def test_both_cover_forms_build_nodes(parser):
    p = _parse_only(COVER_SRC, parser)
    assert len(_find_nodes(p, "CoverStmtReference")) == 2
    assert len(_find_nodes(p, "CoverStmtInline")) == 2


def test_cover_reference_names_a_type(parser):
    """`cover M;` names a monitor type, not an instance.

    The class used to hold an ExprRefPath, which claimed the opposite. There
    is no syntax for covering an instance.
    """
    p = _parse_only(COVER_SRC, parser)
    ref = _find_nodes(p, "CoverStmtReference")[0]
    target = ref.getTarget()
    assert type(target).__name__ == "TypeIdentifier"
    assert [e.getId().getId() for e in target.getElems()] == ["M"]


def test_cover_labels_are_attached(parser):
    """Both forms take `label_identifier ':'`, and both must keep it."""
    p = _parse_only(COVER_SRC, parser)
    refs = _find_nodes(p, "CoverStmtReference")
    inlines = _find_nodes(p, "CoverStmtInline")
    assert [r.getLabel() and r.getLabel().getId() for r in refs] == [None, "hs"]
    assert [i.getLabel() and i.getLabel().getId()
            for i in inlines] == [None, "inline_cov"]


def test_cover_inline_carries_its_body(parser):
    """`cover { ... }` is an anonymous monitor body, so it is a scope."""
    p = _parse_only(COVER_SRC, parser)
    inline = _find_nodes(p, "CoverStmtInline")[0]
    kinds = [type(c).__name__ for c in inline.getChildren()]
    assert kinds == ["ActionHandleField", "ConstraintBlock",
                     "MonitorActivityDecl"]


def test_cover_inline_body_resolves_its_own_handles():
    """A handle declared inside `cover { }` must resolve inside it.

    The AST node is a plain Scope, so the linker builds a synthetic symbol
    scope for it; without that, `a` in the constraint resolves against the
    enclosing component and is not found.
    """
    parse_pss(
        "component c { action A { rand int len; }"
        " cover { A a; constraint { a.len > 0; } activity { a; } } }")


def test_cover_inline_handles_do_not_leak_into_the_component():
    """Two inline covers may each declare `a` without colliding.

    They are separate scopes. If the members were named in the enclosing
    component instead, the second `a` would be a duplicate declaration.
    """
    parse_pss(
        "component c { action A { rand int len; }"
        " cover { A a; activity { a; } }"
        " cover { A a; activity { a; } } }")


def test_monitor_activity_statements_do_not_leak_into_the_monitor(parser):
    """The linked monitor holds its activity, and not a copy of its contents.

    MonitorActivityDecl had no visitor in TaskBuildSymbolTree, so the generated
    one added the declaration and then walked its children with the monitor
    type scope still pushed -- appending every activity statement to the
    monitor a second time.
    """
    root = parse_pss(
        "component pss_top { action A { }"
        " monitor M { A a; activity { seq: sequence { a; a; } } } }")

    def find(node, name):
        if getattr(node, "getName", None) and node.getName() == name:
            return node
        for c in (node.getChildren() if hasattr(node, "getChildren") else []):
            hit = find(c, name)
            if hit is not None:
                return hit
        return None

    monitor = find(root, "M")
    assert monitor is not None
    kinds = [type(c).__name__ for c in monitor.getChildren()]
    assert kinds == ["ActionHandleField", "MonitorActivityDecl"]


def test_cover_target_is_resolved():
    """The named type reaches the reference pass.

    Building the node is only half of it: an undefined target has to be
    reported, or `cover` would be a hole in name checking. The type's *kind*
    is not checked yet -- `cover A;` naming an action is accepted.
    """
    _, markers = parse_collect("component c { cover NotThere; }")
    assert [m for m in markers if m["severity"] == "error"]


def test_cover_is_not_reported_as_a_gap(parser):
    p = _parse_only(COVER_SRC, parser)
    unrepresented = [m for m in p.markers
                     if "not represented in the AST" in m["message"]]
    assert not unrepresented, \
        "\n".join(m["message"] for m in unrepresented)


# ---------------------------------------------------------------------------
# 11. Activity constraint, randomize, super refs, string ranges
#     (plan items 1.3, 5.1/5.3, 5.4, 5.5)
# ---------------------------------------------------------------------------

ACTIVITY_CONSTRAINT_SRC = """
component c {
    action a {
        rand int x;
        activity {
            constraint { x < 10; x > 1; }
            constraint x != 5;
        }
    }
}
"""


def test_activity_constraint_builds_a_statement(parser):
    """`constraint` among the activity statements is an ActivityConstraint.

    Both the braced and the single-item forms of `constraint_set` are accepted
    there, and both must build.
    """
    p = _parse_only(ACTIVITY_CONSTRAINT_SRC, parser)
    nodes = _find_nodes(p, "ActivityConstraint")
    assert len(nodes) == 2
    assert all(n.getConstraint() is not None for n in nodes)
    # The braced form keeps its two items rather than collapsing to one.
    braced = nodes[0].getConstraint()
    assert braced.numConstraints() == 2


def test_activity_constraint_is_not_a_constraint_block(parser):
    """It is a statement, not a block hoisted out of the activity.

    Its position among the activity statements is the whole point; a
    ConstraintBlock in the action body would lose that.
    """
    p = _parse_only(ACTIVITY_CONSTRAINT_SRC, parser)
    named = [b for b in _find_nodes(p, "ConstraintBlock")]
    assert not named


RANDOMIZE_SRC = """
package p { struct s { rand int x; } }
component c {
    function void f() {
        p::s v;
        randomize v with { v.x < 4; v.x > 0; };
    }
}
"""


def test_randomize_keeps_its_target_and_constraints(parser):
    """`randomize v with { ... }` dropped both halves and built a bare node."""
    p = _parse_only(RANDOMIZE_SRC, parser)
    nodes = _find_nodes_deep(p, "ProceduralStmtRandomize")
    assert len(nodes) == 1
    r = nodes[0]
    assert r.getTarget() is not None
    assert r.numConstraints() == 1
    assert r.getConstraint(0).numConstraints() == 2


def test_super_reference_is_distinguishable_from_a_plain_reference(parser):
    """`super.x` built an ExprRefPathContext, same as a plain `x`."""
    p = _parse_only(
        "package p { struct b { int x; }"
        " struct s : b { int x; constraint c { super.x == 1; x == 2; } } }",
        parser)
    supers = _find_nodes_deep(p, "ExprRefPathSuper")
    assert len(supers) == 1
    assert supers[0].getIs_super()
    # ExprRefPathSuper derives from ExprRefPathContext, so a consumer that does
    # not care about `super` keeps seeing what it saw.
    assert isinstance(supers[0], type(_find_nodes_deep(p, "ExprRefPathContext")[0]))


def test_string_type_range_keeps_its_values(parser):
    """`has_range` was set and `in_range` left empty: a range with no values."""
    p = _parse_only('package p { struct s { string in ["a","bc"] x; } }', parser)
    types = [t for t in _find_nodes_deep(p, "DataTypeString") if t.getHas_range()]
    assert len(types) == 1
    assert list(types[0].getIn_rangeList()) == ["a", "bc"]


# ---------------------------------------------------------------------------
# 12. override / export action / import class / symbol / static
#     (plan items 2.1, 2.4, 2.5, 1.6, 5.1)
# ---------------------------------------------------------------------------

OVERRIDE_SRC = """
component leaf { action A { } action B : A { } }
component pss_top {
    action A { }
    action B : A { }
    leaf sub;

    override {
        type A with B;
        instance sub.A with B;
    }
}
"""


def test_override_block_keeps_its_statements(parser):
    """`override { }` walked its children and discarded them."""
    p = _parse_only(OVERRIDE_SRC, parser)
    blocks = _find_nodes(p, "OverrideDecl")
    assert len(blocks) == 1
    kinds = [type(c).__name__ for c in blocks[0].getChildren()]
    assert kinds == ["TypeOverride", "InstanceOverride"]


def test_type_override_names_both_types(parser):
    p = _parse_only(OVERRIDE_SRC, parser)
    ovr = _find_nodes(p, "TypeOverride")[0]
    assert [e.getId().getId() for e in ovr.getTarget().getElems()] == ["A"]
    assert [e.getId().getId() for e in ovr.getWith_t().getElems()] == ["B"]


def test_instance_override_target_is_a_path(parser):
    """The instance form selects one site, so its target is a path.

    A type identifier would not do: `sub.A` is a field reached through a
    component instance, not a type name.
    """
    p = _parse_only(OVERRIDE_SRC, parser)
    ovr = _find_nodes(p, "InstanceOverride")[0]
    assert type(ovr.getTarget()).__name__ == "ExprHierarchicalId"
    assert [e.getId().getId() for e in ovr.getWith_t().getElems()] == ["B"]


def test_export_action_keeps_its_type_and_parameters(parser):
    p = _parse_only(
        "component c { action A { rand int x; }"
        " export A(int x); export target A(int x, int y); }",
        parser)
    exports = _find_nodes(p, "ExportAction")
    assert len(exports) == 2
    assert [e.getTarget().getElems()[0].getId().getId() for e in exports] == ["A", "A"]
    assert [e.numParameters() for e in exports] == [1, 2]
    # The platform qualifier is read, and defaults to none.
    assert str(exports[0].getPlat()) != str(exports[1].getPlat())


def test_import_class_keeps_its_prototypes_and_bases(parser):
    p = _parse_only(
        "package p { import class B { void g(); }"
        " import class C : B { void f(int x); int h(); } }",
        parser)
    classes = _find_nodes(p, "ImportClass")
    assert len(classes) == 2
    derived = [c for c in classes if c.getName().getId() == "C"][0]
    assert [type(k).__name__ for k in derived.getChildren()] == \
        ["FunctionPrototype", "FunctionPrototype"]
    assert [e.getId().getId() for e in derived.getSuper_t().getElems()] == ["B"]
    assert derived.numExtends() == 1


def test_import_class_is_a_type_in_its_package():
    """It declares a type, so it must be reachable by name after linking."""
    root = parse_pss(
        "package p { import class C { void f(); } }"
        " component pss_top { action A { } }")
    assert root is not None


SYMBOL_SRC = """
component pss_top {
    action A { }
    action top {
        symbol two(int n) {
            do A;
            do A;
        }
        activity {
            two(1);
        }
    }
}
"""


def test_symbol_declaration_keeps_its_body_and_parameters(parser):
    p = _parse_only(SYMBOL_SRC, parser)
    syms = _find_nodes(p, "SymbolDeclaration")
    assert len(syms) == 1
    s = syms[0]
    assert s.getName() == "two"
    assert s.numParams() == 1
    assert [type(c).__name__ for c in s.getChildren()] == \
        ["ActivityActionTypeTraversal", "ActivityActionTypeTraversal"]


def test_symbol_call_keeps_its_target_and_arguments(parser):
    p = _parse_only(SYMBOL_SRC, parser)
    calls = _find_nodes(p, "ActivitySymbolCall")
    assert len(calls) == 1
    assert calls[0].getTarget().getId() == "two"
    assert calls[0].numParams() == 1


def test_symbol_body_does_not_leak_into_the_action():
    """The symbol is a scope: its statements stay inside it.

    Without a symbol-tree visitor the generated one adds the declaration and
    then walks its children with the action's scope still pushed, so every
    statement in the symbol body reappears as a loose child of the action.
    """
    root = parse_pss(SYMBOL_SRC)

    def find(node, name):
        if getattr(node, "getName", None) and node.getName() == name:
            return node
        for c in (node.getChildren() if hasattr(node, "getChildren") else []):
            hit = find(c, name)
            if hit is not None:
                return hit
        return None

    top = find(root, "top")
    assert top is not None
    kinds = [type(c).__name__ for c in top.getChildren()]
    assert kinds == ["FieldCompRef", "SymbolDeclaration", "ActivityDecl"]


def test_static_qualifier_is_kept_on_both_function_forms(parser):
    """FunctionPrototype had no is_static, so a static function read as one."""
    p = _parse_only(
        "package p { static function void f(); function void g();"
        " import static function void h(); import function void i(); }",
        parser)
    protos = {pr.getName().getId(): pr
              for pr in _find_nodes_deep(p, "FunctionPrototype")}
    assert protos["f"].getIs_static()
    assert not protos["g"].getIs_static()
    assert protos["h"].getIs_static()
    assert not protos["i"].getIs_static()


# ---------------------------------------------------------------------------
# 13. Covergroups (plan Phase 4)
# ---------------------------------------------------------------------------
# The covergroup AST held a name, a target expression and a list of crossed
# names, and nothing else: every option, bin, guard and explicit sample type
# was reported as a gap and discarded, and a covergroup *type* -- as opposed to
# an inline instance -- built no node at all.

COVERGROUP_FULL_SRC = """
package p {
    covergroup cg_t(int a, int b) {
        option.weight = 2;
        cp_a : coverpoint a iff (b > 0) {
            option.at_least = 4;
            bins low = [0..3, 7];
            bins hi[4] = [8..] with (a % 2 == 0);
            bins mirror = cp_a with (a > 0);
            ignore_bins rest = default;
        }
        bit[4] cp_b : coverpoint b;
        ab : cross cp_a, cp_b iff (a > 0) {
            option.weight = 1;
            illegal_bins same = ab with (a == b);
        }
    }

    struct s {
        rand int x;
        rand int y;
        cg_t cg1(.a(x), .b(y));
        cg_t cg2(x, y) with { option.weight = 3; };
        covergroup { option.weight = 5; coverpoint x; xy : cross x, y; } cg3;
    }
}
"""


def _cg_type(parser):
    return _find_nodes(_parse_only(COVERGROUP_FULL_SRC, parser), "CovergroupType")[0]


def test_covergroup_type_declaration_builds_a_node(parser):
    cg = _cg_type(parser)
    assert cg.getName().getId() == "cg_t"
    # Ports are Fields in the covergroup's own scope, not a list beside it --
    # that is what lets a port's type resolve.
    assert [type(c).__name__ for c in cg.getChildren()] == ["Field", "Field"]
    assert [c.getName().getId() for c in cg.getChildren()] == ["a", "b"]
    assert cg.numCoverpoints() == 2
    assert cg.numCrosses() == 1


def test_covergroup_options_are_kept_in_all_three_positions(parser):
    """`option.x = y;` is legal in a covergroup, a coverpoint and a cross."""
    cg = _cg_type(parser)
    assert [(o.getName().getId()) for o in cg.getOptions()] == ["weight"]
    assert [(o.getName().getId()) for o in cg.getCoverpoint(0).getOptions()] == ["at_least"]
    assert [(o.getName().getId()) for o in cg.getCrosse(0).getOptions()] == ["weight"]
    assert cg.getOption(0).getValue() is not None


def test_coverpoint_keeps_its_type_and_guard(parser):
    cg = _cg_type(parser)
    cp_a, cp_b = cg.getCoverpoint(0), cg.getCoverpoint(1)
    assert cp_a.getIff() is not None
    assert cp_a.getData_type() is None
    assert cp_b.getIff() is None
    assert cp_b.getData_type() is not None


def test_coverpoint_bins_cover_all_three_right_hand_sides(parser):
    """`form` says which shape was written, so a null field is not ambiguous."""
    cg = _cg_type(parser)
    bins = list(cg.getCoverpoint(0).getBins())
    assert [b.getName().getId() for b in bins] == ["low", "hi", "mirror", "rest"]

    low, hi, mirror, rest = bins
    assert low.getForm() == ast.CoverpointBinsFormE.Ranges
    assert low.numRanges() == 2          # [0..3, 7]
    assert not low.getIs_array()

    assert hi.getIs_array()
    assert hi.getArray_size() is not None
    assert hi.getWith_expr() is not None
    # `[8..]` is a range with a low end and no high end.
    assert hi.getRange(0).getLhs() is not None
    assert hi.getRange(0).getRhs() is None

    assert mirror.getForm() == ast.CoverpointBinsFormE.Coverpoint
    assert mirror.getTarget().getId() == "cp_a"
    assert mirror.getWith_expr() is not None

    assert rest.getForm() == ast.CoverpointBinsFormE.Default
    assert rest.getKind() == ast.CovergroupBinsKindE.IgnoreBins
    assert rest.numRanges() == 0


def test_cross_keeps_its_guard_and_bins(parser):
    cg = _cg_type(parser)
    cross = cg.getCrosse(0)
    assert [n.getId() for n in cross.getCoverpoint_names()] == ["cp_a", "cp_b"]
    assert cross.getIff() is not None
    assert cross.numBins() == 1
    b = cross.getBin(0)
    assert b.getName().getId() == "same"
    assert b.getKind() == ast.CovergroupBinsKindE.IllegalBins
    assert b.getTarget().getId() == "ab"
    assert b.getWith_expr() is not None


def test_covergroup_instantiation_distinguishes_named_from_positional(parser):
    """The two ways of supplying actuals are alternatives, so exactly one list
    is populated for any one instantiation."""
    p = _parse_only(COVERGROUP_FULL_SRC, parser)
    insts = _find_nodes(p, "CovergroupInstantiation")
    assert [i.getName().getId() for i in insts] == ["cg1", "cg2"]

    named, positional = insts
    assert named.numPortmap() == 2
    assert named.numTargets() == 0
    assert [m.getName().getId() for m in named.getPortmapList()] == ["a", "b"]

    assert positional.numPortmap() == 0
    assert positional.numTargets() == 2
    assert positional.numOptions() == 1

    assert [e.getId().getId() for e in named.getType().getElems()] == ["cg_t"]


def test_inline_covergroup_keeps_its_options(parser):
    p = _parse_only(COVERGROUP_FULL_SRC, parser)
    inline = _find_nodes(p, "Covergroup")
    assert len(inline) == 1
    assert inline[0].getName().getId() == "cg3"
    assert [o.getName().getId() for o in inline[0].getOptions()] == ["weight"]
    assert inline[0].numCoverpoints() == 1
    assert inline[0].numCrosses() == 1


def test_covergroup_body_does_not_leak_into_the_enclosing_scope():
    """A covergroup body is not a scope, so nothing in it names anything.

    Without symbol-tree visitors the generated ones descend into the
    coverpoint, cross, option and port-map lists with the enclosing scope
    still current, so a struct with one covergroup linked to a struct holding
    the covergroup plus a loose copy of everything inside it.
    """
    root = parse_pss(COVERGROUP_FULL_SRC)

    def find(node, name):
        if getattr(node, "getName", None) and node.getName() == name:
            return node
        for c in (node.getChildren() if hasattr(node, "getChildren") else []):
            hit = find(c, name)
            if hit is not None:
                return hit
        return None

    st = find(root, "s")
    assert st is not None
    kinds = [type(c).__name__ for c in st.getChildren()]
    assert kinds == ["Field", "Field", "CovergroupInstantiation",
                     "CovergroupInstantiation", "Covergroup"]

    # The type is named, so `cg_t cg1(...)` can resolve it.
    assert find(root, "cg_t") is not None


def test_covergroup_port_type_resolves():
    """A port's type is a real type reference and must bind.

    Ports were first modelled as a list beside the covergroup. Nothing walks
    such a list with the covergroup's scope current, so `covergroup cg(Mode m)`
    linked with *type 'Mode' is never resolved*. They are Fields in the scope
    for that reason.
    """
    parse_pss(
        "component c { enum Mode { FAST, SLOW }"
        " covergroup CG(Mode m) { coverpoint m; } }")


def test_covergroup_is_not_reported_as_a_gap(parser):
    p = _parse_only(COVERGROUP_FULL_SRC, parser)
    unrepresented = [m for m in p.markers
                     if "not represented in the AST" in m["message"]]
    assert not unrepresented, \
        "\n".join(m["message"] for m in unrepresented)
