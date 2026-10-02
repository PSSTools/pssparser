"""
Regression tests for the activity-construction gaps catalogued in
``sphinx-pss/design/pssparser-activity-gaps.md`` (A1-A6), tracked by
``parser_refactor/ACTIVITY_GAPS_PLAN.md``.

Every assertion here describes the *correct* behavior. Gaps that are still open
are marked xfail(strict=True); the marker is removed as each fix lands, so an
accidental fix fails loudly rather than passing silently.

The defects share a shape -- the parser accepts the syntax and then builds
nothing, or something plausible-but-wrong, with no diagnostic. So the tests that
matter most are the negative ones: a `replicate` that comes back as a bare
`ActivitySequence` is indistinguishable from a correctly-built one unless you
assert on the type.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import parse_pss, get_symbol
from activity_walk import activity_nodes


# ---------------------------------------------------------------------------
# Open-gap markers. Delete the decorator (not the test) as each fix lands;
# strict=True means a fix that arrives without the marker being removed fails
# the suite rather than passing quietly.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# The probe fixture: one activity exercising every construct in the gaps doc.
# Individual tests use narrower sources; this one exists so the cross-cutting
# tests (A5 locations) have a single dense specimen to sweep.
# ---------------------------------------------------------------------------

PROBE_PSS = """
component C {
    action A { rand int x; }
    action B { rand int y; }

    action Top {
        A a1, a2;
        B b1;
        rand int c;
        rand int arr[4];

        activity {
            lbl_seq: sequence { a1; b1; }
            if (c > 1) { a1; } else { b1; }
            parallel join_none { a1; b1; }
            parallel join_first (1) { a1; b1; }
            parallel join_branch (a1, b1) { a1; b1; }
            schedule {
                s1: a1;
                s2: b1;
                constraint parallel { s1, s2 };
            }
            select { (c > 2) [3]: a1; b1; }
            match (c) { [0..3]: a1; default: b1; }
            repeat (c) { a1; }
            repeat { a1; } while (c > 0);
            foreach (i : arr) { a1; }
            replicate (r: 4) { a1; }
            atomic { a1; b1; }
            do A with { x == 1; };
            bind a1.x a2.x;
        }
    }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _children(node):
    """Children of `node`, or [] for leaf statements (which have no accessor)."""
    if not hasattr(node, "getChildren"):
        return []
    return [node.getChild(i) for i in range(len(node.getChildren()))]


def _tname(node):
    return type(node).__name__ if node is not None else None


# The linked root owns the AST; child wrappers hold borrowed pointers and do
# not keep it alive. A helper that returns a node while letting its root fall
# out of scope hands back a dangling pointer, and touching it segfaults. Pin
# every root for the life of the module.
_ROOTS = []


def _parse(src):
    root = parse_pss(src)
    _ROOTS.append(root)
    return root


def activity_of(src, component="C", action="Top"):
    """Parse `src` and return the ActivityDecl of `component::action`."""
    root = _parse(src)
    comp = get_symbol(root, component)
    assert comp is not None, f"component {component} not found"
    act_sym = get_symbol(comp, action)
    assert act_sym is not None, f"action {action} not found"
    decls = [c for c in _children(act_sym.getTarget())
             if _tname(c) == "ActivityDecl"]
    assert len(decls) == 1, f"expected exactly one ActivityDecl, got {len(decls)}"
    return decls[0]


def activity_stmts(src, **kw):
    return _children(activity_of(src, **kw))


def one_stmt(src, **kw):
    """The single activity statement in `src`."""
    stmts = activity_stmts(src, **kw)
    assert len(stmts) == 1, \
        f"expected one activity statement, got {[_tname(s) for s in stmts]}"
    return stmts[0]


def wrap(body, fields="A a1, a2; B b1; rand int c; rand int arr[4];"):
    """Wrap activity-statement text in the standard two-action component."""
    return """
component C {
    action A { rand int x; }
    action B { rand int y; }
    action Top {
        %s
        activity {
            %s
        }
    }
}
""" % (fields, body)


def ref_name(refpath):
    """Flatten an ExprRefPathContext to a dotted name."""
    elems = refpath.getHier_id().getElems()
    return ".".join(str(refpath.getHier_id().getElem(i).getId().getId())
                    for i in range(len(elems)))


def hier_name(hier_id):
    """Flatten an ExprHierarchicalId, or the path of a reference, to a dotted name."""
    if hasattr(hier_id, "getHier_id"):
        hier_id = hier_id.getHier_id()
    return ".".join(str(hier_id.getElem(i).getId().getId())
                    for i in range(len(hier_id.getElems())))


# ---------------------------------------------------------------------------
# A1 -- if/else branches silently discarded
# ---------------------------------------------------------------------------

def test_a1_if_branch_is_retained():
    ife = one_stmt(wrap("if (c > 1) { a1; } else { b1; }"))
    assert _tname(ife) == "ActivityIfElse"
    assert ife.getTrue_s() is not None, \
        "if-branch was discarded (A1)"


def test_a1_else_branch_is_retained():
    ife = one_stmt(wrap("if (c > 1) { a1; } else { b1; }"))
    assert ife.getFalse_s() is not None, \
        "else-branch was discarded (A1)"


def test_a1_absent_else_is_none():
    """An if with no else must yield None -- distinct from a discarded else."""
    ife = one_stmt(wrap("if (c > 1) { a1; }"))
    assert ife.getTrue_s() is not None
    assert ife.getFalse_s() is None


def test_a1_single_statement_branches_are_retained():
    """The unbraced form takes a different path through mkActivityStmt."""
    ife = one_stmt(wrap("if (c > 1) a1; else b1;"))
    assert ife.getTrue_s() is not None
    assert ife.getFalse_s() is not None


def test_a1_branch_bodies_carry_their_statements():
    ife = one_stmt(wrap("if (c > 1) { a1; b1; } else { b1; }"))
    true_s = ife.getTrue_s()
    assert _tname(true_s) == "ActivitySequence"
    assert len(true_s.getChildren()) == 2, \
        "if-branch block lost its statements"


# ---------------------------------------------------------------------------
# A2 -- join specifications never constructed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("keyword", ["parallel", "schedule"])
@pytest.mark.parametrize("spec,expected", [
    ("join_none",             "ActivityJoinSpecNone"),
    ("join_first (1)",        "ActivityJoinSpecFirst"),
    ("join_select (2)",       "ActivityJoinSpecSelect"),
    ("join_branch (s1, s2)",  "ActivityJoinSpecBranch"),
])
def test_a2_join_spec_is_constructed(keyword, spec, expected):
    stmt = one_stmt(wrap("%s %s { s1: a1; s2: b1; }" % (keyword, spec)))
    js = stmt.getJoin_spec()
    assert js is not None, f"{keyword} {spec}: join spec was dropped (A2)"
    assert _tname(js) == expected


@pytest.mark.parametrize("keyword", ["parallel", "schedule"])
def test_a2_absent_join_spec_stays_none(keyword):
    """
    "default join-all" and "not implemented" are currently indistinguishable.
    Once A2 lands they must stay distinguishable in the other direction: a
    block with no spec keeps a None join_spec rather than gaining a synthetic
    one.
    """
    stmt = one_stmt(wrap("%s { a1; b1; }" % keyword))
    assert stmt.getJoin_spec() is None


def test_a2_join_first_count_expression_is_captured():
    stmt = one_stmt(wrap("parallel join_first (2) { a1; b1; }"))
    js = stmt.getJoin_spec()
    assert js is not None
    assert js.getCount() is not None, "join_first count expression was dropped"


def test_a2_join_select_count_expression_is_captured():
    stmt = one_stmt(wrap("parallel join_select (2) { a1; b1; }"))
    js = stmt.getJoin_spec()
    assert js is not None
    assert js.getCount() is not None, "join_select count expression was dropped"


def test_a2_join_branch_labels_are_captured_in_order():
    stmt = one_stmt(wrap("parallel join_branch (s1, s2) { s1: a1; s2: b1; }"))
    js = stmt.getJoin_spec()
    assert js is not None
    branches = js.getBranches()
    assert len(branches) == 2, "join_branch label list truncated"
    names = [ref_name(js.getBranche(i)) for i in range(len(branches))]
    assert names == ["s1", "s2"]


def test_a2_join_spec_does_not_consume_the_block_body():
    """Regression guard: building the spec must not disturb the statements."""
    stmt = one_stmt(wrap("parallel join_none { a1; b1; }"))
    assert len(stmt.getChildren()) == 2


# ---------------------------------------------------------------------------
# A3 -- replicate produces a bare ActivitySequence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body", [
    "replicate (4) { a1; }",
    "replicate (i: 4) { a1; }",
    "replicate (i: 4) lbl[]: { a1; }",
])
def test_a3_replicate_is_not_a_bare_sequence(body):
    """
    The defining symptom of A3: with no visitor, the default visitChildren
    walks through to the body and hands back its ActivitySequence, which is
    structurally valid and therefore silent.
    """
    stmt = one_stmt(wrap(body))
    assert _tname(stmt) == "ActivityReplicate", \
        f"{body!r} built a {_tname(stmt)} instead of an ActivityReplicate (A3)"


def test_a3_replicate_count_is_captured():
    stmt = one_stmt(wrap("replicate (4) { a1; }"))
    assert stmt.getCount() is not None, "replicate count expression was dropped"


def test_a3_replicate_without_index_has_no_idx_id():
    stmt = one_stmt(wrap("replicate (4) { a1; }"))
    assert stmt.getIdx_id() is None
    assert stmt.getCount() is not None


def test_a3_replicate_index_identifier_is_captured():
    stmt = one_stmt(wrap("replicate (i: 4) { a1; }"))
    assert stmt.getIdx_id() is not None
    assert str(stmt.getIdx_id().getId()) == "i"


def test_a3_replicate_label_array_is_captured():
    stmt = one_stmt(wrap("replicate (i: 4) lbl[]: { a1; }"))
    assert stmt.getIt_label() is not None
    assert str(stmt.getIt_label().getId()) == "lbl"


def test_a3_replicate_body_is_retained():
    stmt = one_stmt(wrap("replicate (4) { a1; b1; }"))
    body = stmt.getBody()
    assert body is not None, "replicate body was dropped"
    assert len(body.getChildren()) == 2


# ---------------------------------------------------------------------------
# A4 -- scheduling constraints dropped
# ---------------------------------------------------------------------------

def _scheduling_constraints(node):
    return [c for c in _children(node)
            if _tname(c) == "ActivitySchedulingConstraint"]


@pytest.mark.parametrize("keyword,is_parallel", [
    ("parallel", True),
    ("sequence", False),
])
def test_a4_scheduling_constraint_in_activity_scope(keyword, is_parallel):
    act = activity_of(wrap(
        "schedule { s1: a1; s2: b1; constraint %s { s1, s2 }; }" % keyword))
    sched = _children(act)[0]
    assert _tname(sched) == "ActivitySchedule"
    scs = _scheduling_constraints(sched)
    assert len(scs) == 1, \
        f"constraint {keyword} was dropped from the schedule block (A4)"
    assert scs[0].getIs_parallel() is is_parallel


@pytest.mark.parametrize("keyword,is_parallel", [
    ("parallel", True),
    ("sequence", False),
])
def test_a4_scheduling_constraint_in_action_scope(keyword, is_parallel):
    """
    activity_scheduling_constraint is reachable from action_body_item as well
    as activity_stmt. A visitor correct in one context and silently dropping in
    the other just reproduces the original defect.
    """
    src = """
component C {
    action A { rand int x; }
    action B { rand int y; }
    action Top {
        A a1; B b1;
        activity { s1: a1; s2: b1; }
        constraint %s { s1, s2 };
    }
}
""" % keyword
    root = _parse(src)
    comp = get_symbol(root, "C")
    action = get_symbol(comp, "Top").getTarget()
    scs = _scheduling_constraints(action)
    assert len(scs) == 1, \
        f"action-scope constraint {keyword} was dropped (A4)"
    assert scs[0].getIs_parallel() is is_parallel


def test_a4_scheduling_constraint_targets_are_captured_in_order():
    act = activity_of(wrap(
        "schedule { s1: a1; s2: b1; s3: a2; "
        "constraint parallel { s1, s2, s3 }; }"))
    sched = _children(act)[0]
    sc = _scheduling_constraints(sched)[0]
    targets = sc.getTargets()
    assert len(targets) == 3, "scheduling-constraint target list truncated"
    names = [hier_name(sc.getTarget(i)) for i in range(len(targets))]
    assert names == ["s1", "s2", "s3"]


def test_a4_scheduling_constraint_does_not_displace_siblings():
    act = activity_of(wrap(
        "schedule { s1: a1; s2: b1; constraint parallel { s1, s2 }; }"))
    sched = _children(act)[0]
    kinds = [_tname(c) for c in _children(sched)]
    assert kinds.count("ActivityActionHandleTraversal") == 2, \
        f"schedule block lost its traversals: {kinds}"


# ---------------------------------------------------------------------------
# A7 -- labels on activity *blocks* were never registered as symbols
#
# Found while fixing A2. registerActivityLabels only handled
# IActivityLabeledStmt; a labeled block (sequence/parallel/schedule) is an
# IActivityLabeledScope, the other branch of the hierarchy split that also
# caused A1, so its label was never registered. Invisible until A2 landed,
# because nothing referenced these labels before.
# ---------------------------------------------------------------------------

def _links(src):
    """Parse and link, returning the error message or None on success."""
    from pssparser import Parser
    p = Parser()
    p.parses([("t.pss", src)])
    try:
        root = p.link()
        _ROOTS.append(root)
        return None
    except Exception as e:
        return str(e)


def test_a7_join_branch_naming_a_block_branch_resolves():
    """
    The LRM case: "the label_identifier ... shall be the label of a top-level
    branch within the parallel or schedule block" (10.5.2). A top-level branch
    may itself be a block.
    """
    err = _links(wrap(
        "L1: parallel join_branch(L2) { "
        "  L2: parallel { L3: a1; L4: b1; } "
        "  L5: a2; "
        "}"))
    assert err is None, f"block label L2 did not resolve: {err}"


def test_a7_join_branch_naming_leaf_branches_resolves():
    err = _links(wrap("L1: parallel join_branch(L2, L3) { L2: a1; L3: b1; }"))
    assert err is None, f"leaf labels did not resolve: {err}"


@pytest.mark.parametrize("keyword", ["sequence", "parallel", "schedule"])
def test_a7_every_labeled_block_kind_registers_its_label(keyword):
    err = _links(wrap(
        "L1: parallel join_branch(L2) { L2: %s { a1; b1; } L5: a2; }" % keyword))
    assert err is None, f"{keyword} block label did not resolve: {err}"


def test_a7_unknown_join_branch_label_is_still_an_error():
    """
    The complement: registering block labels must not turn label resolution
    into a rubber stamp. A label that names nothing must still be diagnosed.
    """
    err = _links(wrap("L1: parallel join_branch(nope) { L2: a1; L3: b1; }"))
    assert err is not None and "nope" in err, \
        f"undefined join_branch label was accepted silently: {err!r}"


# ---------------------------------------------------------------------------
# A8 -- loop index variables are scoped to their loop
#
# Fixed by symbol-resolution plan WS4.1: each loop statement is a scope that
# owns its index and iterator, so sibling loops no longer collide. The index
# used to be injected into the body block and registered in the enclosing
# activity, where the second loop's copy was a duplicate of the first.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("first,second", [
    ("foreach (i : arr) { a1; }",   "foreach (i : arr) { b1; }"),
    ("foreach (i : arr) { a1; }",   "replicate (i: 4) { b1; }"),
    ("repeat (i : 4) { a1; }",      "replicate (i: 4) { b1; }"),
])
def test_a8_sibling_loops_may_share_an_index_name(first, second):
    """
    Each loop is its own scope, so reusing an index name in a sibling loop is
    legal.
    """
    err = _links(wrap("%s\n%s" % (first, second)))
    assert err is None, f"sibling loops could not share an index name: {err}"


def test_a8_distinct_index_names_are_unaffected():
    """The workaround, pinned so the probe fixture's use of it stays honest."""
    err = _links(wrap("foreach (i : arr) { a1; }\nreplicate (r: 4) { b1; }"))
    assert err is None, err


# ---------------------------------------------------------------------------
# A6 -- super; produces nothing
# ---------------------------------------------------------------------------

SUPER_PSS = """
component C {
    action A { rand int x; }
    action Base {
        A a1;
        activity { a1; }
    }
    action Top : Base {
        A a2;
        activity {
            a2;
            super;
            a2;
        }
    }
}
"""


def test_a6_super_statement_is_constructed():
    """
    Unlike A3/A4 the rule has no children, so the default visitChildren
    produces *nothing* rather than something plausible-but-wrong.
    """
    stmts = activity_stmts(SUPER_PSS, action="Top")
    kinds = [_tname(s) for s in stmts]
    assert "ActivitySuper" in kinds, f"super; produced no node (A6): {kinds}"


def test_a6_super_keeps_its_position_among_siblings():
    stmts = activity_stmts(SUPER_PSS, action="Top")
    kinds = [_tname(s) for s in stmts]
    assert kinds == [
        "ActivityActionHandleTraversal",
        "ActivitySuper",
        "ActivityActionHandleTraversal",
    ], kinds


# ---------------------------------------------------------------------------
# A5 -- activity statements carry no source location
# ---------------------------------------------------------------------------

def test_a5_every_activity_statement_has_a_location():
    """
    A blanket sweep rather than a per-type list, so it does not rot as
    statement types are added. lineno < 0 is what sphinx-pss reads as
    "compiler-injected, do not document".
    """
    act = activity_of(PROBE_PSS)
    missing = []
    for stmt in _children(act):
        loc = stmt.getLocation()
        if loc is None or loc.lineno <= 0:
            missing.append(_tname(stmt))
    assert not missing, f"activity statements with no location (A5): {missing}"


def test_a5_locations_are_monotonic_across_the_probe():
    """
    Each statement in the probe is on its own line and they are in source
    order, so the line numbers must be strictly increasing. Catches a location
    that is merely present but copied from the wrong token.
    """
    act = activity_of(PROBE_PSS)
    lines = [s.getLocation().lineno for s in _children(act)]
    assert lines == sorted(lines) and len(set(lines)) == len(lines), lines


# A multi-line twin of PROBE_PSS. A one-line statement cannot tell a missing
# end line from a correct one, which is how R1 and R2 (sphinx-pss
# 2026-09-28) went unnoticed: `atomic` and `bind` had no end location.
MULTILINE_PSS = """
component C {
    action A { rand int x; }
    action B { rand int y; }

    action Top {
        A a1, a2;
        B b1;
        rand int c;
        rand int arr[4];

        activity {
            lbl_seq: sequence {
                a1;
                b1;
            }
            if (c > 1) {
                a1;
            } else {
                b1;
            }
            parallel {
                a1;
                b1;
            }
            schedule {
                a1;
                b1;
            }
            select {
                (c > 2) [3]: a1;
                b1;
            }
            match (c) {
                [0..3]: a1;
                default: b1;
            }
            repeat (c) {
                a1;
            }
            foreach (i : arr) {
                a1;
            }
            atomic {
                a1;
                b1;
            }
            bind a1.x
                a2.x;
            L: atomic {
                a1;
            }
        }
    }
}
"""

#: (statement type, start line, end line) in MULTILINE_PSS, for the two
#: statements R1 and R2 fixed, and the atomic's body.
_ATOMIC_LINE, _ATOMIC_END = 44, 47
_BIND_LINE, _BIND_END = 48, 49


@pytest.mark.parametrize("src", [PROBE_PSS, MULTILINE_PSS], ids=["probe", "multiline"])
def test_a5_nested_statements_have_locations(src):
    """Follows body accessors too: `atomic`'s body is reached only through
    `getBody()`, and had no location at all (R1)."""
    act = activity_of(src)
    missing = [_tname(n) for n in activity_nodes(act)
               if n.getLocation() is None or n.getLocation().lineno <= 0]
    assert not missing, f"nested statements with no location (A5): {missing}"


def test_a5_nested_blocks_have_an_end_location():
    act = activity_of(MULTILINE_PSS)
    nodes = activity_nodes(act)
    assert nodes
    bad = [(_tname(n), n.getLocation().lineno,
            n.getEndLocation().lineno if n.getEndLocation() else None)
           for n in nodes
           if _tname(n) != "ActivityActionHandleTraversal"
           and (n.getEndLocation() is None
                or n.getEndLocation().lineno < n.getLocation().lineno)]
    assert not bad, f"statements with no or backwards end location: {bad}"


def test_r1_atomic_and_its_body_are_located():
    stmts = _children(activity_of(MULTILINE_PSS))
    atomic = [s for s in stmts if _tname(s) == "ActivityAtomicBlock"][0]
    assert atomic.getLocation().lineno == _ATOMIC_LINE
    assert atomic.getEndLocation().lineno == _ATOMIC_END
    body = atomic.getBody()
    assert (body.getLocation().lineno, body.getLocation().linepos) == (_ATOMIC_LINE, 20)
    assert body.getEndLocation().lineno == _ATOMIC_END


def test_r2_bind_has_an_end_location():
    stmts = _children(activity_of(MULTILINE_PSS))
    bind = [s for s in stmts if _tname(s) == "ActivityBindStmt"][0]
    assert bind.getLocation().lineno == _BIND_LINE
    assert bind.getEndLocation().lineno == _BIND_END


def test_r1_a_labeled_atomic_keeps_its_label():
    """The body's location must not swallow the label, which the atomic
    claims before building its body (F8(1))."""
    stmts = _children(activity_of(MULTILINE_PSS))
    atomic = [s for s in stmts if _tname(s) == "ActivityAtomicBlock"][-1]
    assert atomic.getLabel() is not None and atomic.getLabel().getId() == "L"
    assert atomic.getBody().getLocation().linepos > atomic.getLocation().linepos


def test_a5_source_slices_start_and_end_on_the_right_tokens():
    """What sphinx-pss does with a location: slice the source between the
    start and end. A location copied from the wrong token shows up here even
    when it is present."""
    lines = MULTILINE_PSS.split("\n")

    def text(loc, end):
        # Lines are 1-based and MULTILINE_PSS starts with a newline, so
        # line n is lines[n-1]. Columns are 1-based; end is one past.
        if loc.lineno == end.lineno:
            return lines[loc.lineno - 1][loc.linepos - 1:end.linepos - 1]
        first = lines[loc.lineno - 1][loc.linepos - 1:]
        last = lines[end.lineno - 1][:end.linepos - 1]
        return first + "\n".join([""] + lines[loc.lineno:end.lineno - 1] + [last])

    for s in _children(activity_of(MULTILINE_PSS)):
        if _tname(s) not in ("ActivityAtomicBlock", "ActivityBindStmt"):
            continue
        t = text(s.getLocation(), s.getEndLocation()).strip()
        kw = "bind" if _tname(s) == "ActivityBindStmt" else "atomic"
        assert t.startswith(kw), t
        assert t.endswith("}" if kw == "atomic" else ";"), t


def test_a5_block_statements_have_an_end_location():
    """
    endLocation is what lets a consumer slice the source text of a nested
    block. Only meaningful for the brace-delimited forms.
    """
    act = activity_of(PROBE_PSS)
    blocks = [c for c in _children(act) if _tname(c) in (
        "ActivitySequence", "ActivityParallel", "ActivitySchedule",
        "ActivitySelect", "ActivityMatch", "ActivityRepeatCount",
        "ActivityForeach", "ActivityIfElse", "ActivityAtomicBlock",
        "ActivityBindStmt")]
    assert blocks, "probe built no block statements"
    missing = [_tname(b) for b in blocks
               if b.getEndLocation() is None or b.getEndLocation().lineno <= 0]
    assert not missing, f"block statements with no end location (A5): {missing}"
