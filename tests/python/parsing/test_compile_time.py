"""
Tests for PSS compile-time features.

Tests compile-time conditionals (compile if), compile-time queries (compile has),
and compile-time assertions.

Based on PSS LRM v3.0 Chapter 18 (Compile-time Elaboration).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Compile If Tests
# ============================================================================

def test_compile_if_true():
    """Test compile if with true condition."""
    pss = """
component MyComponent {
    compile if (true) {
        action A { }
    }
}
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_compile_if_false():
    """Test compile if with false condition."""
    pss = """
    component MyComponent {
        compile if (false) {
            action A { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_else():
    """Test compile if-else."""
    pss = """
    component MyComponent {
        compile if (true) {
            action A { }
        } else {
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_nested():
    """Test nested compile if."""
    pss = """
    component MyComponent {
        compile if (true) {
            compile if (true) {
                action A { }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_in_action():
    """Test compile if inside action."""
    pss = """
    component MyComponent {
        action A {
            compile if (true) {
                rand bit[8] field1;
            }
            compile if (false) {
                rand bit[16] field2;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_in_struct():
    """Test compile if inside struct."""
    pss = """
    component MyComponent {
        struct MyStruct {
            compile if (true) {
                bit[8] field1;
            }
            compile if (false) {
                bit[16] field2;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Compile Has Tests
# ============================================================================

def test_compile_has_type():
    """Test compile has for type existence."""
    pss = """
    component MyComponent {
        action A { }
        compile if (compile has (A)) {
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_has_field():
    """Test compile has for field existence."""
    pss = """
    component MyComponent {
        struct MyStruct {
            bit[8] field1;
        }
        action A {
            MyStruct s;
            compile if (compile has (s.field1)) {
                rand bit[8] value;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_has_nested():
    """Test nested compile has checks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        compile if (compile has (A)) {
            compile if (compile has (B)) {
                action C { }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_has_negative():
    """Test compile has with negation."""
    pss = """
    component MyComponent {
        action A { }
        compile if (!compile has (NonExistent)) {
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Compile Assert Tests
# ============================================================================

def test_compile_assert_simple():
    """Test simple compile assert."""
    pss = """
    component MyComponent {
        compile assert (true, "This should pass");
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_assert_with_expression():
    """Test compile assert with expression."""
    pss = """
    component MyComponent {
        compile assert (1 + 1 == 2, "Math works");
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_assert_multiple():
    """Test multiple compile asserts."""
    pss = """
    component MyComponent {
        compile assert (true, "First assertion");
        compile assert (true, "Second assertion");
        compile assert (true, "Third assertion");
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_assert_in_action():
    """Test compile assert inside action."""
    pss = """
    component MyComponent {
        action A {
            compile assert (true, "Inside action");
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Combined Compile Features Tests
# ============================================================================

def test_compile_if_has_assert_combined():
    """Test combination of compile if, has, and assert."""
    pss = """
    component MyComponent {
        action A { }
        compile if (compile has (A)) {
            compile assert (true, "A exists");
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_with_multiple_branches():
    """Test compile if with elsif and else."""
    pss = """
    component MyComponent {
        compile if (false) {
            action A { }
        } else compile if (false) {
            action B { }
        } else {
            action C { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("branch_count", [2, 4, 6])
def test_scalability_multiple_compile_ifs(branch_count):
    """Test multiple compile if blocks."""
    branches = "\n".join([
        f"""        compile if (true) {{
            action A{i} {{ }}
        }}""" for i in range(branch_count)
    ])
    
    pss = f"""
    component MyComponent {{
{branches}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("nesting_depth", [2, 3, 4])
def test_scalability_nested_compile_ifs(nesting_depth):
    """Test deeply nested compile if statements."""
    def generate_nested(depth):
        if depth == 0:
            return "                action A { }"
        indent = "    " * (depth + 2)
        return f"""{indent}compile if (true) {{
{generate_nested(depth-1)}
{indent}}}"""
    
    nested = generate_nested(nesting_depth)
    pss = f"""
    component MyComponent {{
{nested}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("assert_count", [3, 6, 10])
def test_scalability_multiple_asserts(assert_count):
    """Test multiple compile assertions."""
    asserts = "\n".join([
        f'        compile assert (true, "Assertion {i}");'
        for i in range(assert_count)
    ])
    
    pss = f"""
    component MyComponent {{
{asserts}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# PSS 3.1: compile-if branch delimiters (plan item P1-G4, decisions D1/D2)
# ============================================================================
# Five of the ten `*_compile_if_item` rules emitted TOK_LSBRACE/TOK_RSBRACE
# (`[ ]`) where the spec has `{ }`, and three of those admitted only a single
# item -- so none of them accepted any conforming source. Each now carries both
# alternatives, matching the other five.
#
# Per decision D2, the brace-less single-item form stays legal, but is reported
# as deprecated (PSS104). The check lives in one shared builder helper,
# AstBuilderInt::checkCompileIfBranches, so the message and severity are
# identical across all ten scopes -- which is what the parametrization below is
# really asserting.

from test_helpers import (  # noqa: E402
    assert_parse_error, assert_parse_ok_with_warning, assert_no_marker,
    parse_collect, find_markers,
)

# (scope name, source template with one %s, body item to place in the branch)
COMPILE_IF_SCOPES = [
    ("package",
     "package p { compile if (1) %s }",
     "struct S1 { int a; }"),
    ("annotation",
     "package p { annotation a_s { compile if (1) %s } }",
     "int a;"),
    ("action",
     "component C { action A { compile if (1) %s } }",
     "int a;"),
    ("component",
     "component C { compile if (1) %s }",
     "int a;"),
    ("struct",
     "struct S { compile if (1) %s }",
     "int a;"),
    ("monitor",
     "component C { action A {} monitor M { compile if (1) %s } }",
     "A a;"),
    ("constraint",
     "component C { action A { rand int x; constraint c { compile if (1) %s } } }",
     "x > 0;"),
    ("covergroup",
     "covergroup cg(bit[8] p1) { compile if (1) %s }",
     "coverpoint p1;"),
    ("procedural",
     "component C { function void f() { compile if (1) %s } }",
     "int a;"),
    ("override",
     "component C { action A {} action B {} override { compile if (1) %s } }",
     "type A with B;"),
]

_SCOPE_IDS = [s[0] for s in COMPILE_IF_SCOPES]


@pytest.mark.parametrize("name,template,item", COMPILE_IF_SCOPES, ids=_SCOPE_IDS)
def test_compile_if_braced_branch_accepted(name, template, item):
    """The conforming form parses, and parses silently."""
    src = template % ("{ %s }" % item)
    assert_parse_ok(src)
    assert_no_marker(src, severity="warning")


@pytest.mark.parametrize("name,template,item", COMPILE_IF_SCOPES, ids=_SCOPE_IDS)
def test_compile_if_bare_branch_warns_but_parses(name, template, item):
    """D2: the brace-less form stays legal, and warns."""
    src = template % item
    assert_parse_ok_with_warning(src, marker_id="PSS104")


@pytest.mark.parametrize("name,template,item", COMPILE_IF_SCOPES, ids=_SCOPE_IDS)
def test_compile_if_square_brackets_rejected(name, template, item):
    """`[ ]` was never valid PSS; it was a defect in this grammar."""
    assert_parse_error(template % ("[ %s ]" % item))


@pytest.mark.parametrize("name,template,item", COMPILE_IF_SCOPES, ids=_SCOPE_IDS)
def test_compile_if_deprecation_message_is_uniform(name, template, item):
    """
    One shared helper emits this, so every scope must produce the identical
    message. A scope that grew its own copy would drift.
    """
    _, markers = parse_collect(template % item)
    warnings = find_markers(markers, marker_id="PSS104")
    assert len(warnings) == 1
    assert warnings[0]["message"] == \
        "'compile if' branch without enclosing braces is deprecated"


# -- multi-item branches -----------------------------------------------------
# constraint / covergroup / override previously accepted a single item only.

def test_compile_if_multiple_items_in_constraint():
    assert_parse_ok("""
    component C {
        action A {
            rand int x, y;
            constraint c { compile if (1) { x > 0; y > 0; } }
        }
    }
    """)


def test_compile_if_multiple_items_in_covergroup():
    assert_parse_ok("""
    covergroup cg(bit[8] p1, bit[8] p2) {
        compile if (1) { coverpoint p1; coverpoint p2; }
    }
    """)


def test_compile_if_multiple_items_in_override():
    assert_parse_ok("""
    component C {
        action A {} action B {} action D {}
        override { compile if (1) { type A with B; type B with D; } }
    }
    """)


def test_compile_if_empty_braced_branch():
    assert_parse_ok("component C { compile if (1) { } }")


# -- else branches -----------------------------------------------------------

def test_compile_if_else_both_braced_is_silent():
    src = "component C { compile if (1) { int a; } else { int b; } }"
    assert_parse_ok(src)
    assert_no_marker(src, severity="warning")


def test_compile_if_else_bare_branch_warns_even_when_not_taken():
    """
    The bare spelling is deprecated regardless of which way the condition
    evaluates. Warning only on the taken branch would make the diagnostic
    appear and disappear as unrelated configuration changed.
    """
    _, markers = parse_collect(
        "component C { compile if (1) { int a; } else int b; }")
    assert len(find_markers(markers, marker_id="PSS104")) == 1


def test_compile_if_both_branches_bare_warns_twice():
    _, markers = parse_collect(
        "component C { compile if (1) int a; else int b; }")
    assert len(find_markers(markers, marker_id="PSS104")) == 2


# -- procedural scope: braces are grouping, not a sequence block --------------

def test_procedural_compile_if_is_reachable():
    """
    `procedural_compile_if` was defined but never referenced from
    `procedural_stmt`, so `compile if` in a function body did not parse at all.
    """
    assert_parse_ok("component C { function void f() { compile if (1) { int a; } } }")


def test_procedural_compile_if_braces_are_not_a_sequence_block():
    """
    `{ ... }` is also spelled as a procedural sequence block, so the two
    alternatives genuinely overlap here. The braced compile-if group must win,
    otherwise the conforming form would be reported as the deprecated one.
    """
    assert_no_marker(
        "component C { function void f() { compile if (1) { int a; } } }",
        marker_id="PSS104")


def test_procedural_compile_if_explicit_sequence_block_still_parses():
    assert_parse_ok(
        "component C { function void f() { compile if (1) sequence { int a; } } }")


def test_procedural_compile_if_bare_stmt_warns():
    assert_parse_ok_with_warning(
        "component C { function void f() { compile if (1) int a; } }",
        marker_id="PSS104")
