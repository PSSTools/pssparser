"""PSS116: constructs the grammar accepts but the AST does not represent.

This file is the ledger for docs/ast-coverage-plan.md. Every construct the
builder discards -- or represents only partially -- must say so, so that
"parsed clean" means "fully represented" rather than "silently incomplete".

The survey that motivated this (docs/ast-coverage-gaps.md) found that all 15
constructs it probed produced an *empty* marker list: source using them parsed
"successfully" and the consumer received a model missing behaviour.

**When a construct is implemented, delete its case here** and add the positive
probe to ``test_ast_node_probes.py`` in the same commit. A case disappearing
from this file is the measure of progress through the plan; a case that stays
while the probe passes means the diagnostic was left behind.

For partial representation the message carries a ``: <detail>`` suffix naming
the part that is dropped -- a construct is never allowed to return to silence
just because *some* of it is now built.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import find_markers, parse_collect  # noqa: E402


# (id, source, expected substring of the PSS116 message)
#
# The substring is the construct name as the builder spells it, plus enough of
# the detail to distinguish partials that share a construct name.
UNREPRESENTED = [
    # -- Phase 5: qualifiers lost on nodes that are built --------------------
    # The single-target form is fully represented; only the list is not.
    # ProceduralStmtRandomize has one `target` expression and the grammar takes
    # a comma-separated list -- see open question O-4.
    ("randomize_multi_target",
     "package p { struct s { rand int x; } }"
     " component c { function void f() { p::s v; p::s w;"
     " randomize v, w with { v.x < 4; } } }",
     "only the first of several randomization targets is kept"),
]

_IDS = [c[0] for c in UNREPRESENTED]


@pytest.mark.parametrize("name,src,expected", UNREPRESENTED, ids=_IDS)
def test_unrepresented_construct_is_reported(name, src, expected):
    """The construct parses, and says out loud that it is not in the AST."""
    _, markers = parse_collect(src)

    errors = find_markers(markers, severity="error")
    assert not errors, \
        "expected a clean parse, got errors:\n%s" % "\n".join(
            m["message"] for m in errors)

    pss116 = find_markers(markers, marker_id="PSS116")
    assert pss116, "no PSS116 emitted; the gap is silent again"

    matching = [m for m in pss116 if expected in m["message"]]
    assert matching, \
        "no PSS116 mentioning %r; got:\n%s" % (
            expected, "\n".join(m["message"] for m in pss116))


# Constructs that *were* on the ledger above and have since been implemented.
# Each must now parse with no PSS116 at all -- the other half of the "no silent
# partials" rule: a construct never returns to silence, and once it is
# represented it must stop claiming to be a gap.
CLOSED_CASES = [
    # -- Phase 2 -------------------------------------------------------------
    ("attr_group",
     "package p { struct s { private: int x; } }"),
    ("default_constraint",
     "package p { struct s { rand int x; constraint c { default x == 3; } } }"),
    ("default_disable_constraint",
     "package p { struct s { rand int x; constraint c { default disable x; } } }"),
    ("import_function_two_step",
     "package p { function void f(); import function p::f; }"),
    # -- Phase 5 -------------------------------------------------------------
    ("import_function_language",
     "package p { import C function void g(); }"),
    # The marker here fired on *every* object bind, including the wildcard form
    # that was already fully represented -- so all 10 corpus hits were false
    # gaps. Both the plain and the indexed forms must now be clean.
    ("bind_plain",
     "buffer Buf { int x; } component pss_top { pool Buf p;"
     " bind p { producer.out }; action producer { output Buf out; } }"),
    ("bind_wildcard",
     "buffer Buf { int x; } component pss_top { pool Buf p; bind p *; }"),
    ("bind_component_path_index",
     "buffer Buf { int x; }"
     " component leaf { action prod { output Buf out; } }"
     " component pss_top { leaf sub[4]; pool Buf p;"
     " bind p { sub[0..3].prod.out }; }"),
    # -- Phase 3 -------------------------------------------------------------
    # Six markers covered the monitor activity: the declaration, `sequence`,
    # `concat`, `overlap`, `schedule`, `select`, `eventually`, the monitor
    # traversal, and both constraint forms. One source must silence all of them
    # -- a partial fix here would leave `concat`'s marker firing while
    # `sequence`'s went quiet.
    ("monitor_activity_all_forms",
     "component c { action A { rand int v; } monitor M1 { }"
     " monitor M { A a; M1 h; constraint cb { a.v < 9; }"
     " activity { lbl: sequence { a; } concat { a; } overlap { a; }"
     " schedule { a; } select { a; a; } eventually a; h; do M1;"
     " constraint { a.v < 4; } a; } } }"),
    # One marker covered both cover forms, so one source must silence both --
    # and the labeled spellings too, since the label is what the reference form
    # and the inline form have in common.
    ("cover_stmt_all_forms",
     "component c { action A { rand int v; } monitor M { A a; activity { a; } }"
     " cover M; ref_lbl: cover M;"
     " cover { A a; constraint { a.v < 4; } activity { a; } }"
     " inline_lbl: cover { A a; activity { a; } } }"),
    # -- Phase 1 -------------------------------------------------------------
    ("activity_constraint",
     "component c { action a { rand int x; activity { constraint { x < 10; }"
     " constraint x > 1; } } }"),
    # -- Phase 5 -------------------------------------------------------------
    # One target and a `with` block: the form that carried both markers.
    ("randomize_single_target",
     "package p { struct s { rand int x; } }"
     " component c { function void f() { p::s v; randomize v with { v.x < 4; } } }"),
    ("super_ref_path",
     "package p { struct b { int x; } struct s : b { constraint c { super.x == 1; } } }"),
    ("string_type_range",
     'package p { struct s { string in ["a","b"] x; } }'),
    ("function_static",
     "package p { static function void f();"
     " import static function void g(); }"),
    # -- Phase 2 -------------------------------------------------------------
    ("export_action",
     "component c { action A { rand int x; } export A(int x);"
     " export target A(int x); }"),
    ("import_class",
     "package p { import class B { void g(); }"
     " import class C : B { void f(int x); } }"),
    # One marker covered the whole block, so one source must silence it for
    # both statement forms.
    ("override_both_forms",
     "component leaf { action A { } action B : A { } }"
     " component c { action A {} action B : A {} leaf sub;"
     " override { type A with B; instance sub.A with B; } }"),
    # -- Phase 1 -------------------------------------------------------------
    # `symbol` and `symbol call` were two markers on one construct: declaring a
    # symbol without calling it, or the reverse, is not a use of the feature.
    ("symbol_declaration_and_call",
     "component c { action A {} action a { symbol s(int n) { do A; }"
     " activity { s(1); } } }"),
    # -- Phase 4 -------------------------------------------------------------
    # Seven markers covered the covergroup subsystem: the type declaration, the
    # type instantiation, options in all three positions, and a coverpoint's
    # data type, `iff` guard and bins. One source must silence all of them.
    ("covergroup_all_forms",
     "package p {"
     " covergroup cg_t(int a, int b) {"
     "   option.weight = 2;"
     "   cp_a : coverpoint a iff (b > 0) {"
     "     option.at_least = 4;"
     "     bins low = [0..3, 7];"
     "     bins hi[4] = [8..] with (a % 2 == 0);"
     "     bins mirror = cp_a with (a > 0);"
     "     ignore_bins rest = default;"
     "   }"
     "   bit[4] cp_b : coverpoint b;"
     "   ab : cross cp_a, cp_b iff (a > 0) {"
     "     option.weight = 1;"
     "     illegal_bins same = ab with (a == b);"
     "   }"
     " }"
     " struct s { rand int x; rand int y;"
     "   cg_t cg1(.a(x), .b(y));"
     "   cg_t cg2(x, y) with { option.weight = 3; };"
     "   covergroup { option.weight = 5; coverpoint x; } cg3;"
     " } }"),
]


@pytest.mark.parametrize(
    "case_id,source", CLOSED_CASES, ids=[c[0] for c in CLOSED_CASES])
def test_closed_construct_is_clean(case_id, source):
    _, markers = parse_collect(source)
    assert not find_markers(markers, marker_id="PSS116"), \
        "%s is implemented but still reports a gap:\n%s" % (
            case_id, "\n".join(m["message"] for m in markers))


def test_a_fully_represented_construct_is_clean():
    """PSS116 must not fire on source the builder does represent."""
    src = """
        component c {
            action A { int x; }
            action a {
                activity {
                    replicate (i: 4) { do A; }
                    parallel join_none { do A; }
                }
            }
        }
    """
    _, markers = parse_collect(src)
    assert not find_markers(markers, marker_id="PSS116"), \
        "PSS116 on a represented construct:\n" + "\n".join(
            m["message"] for m in markers)


def test_the_standard_library_does_not_report_gaps():
    """
    The stdlib itself uses unrepresented constructs (`default` constraints in
    addr_reg_pkg). Those are real gaps, but they are not the user's source and
    the user cannot act on them, so the loader suppresses PSS116 -- otherwise
    every parse of every file would carry the same warnings.
    """
    _, markers = parse_collect("component c { action A { int x; } }")
    assert not find_markers(markers, marker_id="PSS116"), \
        "stdlib PSS116 leaked into a user parse:\n" + "\n".join(
            m["message"] for m in markers)
