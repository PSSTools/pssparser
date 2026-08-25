"""
Tests that constraints survive template specialization intact (known-issues P3-X3).

`TaskCopyAst` builds the specialized copy of a parameterized type. A constraint
kind with no visitor there used to come back null; the null was pushed into the
specialization's constraint list, and the next walk over that list dereferenced
it. So the failure mode was not the silent weakening the original entry
described -- it was a segfault, for `foreach`, `forall` and `->` alike.

Each test therefore asserts the copied constraint is *present and equivalent*,
not merely that specialization did not crash. Structure is compared against the
unspecialized declaration, so a test cannot pass by both sides being empty.

Closing that copy then exposed two more defects, both fixed here and covered
below: field references inside a specialization did not resolve (P3-X4), and a
parameterized type declared inside a component crashed the linker (P3-X3a).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pssparser import Parser


def link_ignoring_errors(code):
    """Link and return the root scope without raising on error markers.

    The structural tests want the tree itself, independent of whether anything
    in it failed to resolve; resolution is asserted separately, by the tests
    that go through `Parser.link()`.
    """
    p = Parser()
    p.parses([("t.pss", code)])
    linker = p.parser_f.mkAstLinker()
    markers = p.parser_f.mkMarkerCollector()
    return p, linker.link(markers, p._files)


def find_type_scope(scope, name, depth=0):
    """Depth-bounded search for a SymbolTypeScope by name.

    Bounded by depth rather than a visited set: accessors hand back a fresh
    wrapper each call, so `id()` is neither stable nor unique.
    """
    if depth > 10:
        return None
    try:
        n = scope.numChildren()
    except AttributeError:
        return None
    for i in range(n):
        c = scope.getChild(i)
        if c is None:
            continue
        if getattr(c, "getName", lambda: None)() == name and hasattr(c, "numSpec_types"):
            return c
        found = find_type_scope(c, name, depth + 1)
        if found is not None:
            return found
    return None


def constraint_block(type_scope, name):
    target = type_scope.getTarget()
    for i in range(target.numChildren()):
        child = target.getChild(i)
        if type(child).__name__ == "ConstraintBlock" and child.getName() == name:
            return child
    return None


def outline(c):
    """A comparable summary of a constraint sub-tree.

    Covers kind, position, nested statements and the iteration-variable scope
    -- everything a specialization has to reproduce for the copy to mean what
    the declaration meant.
    """
    entry = {
        "kind": type(c).__name__,
        "index": c.getIndex(),
        "constraints": [],
    }

    if hasattr(c, "numConstraints"):
        entry["constraints"] = [
            outline(c.getConstraint(k)) for k in range(c.numConstraints())]

    if hasattr(c, "getSymtab"):
        symtab = c.getSymtab()
        entry["symtab"] = None if symtab is None else {
            "name": symtab.getName(),
            "children": [
                None if symtab.getChild(k) is None
                else symtab.getChild(k).getName().getId()
                for k in range(symtab.numChildren())],
        }

    if hasattr(c, "getIt"):
        entry["it"] = None if c.getIt() is None else c.getIt().getName().getId()
        entry["idx"] = None if c.getIdx() is None else c.getIdx().getName().getId()

    return entry


def declared_and_specialized(body, name="S"):
    """Return (declared, specialized) outlines of constraint block `c`."""
    code = """
    package p {
        struct E { rand int val; }
        struct %s<int W = 4> {
            rand bit[8] arr[4];
            rand bit    m;
            rand int    x;
            constraint c {
                %s
            }
        }
    }
    component pss_top {
        p::%s<8> s;
    }
    """ % (name, body, name)

    _parser, root = link_ignoring_errors(code)
    decl = find_type_scope(root, name)
    assert decl is not None, "declaration not found"
    assert decl.numSpec_types() == 1, (
        "expected exactly one specialization, got %d" % decl.numSpec_types())

    declared = constraint_block(decl, "c")
    specialized = constraint_block(decl.getSpec_type(0), "c")
    assert declared is not None, "declaration has no constraint block"
    assert specialized is not None, "specialization has no constraint block"

    return (
        [outline(declared.getConstraint(i))
            for i in range(declared.numConstraints())],
        [outline(specialized.getConstraint(i))
            for i in range(specialized.numConstraints())],
    )


def test_foreach_survives_specialization():
    """A foreach is copied whole -- body, iteration scope and index variable."""
    declared, specialized = declared_and_specialized(
        "foreach (arr[i]) { arr[i] > 0; }")

    assert declared[0]["kind"] == "ConstraintStmtForeach"
    assert declared[0]["idx"] == "i"
    assert declared[0]["constraints"], "declaration itself has an empty body"
    assert specialized == declared


def test_implication_survives_specialization():
    """An implication is copied with its consequent, not just its antecedent."""
    declared, specialized = declared_and_specialized("m -> { x < 10; }")

    assert declared[0]["kind"] == "ConstraintStmtImplication"
    assert declared[0]["constraints"], "declaration itself has an empty body"
    assert specialized == declared


def test_forall_survives_specialization():
    """A forall is copied whole, including its quantified iterator."""
    declared, specialized = declared_and_specialized(
        "forall (a : E) { a.val > 5; }")

    assert declared[0]["kind"] == "ConstraintStmtForall"
    # The iterator is constraints[0] and is referenced from the symbol scope;
    # both halves have to come through the copy.
    assert declared[0]["constraints"][0]["kind"] == "ConstraintStmtField"
    assert declared[0]["symtab"]["children"] == ["a"]
    assert specialized == declared


def test_all_constraint_kinds_survive_together():
    """The whole block round-trips, with each statement at its declared index."""
    declared, specialized = declared_and_specialized("""
        foreach (arr[i]) { arr[i] > 0; soft arr[i] < 100; }
        m -> { x < 10; }
        if (m) { x < 5; } else { x > 20; }
        forall (a : E) { a.val > 5; }
        x != 7;
    """)

    assert [c["kind"] for c in declared] == [
        "ConstraintStmtForeach",
        "ConstraintStmtImplication",
        "ConstraintStmtIf",
        "ConstraintStmtForall",
        "ConstraintStmtExpr",
    ]
    assert specialized == declared


def test_soft_constraint_position_is_preserved():
    """
    A soft constraint's priority is its position in the model, so a copy that
    loses `index` silently changes what the model means.
    """
    declared, specialized = declared_and_specialized("""
        soft x > 10;
        soft x < 60;
    """)

    assert [c["index"] for c in declared] == [0, 1]
    assert [c["index"] for c in specialized] == [0, 1]


def test_specializing_a_type_with_a_foreach_does_not_crash():
    """
    Direct guard on the original failure. A dropped constraint left a null in
    the constraint list, and TaskBuildSymbolTree walked into it -- so the
    symptom was a segfault, which no assertion in this file would survive to
    report.
    """
    _parser, root = link_ignoring_errors("""
    package p {
        struct S<int W = 4> {
            rand bit[8] arr[4];
            constraint c { foreach (arr[i]) { arr[i] > 0; } }
        }
    }
    component pss_top {
        p::S<8> s;
    }
    """)
    assert root is not None


SCOPES = {
    "global": """
        struct S<int W = 4> { %s }
        component pss_top { S<8> s; }
    """,
    "package": """
        package p { struct S<int W = 4> { %s } }
        component pss_top { p::S<8> s; }
    """,
    # P3-X3a: this one used to segfault the linker in
    # TaskResolveSymbolPathRef::mkIterator, before any constraint was reached.
    # `mkIterator` asked whether each enclosing scope was a specialization by
    # dereferencing its template parameter list, which is null for every
    # ordinary component.
    "component": """
        component pss_top {
            struct S<int W = 4> { %s }
            action T { S<8> s; }
        }
    """,
}


@pytest.mark.parametrize("placement", sorted(SCOPES))
def test_field_ref_in_a_specialized_constraint_resolves(placement):
    """
    P3-X4. Not specific to foreach/forall/implication, which is why the body is
    the plainest constraint there is: `x > 0` in an instantiated parameterized
    type used to report `PSS002 unknown identifier 'x'`.

    The cause was in `TaskGetSymbolScope`, which had no `visitSymbolTypeScope`
    override. The generated visitor set the result and then descended into the
    type's `<plist>`, overwriting it -- so a lookup inside `struct S<int W>`
    searched the scope holding `W` and never the type's own fields. A type with
    no parameters has a null plist, which is why only parameterized types were
    affected.
    """
    parser = Parser()
    parser.parses([("t.pss", SCOPES[placement] % """
        rand int x;
        constraint c { x > 0; }
    """)])
    parser.link()


@pytest.mark.parametrize("placement", sorted(SCOPES))
def test_a_parameterized_type_links_in_every_scope(placement):
    """P3-X3a, with no constraints at all -- an empty body reproduced it."""
    parser = Parser()
    parser.parses([("t.pss", SCOPES[placement] % "rand int x;")])
    parser.link()


def test_references_inside_copied_loop_constraints_resolve():
    """
    The iteration variables and the fields they constrain both resolve inside a
    specialization -- `foreach` and `forall` bring their own symbol scopes, so
    they exercise more of the copy than a flat constraint does.
    """
    parser = Parser()
    parser.parses([("t.pss", """
    package p {
        struct E { rand int val; }
        struct S<int W = 4> {
            rand bit[8] arr[4];
            rand bit    m;
            rand int    x;
            constraint c {
                foreach (arr[i]) { arr[i] > 0; soft arr[i] < 100; }
                m -> { x < 10; }
                if (m) { x < 5; } else { x > 20; }
                forall (a : E) { a.val > 5; }
                x != 7;
            }
        }
    }
    component pss_top {
        p::S<8> s;
    }
    """)])
    parser.link()
