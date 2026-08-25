"""
Tests for PSS 3.1 exec block tags (P3-X1, LRM §20.5.4) and `pre_body` (P3-X2).

::

    target_code_exec_block ::= exec exec_kind language_identifier
                                   = [ exec_block_tag : ] string_literal ;
    target_file_exec_block ::= exec file filename_string
                                   = [ exec_block_tag : ] string_literal ;
    exec_block_tag         ::= type_identifier [ struct_literal ]

A tag exists solely so a code generator can decide whether two emitted blocks
are equivalent and may be coalesced. It affects neither traversal, solving, nor
runtime execution.

**Target exec blocks were previously discarded outright.** Both
`visitTarget_code_exec_block` and `visitTarget_file_exec_block` were bare
`TODO`s, so `exec header C = "...";` parsed and produced no AST at all. They now
build an `ExecTargetTemplateBlock`. The `{{expr}}` substitutions inside the
template body are still *not* extracted -- that needs a sub-parser and is P5-I1
-- so `parameters` stays empty and the raw text is preserved in `data`.

**Placement (PSS106) is checked in the builder, not the linker.** §20.5.4 permits
tags only on `header`, `declaration`, `run_start`, `run_end` and `exec file`.
Deciding that needs nothing but the exec kind, which is known while building.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import (  # noqa: E402
    assert_parse_ok, assert_parse_error, assert_marker, assert_no_marker,
)
from pssparser import Parser  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []

_TAG = "struct tag_s { string name; int id; }\n"

# Target exec blocks reach the grammar through `exec_block_stmt`, which
# `action_body_item` and `struct_body_item` reference. `component_body_item`
# deliberately does not: Annex B B.8 gives a component only the braced
# `exec_block`, so `exec header` directly in a component body is a syntax error
# in 3.1 as it was in 3.0.
_ACTION = _TAG + "component pss_top { action A { %s } }"
_STRUCT = _TAG + "struct S { %s }"

_TAGGABLE = ["header", "declaration", "run_start", "run_end"]
_UNTAGGABLE = ["body", "init_down", "init_up", "pre_solve", "post_solve",
               "pre_body"]


def _exec_block(code):
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    assert not parser.markers, [m for m in parser.markers]

    def walk(node, depth=0):
        if node is None or depth > 20 or not hasattr(node, "numChildren"):
            return None
        for i in range(node.numChildren()):
            child = node.getChild(i)
            if type(child).__name__ == "ExecTargetTemplateBlock":
                return child
            found = walk(child, depth + 1)
            if found is not None:
                return found
        return None

    for scope in parser._files[1:]:
        found = walk(scope)
        if found is not None:
            return found
    raise AssertionError("no ExecTargetTemplateBlock built")


# ===========================================================================
# Syntax
# ===========================================================================

@pytest.mark.parametrize("kind", _TAGGABLE)
def test_tagged_target_code_block_parses(kind):
    assert_parse_ok(_ACTION % ('exec %s C = tag_s: "code";' % kind))


@pytest.mark.parametrize("kind", _TAGGABLE)
def test_tagged_with_struct_literal_parses(kind):
    assert_parse_ok(_ACTION % (
        'exec %s C = tag_s {.name = "n", .id = 1}: "code";' % kind))


def test_untagged_target_code_block_still_parses():
    assert_parse_ok(_ACTION % 'exec header C = "code";')


def test_tagged_target_file_block_parses():
    assert_parse_ok(_ACTION % 'exec file "out.c" = tag_s: "code";')


def test_untagged_target_file_block_still_parses():
    assert_parse_ok(_ACTION % 'exec file "out.c" = "code";')


def test_tagged_block_in_a_struct():
    assert_parse_ok(_STRUCT % 'exec header C = tag_s: "code";')


def test_tagged_block_with_a_triple_quoted_template():
    assert_parse_ok(_ACTION % 'exec header C = tag_s: """\nline one\nline two\n""";')


def test_qualified_tag_type():
    assert_parse_ok("""
    package p { struct tag_s { string name; } }
    component pss_top {
        action A { exec header C = p::tag_s: "code"; }
    }
    """)


# ===========================================================================
# AST shape
# ===========================================================================

def test_target_code_block_is_built_at_all():
    """
    It was not, before this. The visitor was a bare TODO, so the construct
    parsed and vanished.
    """
    assert _exec_block(_ACTION % 'exec header C = "code";') is not None


def test_template_text_is_preserved():
    block = _exec_block(_ACTION % 'exec header C = "some code";')
    assert block.getData() == "some code"


def test_language_identifier_is_recorded():
    block = _exec_block(_ACTION % 'exec header CPP = "code";')
    assert block.getLanguage() == "CPP"


def test_file_block_records_its_filename():
    block = _exec_block(_ACTION % 'exec file "out.c" = "code";')
    assert block.getFilename() == "out.c"
    assert block.getLanguage() == ""


def test_untagged_block_has_no_tag():
    """
    Null, not an empty tag. §20.5.4.1 makes the distinction load-bearing: an
    untagged block matches nothing, *including another untagged block*, so
    "absent" and "present but empty" must not be conflated.
    """
    assert _exec_block(_ACTION % 'exec header C = "code";').getTag() is None


def test_tag_records_its_type():
    tag = _exec_block(_ACTION % 'exec header C = tag_s: "code";').getTag()
    assert tag is not None
    assert tag.getType().getElem(0).getId().getId() == "tag_s"


def test_tag_without_a_literal_has_no_literal():
    """§20.5.4: the instance is then initialized from the field defaults."""
    tag = _exec_block(_ACTION % 'exec header C = tag_s: "code";').getTag()
    assert tag.getLiteral() is None


def test_tag_literal_is_recorded():
    tag = _exec_block(
        _ACTION % 'exec header C = tag_s {.name = "n", .id = 1}: "code";').getTag()
    literal = tag.getLiteral()
    assert literal is not None
    names = [literal.getElem(i).getName().getId()
             for i in range(literal.numElems())]
    assert names == ["name", "id"]


def test_file_block_carries_its_tag():
    tag = _exec_block(_ACTION % 'exec file "out.c" = tag_s: "code";').getTag()
    assert tag is not None
    assert tag.getType().getElem(0).getId().getId() == "tag_s"


def test_template_parameters_are_not_extracted_yet():
    """
    A recorded limit, not an accident: pulling `{{expr}}` out of the template
    body needs a sub-parser over its content, which is P5-I1. The raw text is
    kept verbatim so nothing is lost in the meantime.
    """
    block = _exec_block(_ACTION % 'exec header C = "value is {{x}}";')
    assert block.numParameters() == 0
    assert block.getData() == "value is {{x}}"


# ===========================================================================
# PSS106 -- tag placement
# ===========================================================================

@pytest.mark.parametrize("kind", _TAGGABLE)
def test_tag_is_permitted_on_generation_time_kinds(kind):
    assert_no_marker(_ACTION % ('exec %s C = tag_s: "code";' % kind),
                     marker_id="PSS106")


def test_tag_is_permitted_on_exec_file():
    assert_no_marker(_ACTION % 'exec file "out.c" = tag_s: "code";',
                     marker_id="PSS106")


@pytest.mark.parametrize("kind", _UNTAGGABLE)
def test_tag_is_rejected_on_other_kinds(kind):
    """
    `body` runs once per traversal and the solve execs run during solving, so
    neither emits code a generator could deduplicate.
    """
    marker = assert_marker(_ACTION % ('exec %s C = tag_s: "code";' % kind),
                           marker_id="PSS106", severity="error")
    assert "'%s'" % kind in marker["message"]


@pytest.mark.parametrize("kind", _UNTAGGABLE)
def test_untagged_block_of_any_kind_is_accepted(kind):
    """Only the *tag* is restricted, not the target-code block itself."""
    assert_no_marker(_ACTION % ('exec %s C = "code";' % kind),
                     marker_id="PSS106")


def test_native_exec_block_is_unaffected():
    assert_no_marker(_ACTION % 'exec post_solve { }', marker_id="PSS106")


# ===========================================================================
# Tag type resolution
# ===========================================================================

def test_unknown_tag_type_is_reported():
    assert_marker(_ACTION % 'exec header C = nosuch_s: "code";',
                  marker_id="PSS002", severity="error", count=1)


def test_known_tag_type_resolves_cleanly():
    assert_no_marker(_ACTION % 'exec header C = tag_s: "code";',
                     marker_id="PSS002")


# ===========================================================================
# P3-X2 -- the `pre_body` exec kind
# ===========================================================================

def test_pre_body_exec_block_parses():
    assert_parse_ok("""
    component pss_top {
        action A {
            int x;
            exec pre_body { x = 1; }
        }
    }
    """)


def test_pre_body_is_not_an_unknown_exec_kind():
    """
    `exec_kind` is a free identifier in the grammar, so an unrecognized kind is
    caught by the builder's map rather than by a parse error. `pre_body` was
    missing from that map.
    """
    assert_no_marker("""
    component pss_top {
        action A { exec pre_body { } }
    }
    """, text="unknown exec-block kind")


def test_an_actually_unknown_exec_kind_is_still_reported():
    assert_marker("""
    component pss_top {
        action A { exec nonsense { } }
    }
    """, text="unknown exec-block kind")


# ===========================================================================
# Negative cases
# ===========================================================================

@pytest.mark.parametrize("stmt", [
    'exec header C = tag_s "code";',        # missing ':' after the tag
    'exec header C = tag_s: ;',             # missing template
    'exec header C = : "code";',            # ':' with no tag
    'exec header C = tag_s: "code"',        # missing ';'
    'exec file = tag_s: "code";',           # missing filename
])
def test_malformed_tagged_block_rejected(stmt):
    assert_parse_error(_ACTION % stmt)


def test_target_code_block_is_not_permitted_in_a_component_body():
    """
    Annex B B.8 gives `component_body_item` only the braced `exec_block`, not
    `exec_block_stmt`. Asserted so the boundary is deliberate rather than
    assumed.
    """
    assert_parse_error(_TAG + 'component C { exec header C = tag_s: "code"; }')
