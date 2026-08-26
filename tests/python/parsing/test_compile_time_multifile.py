"""Compile-time elaboration across source units.

Every pre-existing compile-time test in this suite passes a *single* PSS string,
which is why a defect that made ``compile if``/``compile assert``/``compile has``
file-local survived: a condition reading a ``static const`` from another file
failed to resolve, ``evalConstantExpression`` returned false, and every caller
read that as "the condition is false".  The branch was dropped, the parse
reported 0 errors, and the missing declarations only surfaced downstream.

The semantics being pinned here are PSS 3.1 (Draft 19) clause 19:

* 19.1.2 -- compile-time expressions (``static const`` initializers and
  ``compile if`` conditions) are evaluated against types and constants declared
  unconditionally, or in an enabled ``compile if`` branch, either **in a
  previously-processed source unit** or earlier in the current one.
* 19.1.3 -- the value "must be determinable at compile time".  An
  indeterminable condition is an error here, not a silent false.
* 19.3 -- ``compile has`` is true iff the type or constant "has been previously
  declared", so it is deliberately *order-sensitive* (Example 275 depends on a
  later declaration reading as absent) and never an error.
* 19.4 -- a failing ``compile assert`` is reported.

Compile-time elaboration is therefore order-**dependent**, unlike ordinary
linking (see ``linking/test_file_order_independence.py``).  A forward reference
to a constant in a not-yet-processed unit is not supported, and the tests in
group D require it to be loud.
"""
import pytest

from pssparser import Parser, ParseException
from ..test_helpers import get_symbol


CFG_TRUE = "package cfg_pkg { static const bool FLAG = true; }"
CFG_FALSE = "package cfg_pkg { static const bool FLAG = false; }"


def link_files(files):
    """Parse and link *files* in order, returning the linked symbol root."""
    parser = Parser()
    parser.parses(files)
    return parser.link()


def expect_error(files, substr):
    """Require an error containing *substr*, from either parse or link.

    Compile-time markers are produced while the AST is built, so they surface
    from ``parses()``; unresolved references surface from ``link()``.  A test
    that guards only one of the two silently passes when the other fires.
    """
    parser = Parser()
    try:
        parser.parses(files)
        parser.link()
    except ParseException as e:
        assert substr in str(e), f"expected {substr!r} in error, got: {e}"
        return e
    pytest.fail(f"expected an error containing {substr!r}, but the model was clean")


def sym(root, path):
    """Look up a dotted path of names, returning None if any step is missing."""
    node = root
    for elem in path.split("."):
        node = get_symbol(node, elem)
        if node is None:
            return None
    return node


# ===========================================================================
# A. static const declared in a previously-processed source unit
# ===========================================================================

GATED_EXTEND = """
import cfg_pkg::*;
extend component C {
    compile if (cfg_pkg::FLAG) {
        target function int gated() { return 1; }
    } else {
        target function int not_gated() { return 0; }
    }
}
"""


def test_qualified_const_from_earlier_unit_selects_true_branch():
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("comp.pss", "component C { }"),
        ("ext.pss", GATED_EXTEND),
    ])
    assert sym(root, "C.gated") is not None
    assert sym(root, "C.not_gated") is None


def test_qualified_const_from_earlier_unit_selects_false_branch():
    root = link_files([
        ("cfg.pss", CFG_FALSE),
        ("comp.pss", "component C { }"),
        ("ext.pss", GATED_EXTEND),
    ])
    assert sym(root, "C.gated") is None
    assert sym(root, "C.not_gated") is not None


def test_wildcard_import_of_earlier_unit_const():
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("comp.pss", "component C { }"),
        ("ext.pss", """
import cfg_pkg::*;
extend component C {
    compile if (FLAG) {
        target function int gated() { return 1; }
    }
}
"""),
    ])
    assert sym(root, "C.gated") is not None


def test_aliased_import_of_earlier_unit_const():
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("comp.pss", "component C { }"),
        ("ext.pss", """
import cfg_pkg as cfg;
extend component C {
    compile if (cfg::FLAG) {
        target function int gated() { return 1; }
    }
}
"""),
    ])
    assert sym(root, "C.gated") is not None


def test_nested_package_const_from_earlier_unit():
    root = link_files([
        ("cfg.pss", "package outer::inner { static const int LEVEL = 2; }"),
        ("comp.pss", """
compile if (outer::inner::LEVEL == 2) {
    component C { }
}
"""),
    ])
    assert sym(root, "C") is not None


def test_const_chain_across_three_units():
    """A constant whose initializer reads a constant from a third unit."""
    root = link_files([
        ("a.pss", "package a_pkg { static const int K = 2; }"),
        ("b.pss", """
import a_pkg::*;
package b_pkg { static const int J = a_pkg::K + 1; }
"""),
        ("c.pss", """
compile if (b_pkg::J == 3) {
    component C { }
}
"""),
    ])
    assert sym(root, "C") is not None


PLACEMENTS = {
    "package-body": ("""
package p {
    compile if (cfg_pkg::FLAG) {
        struct gated_s { int a; }
    }
}
""", "p::gated_s"),
    "component-primary": ("""
component C {
    compile if (cfg_pkg::FLAG) {
        target function int gated() { return 1; }
    }
}
""", "C.gated"),
    "component-extend": ("""
component C { }
extend component C {
    compile if (cfg_pkg::FLAG) {
        target function int gated() { return 1; }
    }
}
""", "C.gated"),
    "action-body": ("""
component C {
    action A {
        compile if (cfg_pkg::FLAG) {
            rand bit[8] gated;
        }
    }
}
""", "C.A.gated"),
    "struct-body": ("""
struct S {
    compile if (cfg_pkg::FLAG) {
        int gated;
    }
}
""", "S.gated"),
    "file-scope": ("""
compile if (cfg_pkg::FLAG) {
    component C {
        target function int gated() { return 1; }
    }
}
""", "C.gated"),
    "file-scope-extend": ("""
component C { }
compile if (cfg_pkg::FLAG) {
    extend component C {
        target function int gated() { return 1; }
    }
}
""", "C.gated"),
    "constraint-body": ("""
component C {
    action A {
        rand int x;
        constraint {
            compile if (cfg_pkg::FLAG) {
                x > 4;
            }
        }
    }
}
""", None),
    "procedural-body": ("""
component C {
    target function int f() {
        compile if (cfg_pkg::FLAG) {
            return 1;
        }
        return 0;
    }
}
""", None),
}


@pytest.mark.parametrize("placement", sorted(PLACEMENTS))
def test_cross_unit_const_at_each_placement(placement):
    """Every scope that admits a compile if must see an earlier unit's const."""
    body, path = PLACEMENTS[placement]
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("model.pss", "import cfg_pkg::*;\n" + body),
    ])
    if path is not None:
        assert sym(root, path) is not None


#: A reference no scope can resolve.  Elaborating a branch that contains it
#: reports it; pruning the branch leaves the model clean.  This is the only
#: probe available for statement scopes, whose contents are not symbols.
UNRESOLVABLE = "totally_unknown_fn()"

PROCEDURAL_MODEL = """
import cfg_pkg::*;
component C {
    target function int f() {
        compile if (cfg_pkg::FLAG) {
            return %s;
        }
        return 0;
    }
}
""" % UNRESOLVABLE

CONSTRAINT_MODEL = """
import cfg_pkg::*;
component C {
    action A {
        rand int x;
        constraint {
            compile if (cfg_pkg::FLAG) {
                unknown_field > 4;
            }
        }
    }
}
"""


@pytest.mark.parametrize("model,name", [
    (PROCEDURAL_MODEL, "totally_unknown_fn"),
    (CONSTRAINT_MODEL, "unknown_field"),
])
def test_statement_scope_branch_is_really_elaborated(model, name):
    """Enabled: the branch's contents are in the model, so its bad reference
    is reported.  Both statement scopes accept `compile if` only since the
    grammar was corrected -- and the procedural one built its statements and
    then discarded them, which this catches and a "does it parse" test cannot.
    """
    expect_error([("cfg.pss", CFG_TRUE), ("model.pss", model)], name)


@pytest.mark.parametrize("model", [PROCEDURAL_MODEL, CONSTRAINT_MODEL])
def test_statement_scope_disabled_branch_is_pruned(model):
    """Disabled: the same bad reference must not be elaborated at all."""
    link_files([("cfg.pss", CFG_FALSE), ("model.pss", model)])


def test_gated_declaration_is_visible_to_a_still_later_unit():
    """The end-to-end shape this defect blocked: gate, then call from elsewhere.

    One element per file is this project's convention, so a gated function and
    its callers are in different files by construction.
    """
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("comp.pss", "component C { }"),
        ("gated.pss", """
import cfg_pkg::*;
extend component C {
    compile if (cfg_pkg::FLAG) {
        target function int gated() { return 1; }
    }
}
"""),
        ("caller.pss", """
extend component C {
    target function int probe() { return gated(); }
}
"""),
    ])
    assert sym(root, "C.gated") is not None
    assert sym(root, "C.probe") is not None


def test_call_to_a_disabled_declaration_is_reported():
    """The control for the test above: gating it off must be loud, not silent."""
    expect_error([
        ("cfg.pss", CFG_FALSE),
        ("comp.pss", "component C { }"),
        ("gated.pss", """
import cfg_pkg::*;
extend component C {
    compile if (cfg_pkg::FLAG) {
        target function int gated() { return 1; }
    }
}
"""),
        ("caller.pss", """
extend component C {
    target function int probe() { return gated(); }
}
"""),
    ], "gated")


# ===========================================================================
# B. compile assert
# ===========================================================================

def test_compile_assert_reads_true_const_from_earlier_unit():
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("comp.pss", "component C { }"),
        ("assert.pss", """
import cfg_pkg::*;
extend component C {
    compile assert(cfg_pkg::FLAG, "this tree needs FLAG set");
}
"""),
    ])
    assert sym(root, "C") is not None


def test_compile_assert_reads_false_const_from_earlier_unit():
    exc = expect_error([
        ("cfg.pss", CFG_FALSE),
        ("comp.pss", "component C { }"),
        ("assert.pss", """
import cfg_pkg::*;
extend component C {
    compile assert(cfg_pkg::FLAG, "this tree needs FLAG set");
}
"""),
    ], "compile assert failed: this tree needs FLAG set")

    marker = [m for m in exc.markers if "compile assert failed" in m["message"]][0]
    assert marker["severity"] == "error"
    assert marker["file"] == "assert.pss"
    assert marker["line"] == 4
    assert marker["col"] >= 1


@pytest.mark.parametrize("placement,body", [
    ("package-body", "package p { compile assert(cfg_pkg::FLAG, \"needs FLAG\"); }"),
    ("component", "component C { compile assert(cfg_pkg::FLAG, \"needs FLAG\"); }"),
    ("component-extend",
     "component C { }\nextend component C { compile assert(cfg_pkg::FLAG, \"needs FLAG\"); }"),
    ("action", "component C { action A { compile assert(cfg_pkg::FLAG, \"needs FLAG\"); } }"),
])
def test_compile_assert_placements_read_earlier_unit_const(placement, body):
    link_files([("cfg.pss", CFG_TRUE), ("model.pss", "import cfg_pkg::*;\n" + body)])


def test_compile_assert_over_compile_has_from_earlier_unit():
    link_files([
        ("cfg.pss", CFG_TRUE),
        ("model.pss", """
import cfg_pkg::*;
component C {
    compile assert(compile has (cfg_pkg::FLAG), "FLAG not found");
}
"""),
    ])


# ===========================================================================
# C. compile has ordering (19.3)
# ===========================================================================

def test_compile_has_sees_type_from_earlier_unit():
    root = link_files([
        ("p1.pss", "package p1 { struct s { } }"),
        ("p2.pss", """
compile if (compile has (p1::s)) {
    component Present { }
}
"""),
    ])
    assert sym(root, "Present") is not None


def test_compile_has_does_not_see_type_from_a_later_unit():
    """LRM 19.3 / Example 275: a later declaration reads as absent, quietly."""
    root = link_files([
        ("p2.pss", """
compile if (compile has (p1::s)) {
    component Present { }
} else {
    component Absent { }
}
"""),
        ("p1.pss", "package p1 { struct s { } }"),
    ])
    assert sym(root, "Present") is None
    assert sym(root, "Absent") is not None


def test_compile_has_does_not_see_a_disabled_branch_of_an_earlier_unit():
    root = link_files([
        ("cfg.pss", CFG_FALSE),
        ("p1.pss", """
import cfg_pkg::*;
package p1 {
    compile if (cfg_pkg::FLAG) {
        struct s { }
    }
}
"""),
        ("p2.pss", """
compile if (compile has (p1::s)) {
    component Present { }
} else {
    component Absent { }
}
"""),
    ])
    assert sym(root, "Present") is None
    assert sym(root, "Absent") is not None


def test_compile_has_sees_an_enabled_branch_of_an_earlier_unit():
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("p1.pss", """
import cfg_pkg::*;
package p1 {
    compile if (cfg_pkg::FLAG) {
        struct s { }
    }
}
"""),
        ("p2.pss", """
compile if (compile has (p1::s)) {
    component Present { }
}
"""),
    ])
    assert sym(root, "Present") is not None


def test_compile_has_sees_const_from_earlier_unit():
    root = link_files([
        ("cfg.pss", CFG_TRUE),
        ("p2.pss", """
compile if (compile has (cfg_pkg::FLAG)) {
    component Present { }
}
"""),
    ])
    assert sym(root, "Present") is not None


# ===========================================================================
# D. determinability diagnostics (19.1.3)
# ===========================================================================

CANNOT_EVAL = "cannot be evaluated at compile time"


def test_forward_reference_to_a_later_unit_const_is_an_error():
    """Not supported per 19.1.2 -- but it must say so instead of reading false."""
    exc = expect_error([
        ("model.pss", """
import cfg_pkg::*;
compile if (cfg_pkg::FLAG) {
    component C { }
}
"""),
        ("cfg.pss", CFG_TRUE),
    ], CANNOT_EVAL)
    assert "cfg_pkg::FLAG" in str(exc)


def test_unknown_identifier_in_a_condition_is_an_error():
    expect_error([
        ("model.pss", """
compile if (NOT_DECLARED_ANYWHERE) {
    component C { }
}
"""),
    ], CANNOT_EVAL)


def test_non_constant_reference_in_a_condition_is_an_error():
    expect_error([
        ("model.pss", """
component C {
    action A {
        rand int x;
        compile if (x > 2) {
            rand int y;
        }
    }
}
"""),
    ], CANNOT_EVAL)


def test_indeterminable_compile_assert_is_an_error():
    expect_error([
        ("model.pss", """
component C {
    compile assert(NOT_DECLARED_ANYWHERE, "needs a flag");
}
"""),
    ], CANNOT_EVAL)


def test_indeterminable_condition_elaborates_neither_branch():
    """19.1.1 only promises the disabled branch is *syntactically* valid, so an
    unevaluable condition cannot fall back to either side."""
    parser = Parser()
    with pytest.raises(ParseException):
        parser.parses([("model.pss", """
compile if (NOT_DECLARED_ANYWHERE) {
    component Taken { }
} else {
    component NotTaken { }
}
""")])
    files = [f for f in parser._files[1:]]
    names = []
    for f in files:
        for child in f.getChildren():
            name = getattr(child, "getName", lambda: None)()
            if name is not None:
                names.append(name.getId())
    assert "Taken" not in names
    assert "NotTaken" not in names


def test_compile_has_of_a_missing_symbol_is_false_not_an_error():
    """19.3: absence is the answer, never a diagnostic."""
    root = link_files([
        ("model.pss", """
compile if (compile has (nowhere_pkg::MISSING)) {
    component Present { }
} else {
    component Absent { }
}
"""),
    ])
    assert sym(root, "Present") is None
    assert sym(root, "Absent") is not None


# ===========================================================================
# E. environment integrity
# ===========================================================================

def test_processing_order_asymmetry_is_deliberate():
    """Const-unit-first is clean; const-unit-last is a diagnostic.

    Ordinary linking is order-independent, compile-time elaboration is not
    (19.1.2).  This pins the asymmetry so it is not "fixed" by accident.
    """
    cfg = ("cfg.pss", CFG_TRUE)
    model = ("model.pss", """
import cfg_pkg::*;
compile if (cfg_pkg::FLAG) {
    component C { }
}
""")
    root = link_files([cfg, model])
    assert sym(root, "C") is not None
    expect_error([model, cfg], CANNOT_EVAL)


def test_standard_library_is_a_previously_processed_unit():
    root = link_files([
        ("model.pss", """
compile if (compile has (executor_pkg::executor_base_c)) {
    component Present { }
} else {
    component Absent { }
}
"""),
    ])
    assert sym(root, "Present") is not None
    assert sym(root, "Absent") is None


def test_environment_survives_across_parse_calls_on_one_parser():
    parser = Parser()
    parser.parses([("cfg.pss", CFG_TRUE)])
    parser.parses([("model.pss", """
import cfg_pkg::*;
compile if (cfg_pkg::FLAG) {
    component C { }
}
""")])
    root = parser.link()
    assert sym(root, "C") is not None


def test_environment_restarts_after_link():
    """link() hands the units to the linked root, so the environment they
    formed goes with them -- a parse() afterwards starts clean rather than
    reading scopes the Parser no longer owns."""
    parser = Parser()
    parser.parses([("cfg.pss", CFG_TRUE)])
    parser.link()

    with pytest.raises(ParseException) as exc:
        parser.parses([("model.pss", """
import cfg_pkg::*;
compile if (cfg_pkg::FLAG) {
    component C { }
}
""")])
    assert CANNOT_EVAL in str(exc.value)


def test_environment_does_not_leak_between_parser_instances():
    first = Parser()
    first.parses([("cfg.pss", CFG_TRUE)])

    second = Parser()
    with pytest.raises(ParseException) as exc:
        second.parses([("model.pss", """
import cfg_pkg::*;
compile if (cfg_pkg::FLAG) {
    component C { }
}
""")])
    assert CANNOT_EVAL in str(exc.value)


def test_repeated_parses_are_identical():
    files = [
        ("cfg.pss", CFG_TRUE),
        ("comp.pss", "component C { }"),
        ("ext.pss", GATED_EXTEND),
    ]
    for _ in range(2):
        root = link_files(files)
        assert sym(root, "C.gated") is not None
        assert sym(root, "C.not_gated") is None


def test_nested_and_chained_compile_if_across_units():
    root = link_files([
        ("cfg.pss", """
package cfg_pkg {
    static const int LEVEL = 2;
    static const bool FLAG = true;
}
"""),
        ("model.pss", """
import cfg_pkg::*;
component C {
    compile if (cfg_pkg::LEVEL == 1) {
        target function int one() { return 1; }
    } else compile if (cfg_pkg::LEVEL == 2) {
        compile if (cfg_pkg::FLAG) {
            target function int two_flagged() { return 2; }
        }
    } else {
        target function int other() { return 3; }
    }
}
"""),
    ])
    assert sym(root, "C.one") is None
    assert sym(root, "C.two_flagged") is not None
    assert sym(root, "C.other") is None
