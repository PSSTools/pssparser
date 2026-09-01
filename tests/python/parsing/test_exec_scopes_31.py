"""``P7-T11`` -- every exec form, in every scope that admits exec blocks.

Regression cover for **P7-G3**: ``component_body_item`` referenced ``exec_block``
-- the brace form alone -- where ``action_body_item`` and ``struct_body_item``
both reference ``exec_block_stmt``.  The consequence was broad and had nothing
to do with obscure syntax: ``exec header``, ``exec declaration``,
``exec run_start``, ``exec run_end``, tagged exec blocks and ``exec file`` were
all syntax errors **in a component**, which is the scope where most of them are
actually written.  Actions and structs were unaffected, which is why nothing
noticed.

The module is deliberately a matrix rather than a list of cases.  The defect was
not "``exec file`` is unsupported" -- the rule existed and was correct, and
worked two scopes over.  It was that *one* scope reached a narrower rule than
its siblings, and a matrix is what makes that visible: read down a column and
the scopes must agree.  A flat list of component-scope cases would have pinned
the fix without pinning the property that was actually violated.

**On Annex B.**  B.7 really does give ``component_body_item ::= ... | exec_block``
and B.4 gives ``exec_block ::= exec exec_kind { { exec_stmt } }``, so what this
module asserts is *not* derivable from Annex B as written.  It is derivable from
the standard taken as a whole: Example 309 puts ``exec file`` directly inside
``component cpu_executor_c``, and 20.5.4 both states that exec blocks "declared
in different types, including different action types or components, may match"
and lists the taggable kinds as ``header``, ``declaration``, ``run_start``,
``run_end`` and ``exec file`` -- every one a target-template kind, and tags are
explicitly not permitted on native brace blocks.  Filed upstream as item 8 of
``docs/design/pss31-prd-spec-comments.md``.  If that comment is rejected, this
module is the thing to revisit -- not the grammar, which is currently the only
reading under which the document's own example parses.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_collect  # noqa: E402


#: The five exec spellings, as a body fragment.  ``{scope}`` is where the
#: fragment lands; every one is legal in all three scopes.
#:
#: ``tagged`` and ``file`` are the two that matter most: 20.5.4 permits a tag
#: only on target-template blocks, so a scope that cannot hold a target-template
#: block cannot hold a tagged one either -- the two failed together, and they
#: are the pair that connects this module to Example 309.
EXEC_FORMS = {
    "brace": "exec init_up { int x = 1; }",
    "target_code": 'exec header C = "int x;";',
    "target_file": 'exec file "out.txt" = "hi";',
    "target_file_templated_name": 'exec file """out_{{nm}}.txt""" = """hi""";',
    "tagged": 'exec declaration C = tg{.n = "A"} : "int y;";',
}

#: The three scopes B.5/B.6/B.7 give exec blocks to.  ``nm`` is declared in each
#: so the templated filename has something to interpolate, and ``tg`` is a
#: package-scope struct so the tagged form has a tag type in every case.
SCOPES = {
    "component": "package p { struct tg { string n; } component C { string nm; %s } }",
    "action": "package p { struct tg { string n; } component C { action A { string nm; %s } } }",
    "struct": "package p { struct tg { string n; } struct S { string nm; %s } }",
}


def _syntax_errors(src):
    _, markers = parse_collect(src, "t.pss")
    return [m for m in markers if m["severity"] == "error"]


@pytest.mark.parametrize("scope", sorted(SCOPES))
@pytest.mark.parametrize("form", sorted(EXEC_FORMS))
def test_every_exec_form_parses_in_every_exec_scope(form, scope):
    """The matrix.  Fifteen cells; five of them -- the component column minus
    the brace form -- were syntax errors before P7-G3.

    Parametrised over both axes rather than written out so that adding a scope
    or a form cannot quietly cover only some of the combinations, which is the
    shape of the original defect.
    """
    errs = _syntax_errors(SCOPES[scope] % EXEC_FORMS[form])
    assert not errs, "%s exec in a %s body: %s" % (
        form, scope, [m["message"] for m in errs])


def test_component_and_action_admit_the_same_exec_forms():
    """The property the matrix exists to protect, asserted directly.

    P7-G3 was not a missing rule -- ``target_file_exec_block`` existed and was
    correct -- but one scope reaching a *narrower* rule than its siblings.  That
    is invisible to any test that checks a scope in isolation, and it is what
    this asserts: the three scopes accept the same set, whatever that set is.

    Written as a set comparison so a future divergence names the forms that
    diverged rather than failing on whichever cell pytest reached first.
    """
    accepted = {
        scope: {f for f in EXEC_FORMS
                if not _syntax_errors(tmpl % EXEC_FORMS[f])}
        for scope, tmpl in SCOPES.items()
    }
    assert accepted["component"] == accepted["action"] == accepted["struct"], (
        "the exec scopes have diverged; each should admit the same forms: %s"
        % accepted)


def test_example_309_shape_parses():
    """The specific construct Annex B cannot derive, kept as its own case.

    Not folded into the matrix: this is the *evidence* for the upstream comment,
    so it should fail with a name that says what was lost rather than as one
    cell of a parametrisation.  Close to the LRM's text, trimmed to what parses
    standalone.
    """
    src = '''
package p {
    component executor_c { }
    component cpu_executor_c : executor_c {
        struct boot_tag { string target_id; }
        string target_id;

        exec file """boot_{{target_id}}.S""" = boot_tag{.target_id = target_id} : """
            .global _start_{{target_id}}
            _start_{{target_id}}: /* ... */
        """;
    }
}
'''
    errs = _syntax_errors(src)
    assert not errs, "Example 309 does not parse: %s" % [m["message"] for m in errs]


def test_brace_exec_in_a_component_was_never_affected():
    """The control.

    The brace form is the one alternative the old ``component_body_item`` did
    reach, so it parsed throughout.  Pinned beside the others because a change
    that broke *it* would be a regression in the opposite direction, and because
    its passing is what localised the original defect to the rule reference
    rather than to component bodies generally.
    """
    assert not _syntax_errors(SCOPES["component"] % EXEC_FORMS["brace"])
