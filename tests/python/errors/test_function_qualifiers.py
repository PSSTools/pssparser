"""Function qualifiers, and where a void call may appear.

Four rules from LRM Clause 20, all of which used to link clean:

* **20.2.2 / 20.3.2 -- direction modifiers.**  "Parameter direction modifiers
  (input, output, or inout) are optional in the function declaration.  However,
  if they are specified in the function declaration, such a function may only
  be imported."  A direction on a *prototype* stays legal; it is the arrival of
  a PSS body that makes it illegal, which is why the check runs over every
  prototype of the function rather than over the one the body came with.
* **20.2.6 (a) -- pure functions.**  "Only non-void functions with no output or
  inout parameters may be declared pure."  Both halves follow from what the
  modifier licenses an implementation to do: hoist the call, reorder it, or
  evaluate it once and reuse the result.
* **20.5 -- void calls.**  "Functions not returning a value (declared with void
  return type) may only be called as standalone procedural statements."

The ``pure`` group is the reason this file exists at all.  The checks were
written first and reported nothing, because ``TOK_PURE`` appeared in the
grammar rule unlabelled and ``setIs_pure()`` was called from nowhere: the
modifier was parsed and discarded, so ``getIs_pure()`` was false for every
function ever parsed.  That is the same shape as the dead enum branch in
section 35.3 -- a check that cannot fire, passing vacuously.

Deliberately *not* checked here, and each with a control below recording the
current behaviour:

* ``const`` on a parameter (LRM 20.2.3).  ``PSSParser.g4`` accepts the token
  and drops it -- there is no AST field to check against.
* An ``output`` argument that is not assignable, e.g. ``f(1)`` for
  ``output int a``.  The LRM does not plainly state the rule, and inventing it
  would be guessing (cf. section 33.3).
* Calling a non-void function as a statement, which LRM 20.5 explicitly makes
  **legal** -- it recommends ``(void)f();`` but does not require it.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# 20.2.2 / 20.3.2 -- a direction modifier means "imported only"
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    "function void f(output int a) { }",
    "function void f(inout int a) { }",
    "function void f(input int a) { }",
    "component C { function void f(output int a) { } }",
    "package p { function void f(output int a) { } }",
])
def test_a_direction_modifier_on_a_defined_function_is_rejected(src):
    assert_rejects([("t.pss", src)], "may only be imported, not defined in PSS")


def test_the_direction_may_be_on_an_earlier_prototype():
    """The rule attaches to the declaration, not to the form the body arrived
    in.  Checking only the definition's own prototype -- which the first
    version did -- sees a clean parameter list and accepts the pair."""
    assert_rejects([("t.pss", """
        function void f(output int a);
        function void f(int a) { }
    """)], "may only be imported, not defined in PSS")


def test_one_report_per_function():
    res = assert_rejects([("t.pss",
        "function void f(output int a, inout int b) { }")])
    assert res.output.count("may only be imported") == 1, res.describe()


# --- controls ---

def test_a_direction_on_an_import_still_links():
    """The form the rule exists to permit."""
    assert_clean([("t.pss", "import solve function void f(output int a);")])


def test_a_direction_on_a_bare_prototype_still_links():
    """Legal until an implementation turns up for it."""
    assert_clean([("t.pss", "function void f(output int a);")])


def test_an_undirected_definition_still_links():
    assert_clean([("t.pss", "function void f(int a) { }")])


def test_the_core_library_still_links():
    """`is_core` is the exemption the LRM grants itself: functions built into
    an implementation "may also have output or inout parameters"."""
    assert_clean([("t.pss", """
        package p { import addr_reg_pkg::*; }
        component pss_top { }
    """)])


# ---------------------------------------------------------------------------
# 20.2.6 (a) -- pure functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    "pure function void f(int a);",
    "pure function void f();",
    "component C { pure function void f(int a); }",
])
def test_a_pure_void_function_is_rejected(src):
    assert_rejects([("t.pss", src)], "is declared pure, so it cannot return void")


@pytest.mark.parametrize("src,word", [
    ("pure function int f(output int a);", "output"),
    ("pure function int f(inout int a);", "inout"),
    ("pure function int f(int a, output int b);", "output"),
])
def test_a_pure_function_with_a_side_effecting_parameter_is_rejected(src, word):
    res = assert_rejects([("t.pss", src)], "is declared pure, so parameter")
    assert word in res.output, res.describe()


def test_a_pure_function_can_be_wrong_in_both_ways_at_once():
    res = assert_rejects([("t.pss", "pure function void f(output int a);")])
    assert "cannot return void" in res.output, res.describe()
    assert "cannot be output" in res.output, res.describe()


def test_one_parameter_report_per_prototype():
    res = assert_rejects([("t.pss",
        "pure function int f(output int a, output int b, inout int c);")])
    assert res.output.count("is declared pure, so parameter") == 1, res.describe()


def test_the_pure_modifier_is_actually_recorded():
    """The regression test for the reason the checks above reported nothing
    when they were first written.

    ``TOK_PURE`` was in the grammar rule but unlabelled, and ``setIs_pure()``
    was called from nowhere, so the modifier was parsed and thrown away.  Every
    check written against ``getIs_pure()`` was dead code.  Any of the cases
    above would catch a regression, but none of them says *why* -- this one
    reads the flag off the AST.
    """
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from pssparser.parser import Parser

    p = Parser()
    p.parses([("t.pss", "pure function int f(int a); function int g(int a);")])
    root = p.link()

    flags = {}
    for ch in root.getChildren():
        get_name = getattr(ch, "getName", None)
        if not callable(get_name):
            continue
        try:
            name = ch.getName()
        except Exception:
            continue
        if name not in ("f", "g"):
            continue
        protos = ch.getPrototypes()
        assert protos, "no prototype recorded for %s" % name
        flags[name] = protos[0].getIs_pure()

    assert flags.get("f") is True, "`pure` was parsed and discarded: %r" % flags
    assert flags.get("g") is False, "every function came back pure: %r" % flags


# --- controls ---

@pytest.mark.parametrize("src", [
    "pure function int f(int a);",
    "pure function int f();",
    "pure function bit[32] f(int a, string s);",
    "component C { pure function int f(int a); }",
])
def test_a_well_formed_pure_function_still_links(src):
    assert_clean([("t.pss", src)])


def test_the_stdlib_pure_functions_still_link():
    """`addr_reg_pkg` declares several -- all non-void, none with a direction.
    A rule that rejected them would be wrong about the core library."""
    assert_clean([("t.pss", """
        package p { import addr_reg_pkg::*; }
        component pss_top { }
    """)])


def test_pure_may_be_omitted_on_the_definition():
    """LRM 20.2.6 (b): the keyword "may be omitted in a function definition if
    its original declaration contains the pure keyword"."""
    assert_clean([("t.pss", """
        pure function int f(int a);
        function int f(int a) { return a; }
    """)])


# ---------------------------------------------------------------------------
# 20.5 -- a void call may only be a standalone statement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    "function void f(); function void g() { int v; v = f(); }",
    "function void f(); function void h(int a); function void g() { h(f()); }",
    "function void f(); function int g() { return f(); }",
    "function void f(); function void g() { int v; v = f() + 1; }",
    "function void f(); function void g() { if (f()) { } }",
])
def test_using_the_result_of_a_void_call_is_rejected(src):
    assert_rejects([("t.pss", src)],
                   "returns void, so its result cannot be used as a value")


def test_a_qualified_void_call_is_checked_too():
    assert_rejects([("t.pss", """
        package p { function void f(); }
        component C { action A { exec body { int v; v = p::f(); } } }
    """)], "returns void, so its result cannot be used as a value")


def test_a_void_call_through_a_component_instance_is_checked():
    """A multi-element path, which is what the "last element only" rule is
    about: the value of ``c.f()`` is the value of ``f()``, and ``c`` is a
    scope lookup rather than a use of a value."""
    assert_rejects([("t.pss", """
        component C { function void f(); }
        component pss_top { C c; function void g() { int v; v = c.f(); } }
    """)], "returns void, so its result cannot be used as a value")


def test_a_void_method_call_is_checked_too():
    assert_rejects([("t.pss", """
        component C {
            function void f();
            function void g() { int v; v = f(); }
        }
    """)], "returns void, so its result cannot be used as a value")


# --- controls ---

@pytest.mark.parametrize("src", [
    "function void f(); function void g() { f(); }",
    "function void f(int a); function void g() { f(1); }",
    "package p { function void f(int a); } "
        "component C { action A { exec body { p::f(1); } } }",
    "component C { function void f(); function void g() { f(); } }",
    "component C { function void f(); } "
        "component pss_top { C c; function void g() { c.f(); } }",
])
def test_a_standalone_void_call_still_links(src):
    """The statement position the rule exists to permit.  A qualified name
    builds a different expression node from an unqualified one, and setting
    the statement-position marker on only one of the two made every
    ``p::f(1);`` look like an operand."""
    assert_clean([("t.pss", src)])


def test_a_nonvoid_call_as_a_statement_still_links():
    """LRM 20.5 makes this explicitly legal: "Calling a nonvoid function as if
    has no return value shall be legal".  The `(void)` cast is a
    recommendation, not a rule, so this is not diagnosed."""
    assert_clean([("t.pss", "function int f(); function void g() { f(); }")])


def test_a_nonvoid_result_used_as_a_value_still_links():
    assert_clean([("t.pss",
        "function int f(); function void g() { int v; v = f(); }")])


def test_a_void_call_nested_in_a_void_statement_call_is_still_reported():
    """`f(g())` is one statement, but only the outer call is in statement
    position.  The marker is saved and restored around each ref-path rather
    than assigned once, so the inner call is still an operand."""
    assert_rejects([("t.pss", """
        function void g();
        function void f(int a);
        function void h() { f(g()); }
    """)], "returns void, so its result cannot be used as a value")


# ---------------------------------------------------------------------------
# Recorded, not fixed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    "function void f(const int a) { }",
    "function void f(const int a);",
    "import solve function void f(const int a);",
])
def test_const_parameters_are_accepted_but_not_modelled(src):
    """LRM 20.2.3 gives `const` real rules -- it may be specified for native
    functions only, it shall not be combined with a direction, it may not be
    applied to reference types, and it is part of the signature for
    redeclarations.  None of them is checkable: ``PSSParser.g4`` matches
    ``TOK_CONST`` unlabelled in ``function_parameter`` and the builder never
    reads it, so no AST node records that the parameter was const.

    Pinned so that adding the AST field is a visible change.  The third case
    is illegal PSS ("can be specified for native functions only") and is
    accepted here.
    """
    assert_clean([("t.pss", src)])


def test_const_before_a_direction_is_a_syntax_error():
    """Not a semantic check -- the grammar orders the two qualifiers
    ``function_parameter_dir? TOK_CONST?``, so this ordering simply does not
    parse.  Recorded because it makes LRM 20.2.3 (a) look half-enforced: the
    other ordering is accepted silently."""
    assert_rejects([("t.pss", "import solve function void f(const output int a);")],
                   "syntax error")


@pytest.mark.parametrize("src", [
    "function void f(output int a); function void g() { f(1); }",
    "function void f(output int a); function void g() { int v; f(v+1); }",
    "function void f(inout int a); function void g() { f(5); }",
])
def test_a_non_assignable_output_argument_is_accepted(src):
    """Deliberately unchecked.  Passing a literal where the callee will write
    a result is very likely a mistake, but the LRM does not state the rule --
    20.3.2 describes how parameters are passed, not what an argument must be.
    Recorded rather than guessed at; see section 33.3 for the same decision
    about return-on-every-path."""
    assert_clean([("t.pss", src)])
