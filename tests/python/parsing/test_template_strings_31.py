'''
Tests for triple-quoted string special elements -- PSS 3.1 §4.7.1.

Inside `"""..."""` only -- never inside `"..."` -- four kinds of special
element: mustache expressions `{{ expr }}`, control-flow directives
`{% ... %}`, block comments `{# ... #}` and line comments `{#}`.

The parser's job stops at structure and resolution.  It does **not** expand a
foreach over a solved collection: the collection's value is not known until
solve time, which is a tool's job, not a front end's.  What is owed to
consumers is the structure, the resolved references, and the byte offsets --
enough that a generator can expand without re-parsing.

Note this module delimits its PSS sources with single-quoted triple quotes,
since the construct under test is spelled with double-quoted triple quotes.
'''
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import get_symbol, parse_collect


# Keeps the owning Parser alive: AST node wrappers do not reference it, and the
# C++ nodes are freed when it is collected -- touching one then segfaults the
# interpreter with no traceback.
#
# The linked `root` must be kept too, which is a level deeper than the trap as
# usually stated.  A helper that parses, digs out a node and returns *only that
# node* drops the root on the way out and the whole linked tree goes with it.
# That reads as a flaky segfault: it survives when run standalone and dies
# under pytest, because assertion rewriting allocates enough to reuse the
# freed memory.
_LIVE_PARSERS = []
_LIVE_ROOTS = []


def _parse(pss):
    from pssparser import Parser
    p = Parser()
    _LIVE_PARSERS.append(p)
    root, markers = parse_collect(pss, parser=p)
    _LIVE_ROOTS.append(root)
    return root, markers


_ACTION = 'component pss_top { action A { %s } }'


def _exec_template(body, decls=''):
    """Parse an action holding one target exec block; return its TemplateString."""
    root, markers = _parse(_ACTION % (decls + body))
    assert markers == [], [(m.get('code'), m['message']) for m in markers]
    act = get_symbol(get_symbol(root, 'pss_top'), 'A')
    for i in range(act.numChildren()):
        c = act.getChild(i)
        if type(c).__name__ == 'ExecTargetTemplateBlock':
            return c
    raise AssertionError('no ExecTargetTemplateBlock built')


def _markers(body, decls=''):
    _, markers = _parse(_ACTION % (decls + body))
    return markers


def _codes(markers):
    return [m.get('code') for m in markers]


def _kinds(elems_owner, n, get):
    return [type(get(i)).__name__ for i in range(n)]


def _elem_kinds(t):
    return [type(t.getElem(i)).__name__ for i in range(t.numElems())]


def _body_kinds(b):
    return [type(b.getBody(i)).__name__ for i in range(b.numBody())]


def _locals(node):
    """Template-local declarations registered on a scope node."""
    return [node.getChild(i).getName().getId()
            for i in range(node.numChildren())
            if type(node.getChild(i)).__name__ == 'ProceduralStmtDataDeclaration']


# ===========================================================================
# Scanner -- delimiter recognition
# ===========================================================================

def test_mustache_is_recognized():
    t = _exec_template('exec body C = """v={{a}};""";', 'int a;').getTemplate()
    assert _elem_kinds(t) == ['TemplateText', 'TemplateExpr', 'TemplateText']


def test_block_comment_is_recognized_and_retained():
    """Evaluation drops comments (§4.7.1.3); *parsing* must not, or a
    formatter loses the user's comments.  Dropping is the renderer's job."""
    t = _exec_template('exec body C = """{# hello #}""";').getTemplate()
    assert _elem_kinds(t) == ['TemplateComment']
    c = t.getElem(0)
    assert c.getText() == ' hello '
    assert c.getIs_line() is False


def test_line_comment_is_recognized():
    t = _exec_template(
        'exec body C = """{#} to end of line\nx""";').getTemplate()
    assert _elem_kinds(t) == ['TemplateComment', 'TemplateText']
    assert t.getElem(0).getIs_line() is True


def test_line_comment_beats_block_comment():
    """`{#}` must be tested before `{#}`'s prefix `{#`.

    Get the order wrong and every line comment reads as an unterminated block
    comment -- an error on entirely valid input.
    """
    assert _codes(_markers('exec body C = """{#} a line comment""";')) == []


def test_block_comment_content_is_not_scanned():
    """§4.7.1.3: mustaches and directives inside a comment are not
    interpreted.  `{{not_a_mustache}}` here must not be parsed as one, and
    must not report an unknown identifier."""
    t = _exec_template(
        'exec body C = """{# {{nope}} {% if (bad) %} #}""";').getTemplate()
    assert _elem_kinds(t) == ['TemplateComment']


def test_closing_delimiter_inside_a_string_literal_is_skipped():
    """`{{ m["}}"] }}` is legal PSS: the `}}` inside the subscript is part of
    a string literal, not the end of the mustache."""
    t = _exec_template(
        'exec body C = """{{ m["}}"] }}""";',
        'map<string, int> m;').getTemplate()
    assert _elem_kinds(t) == ['TemplateExpr']


def test_escaped_quote_inside_a_nested_string_literal():
    """A triple-quoted string has no escapes, but an ordinary `"..."` nested
    *inside* a mustache is ordinary PSS, where `\\"` is one."""
    t = _exec_template('exec body C = """{{ "a\\"b" }}""";').getTemplate()
    assert _elem_kinds(t) == ['TemplateExpr']


def test_bare_closers_in_text_are_literal():
    """Only the *opening* delimiter is special.

    C and C++ produce `}}` in closing position constantly and none of it is
    affected.  A template with no opening delimiter has no specials at all.
    """
    blk = _exec_template(
        'exec body C = """if (x) { if (y) { z(); }}""";')
    assert blk.getTemplate() is None


# ===========================================================================
# Scanner -- error cases
# ===========================================================================

def test_unterminated_mustache_is_pss108():
    m = _markers('exec body C = """x {{a""";')
    assert _codes(m) == ['PSS108']


def test_unterminated_directive_is_pss110():
    m = _markers('exec body C = """{% if (a) """;', 'int a;')
    assert _codes(m) == ['PSS110']


def test_unterminated_block_comment_is_pss110():
    m = _markers('exec body C = """{# never closed""";')
    assert _codes(m) == ['PSS110']


def test_block_close_with_no_open_block_is_pss111():
    m = _markers('exec body C = """{%%}""";')
    assert _codes(m) == ['PSS111']
    assert 'no open block' in m[0]['message']


def test_else_with_no_preceding_if_is_pss111():
    m = _markers('exec body C = """{% else %}""";')
    assert _codes(m) == ['PSS111']


def test_unclosed_block_at_end_of_string_is_pss110():
    m = _markers('exec body C = """{% if (a) %}body""";', 'int a;')
    assert _codes(m) == ['PSS110']
    assert 'unclosed template block' in m[0]['message']


# ===========================================================================
# Structure
# ===========================================================================

def test_if_else_if_else_stays_flat():
    """One TemplateIf with three clauses, not a tree of nested ifs.

    The source is a flat directive sequence; making it a tree would be an
    invention the formatter would then have to undo.
    """
    t = _exec_template(
        'exec body C = """{% if (a>0) %}p{% else if (a==0) %}q{% else %}r{%%}""";',
        'int a;').getTemplate()
    assert _elem_kinds(t) == ['TemplateIf']

    node = t.getElem(0)
    assert node.numClauses() == 3
    assert node.getClause(0).getCond() is not None
    assert node.getClause(1).getCond() is not None
    assert node.getClause(2).getCond() is None, "the `else` arm has no guard"

    assert _body_kinds(node.getClause(0)) == ['TemplateText']
    assert _body_kinds(node.getClause(2)) == ['TemplateText']


def test_foreach_nests_inside_if():
    t = _exec_template(
        'exec body C = """{% if (a>0) %}{% foreach (arr) %}x{%%}{%%}""";',
        'int a; int arr[4];').getTemplate()
    node = t.getElem(0)
    assert type(node).__name__ == 'TemplateIf'
    inner = node.getClause(0).getBody(0)
    assert type(inner).__name__ == 'TemplateForeach'
    assert _body_kinds(inner) == ['TemplateText']


def test_foreach_iterator_and_index_are_captured():
    t = _exec_template(
        'exec body C = """{% foreach (e : arr) %}x{%%}""";',
        'int arr[4];').getTemplate()
    fe = t.getElem(0)
    assert fe.getIt() is not None and fe.getIt().getId() == 'e'


def test_repeat_index_is_captured():
    t = _exec_template(
        'exec body C = """{% repeat (i : 4) %}x{%%}""";').getTemplate()
    rp = t.getElem(0)
    assert type(rp).__name__ == 'TemplateRepeat'
    assert rp.getIdx() is not None and rp.getIdx().getId() == 'i'


def test_variable_declaration_and_assignment():
    t = _exec_template(
        'exec body C = """{% int i = 0; %}{% i = 1; %}""";').getTemplate()
    assert _elem_kinds(t) == ['TemplateVarDecl', 'TemplateAssign']
    assert t.getElem(0).getDecl(0).getName().getId() == 'i'
    assert t.getElem(1).getLhs().getId() == 'i'


def test_raw_is_byte_identical_to_the_source():
    """`raw` is kept verbatim so a formatter that cannot render a template
    structurally can still copy it."""
    blk = _exec_template('exec body C = """  a{{b}}c  """;', 'int b;')
    t = blk.getTemplate()
    assert t.getRaw() == '  a{{b}}c  '
    assert t.getRaw() == blk.getData(), "raw and data must not drift"


def test_offsets_slice_raw_back_to_the_original_text():
    """Per-element offset/extent must index `raw` exactly -- a renderer that
    wants to splice needs them, and slicing is what catches an off-by-one."""
    blk = _exec_template('exec body C = """a{{b}}c""";', 'int b;')
    t = blk.getTemplate()
    raw = t.getRaw()
    slices = [raw[t.getElem(i).getOffset():
                  t.getElem(i).getOffset() + t.getElem(i).getExtent()]
              for i in range(t.numElems())]
    assert slices == ['a', '{{b}}', 'c']
    assert ''.join(slices) == raw, "elements must tile `raw` with no gaps"


# ===========================================================================
# The negative that matters
# ===========================================================================

def test_string_without_specials_is_a_plain_exprstring():
    """A triple-quoted string with no special elements gets no TemplateString.

    This keeps the common case free of extra nodes and makes "has specials" a
    type test rather than a list-length test.  Asserting the *negative* is the
    point: the positive assertion passes either way.
    """
    blk = _exec_template('exec body C = """ordinary target code""";')
    assert blk.getTemplate() is None


def test_double_quoted_string_is_never_a_template():
    """§4.7.1 admits special elements inside `\"\"\"...\"\"\"` only."""
    blk = _exec_template('exec body C = "value is {{x}}";')
    assert blk.getTemplate() is None
    assert blk.getData() == 'value is {{x}}'


def test_field_initializer_template_is_an_exprtemplatestring():
    """ExprTemplateString subclasses ExprString, so every existing consumer
    that dynamic_casts to ExprString or calls getValue() keeps working and
    sees the raw text.  Only consumers that care look for the subclass."""
    root, markers = _parse(
        'component pss_top { action A { int a; string s = """v={{a}}"""; } }')
    assert markers == []
    act = get_symbol(get_symbol(root, 'pss_top'), 'A')
    fields = [act.getChild(i) for i in range(act.numChildren())
              if type(act.getChild(i)).__name__ == 'Field']
    s = [f for f in fields if f.getName().getId() == 's'][0]
    init = s.getInit()
    assert type(init).__name__ == 'ExprTemplateString'
    assert init.getValue() == 'v={{a}}', "getValue() stays the raw text"
    assert init.getTemplate() is not None


# ===========================================================================
# Locations -- the §6 off-by-one
# ===========================================================================

def test_column_offset_applies_only_on_the_first_line():
    """An ANTLR position inside a fragment maps to
    `(base_line + l - 1, l == 1 ? base_col + c - 1 : c)`.

    The column offset applies **only** on the fragment's first line; from
    line 2 on, the fragment's own column already is the file column.  Getting
    this wrong is invisible until a template spans many lines.
    """
    src = 'component pss_top { action A { int a;\n  exec body C = """{{a}}\n{{a}}""";\n} }'
    root, markers = _parse(src)
    assert markers == []
    act = get_symbol(get_symbol(root, 'pss_top'), 'A')
    blk = [act.getChild(i) for i in range(act.numChildren())
           if type(act.getChild(i)).__name__ == 'ExecTargetTemplateBlock'][0]
    t = blk.getTemplate()
    exprs = [t.getElem(i) for i in range(t.numElems())
             if type(t.getElem(i)).__name__ == 'TemplateExpr']
    assert len(exprs) == 2

    first, second = exprs[0].getLocation(), exprs[1].getLocation()
    # `  exec body C = """` is 19 characters, so the first `{{` is at column 20.
    assert (first.lineno, first.linepos) == (2, 20)
    # The second is at the very start of line 3 -- no base column added.
    assert (second.lineno, second.linepos) == (3, 1)


def test_error_deep_in_a_template_reports_the_right_line():
    # 39 lines of filler, so the bad mustache sits on template line 40. The
    # template opens on file line 1, so file line 40 too.
    body = '\n'.join(['line%d' % i for i in range(1, 40)])
    m = _markers('exec body C = """%s\n{{ 1 + }}""";' % body)
    assert _codes(m) == ['PSS109']
    assert m[0]['line'] == 40, m[0]


# ===========================================================================
# Compatibility -- D3, a deliberate source-level break
# ===========================================================================

def test_double_brace_array_initializer_is_an_error():
    """`int m[2][2] = {{1,2},{3,4}};` in a target template is an ERROR.

    This is deliberate (template-strings-project.md §5.1, decision D3).  PSS
    3.1 makes `{{` open a mustache inside a triple-quoted string and provides
    no escape mechanism, so target code containing two adjacent open braces
    now fails.  Jinja2 fails on this exact input the same way, and the fix is
    the same: separate the braces.

    Do NOT "repair" this test by making an unparseable mustache fall back to
    literal text -- that would let a genuinely malformed `{{ x + }}` through
    silently, which is worse than a loud failure on valid-looking C.
    """
    m = _markers('exec body C = """int m[2][2] = {{1,2},{3,4}};""";')
    assert _codes(m) == ['PSS109']


def test_every_double_brace_diagnostic_carries_the_workaround_hint():
    """D3.3: a C programmer who wrote a legal array initializer and is told
    only "syntax error in mustache expression" has learned nothing.

    The fragment-syntax-error case is the one most likely to regress, by
    forwarding ANTLR's raw message instead of wrapping it.
    """
    cases = [
        'exec body C = """x {{a""";',                       # PSS108, unterminated
        'exec body C = """{{}}""";',                        # empty
        'exec body C = """{{ int x; }}""";',                # not an expression
        'exec body C = """{{ 1 + }}""";',                   # ANTLR fragment error
        'exec body C = """int m[2][2] = {{1,2},{3,4}};""";',  # the real-world case
    ]
    for src in cases:
        m = _markers(src)
        assert m, 'no diagnostic for %r' % src
        assert "'{ {'" in m[0]['message'], \
            'hint missing from %r -> %r' % (src, m[0]['message'])


def test_the_sanctioned_spelling_parses_and_round_trips():
    """`{ {` is a *spelling*, not a feature: a lone `{` is already ordinary
    text, so it needs no scanner support, no grammar and no flag.  That is
    exactly what makes it conformant where an invented escape would not be --
    any other PSS 3.1 tool reads it the same way."""
    text = 'int m[2][2] = { {1,2},{3,4} };'
    blk = _exec_template('exec body C = """%s""";' % text)
    assert blk.getTemplate() is None, 'no specials -- `{ {` is ordinary text'
    assert blk.getData() == text, 'must round-trip byte for byte'


# ===========================================================================
# Compatibility -- O5, the phantom escape
# ===========================================================================

def test_backslash_before_closing_quotes_ends_the_string():
    """§4.7: a triple-quoted string "may contain any ASCII character...  There
    is no escape character", the sole exclusion being three consecutive double
    quotes.

    The lexer used to carry an `EscapedTripleQuote` fragment, so `\\` followed
    by `\"\"\"` was swallowed and scanning continued past the intended end of the
    string.  That was a non-conformant extension; it is gone (O5), and the
    string now ends where the standard says it does, with a trailing
    backslash as ordinary content.
    """
    blk = _exec_template('exec body C = """a\\""";')
    assert blk.getData() == 'a\\'


# ===========================================================================
# P5-G1 -- `exec file` filenames
# ===========================================================================

def test_exec_file_accepts_a_triple_quoted_filename():
    """Annex B gives `filename_string ::= string_literal`; ours was
    `DOUBLE_QUOTED_STRING`, so §20.5.3's per-instance generated filename could
    not be written at all."""
    blk = _exec_template('exec file """out.c""" = "code";')
    assert blk.getFilename() == 'out.c'


def test_exec_file_filename_can_hold_a_mustache():
    blk = _exec_template('exec file """out_{{id}}.c""" = "code";', 'int id;')
    assert blk.getFilename() == 'out_{{id}}.c'
    assert blk.getFilename_template() is not None


def test_exec_file_plain_filename_still_works():
    blk = _exec_template('exec file "out.c" = "code";')
    assert blk.getFilename() == 'out.c'
    assert blk.getFilename_template() is None


# ===========================================================================
# Resolution -- template-local scopes
# ===========================================================================

def test_mustache_resolves_an_action_field():
    """Assert the *resolved target*, not merely that no marker was emitted.

    A missing TaskResolveRefs visitor produces silence, and a
    marker-absence assertion passes right through it.
    """
    t = _exec_template('exec body C = """{{a}}""";', 'int a;').getTemplate()
    expr = t.getElem(0).getExpr()
    assert type(expr).__name__ == 'ExprRefPathContext'
    assert expr.getTarget() is not None, 'reference was never resolved'


def test_foreach_iterator_is_visible_inside_its_block():
    assert _codes(_markers(
        'exec body C = """{% foreach (e : arr) %}{{e}}{%%}""";',
        'int arr[4];')) == []


def test_foreach_iterator_is_not_visible_after_the_block_closes():
    m = _markers('exec body C = """{% foreach (e : arr) %}x{%%}{{e}}""";',
                 'int arr[4];')
    assert _codes(m) == ['PSS002'], [x['message'] for x in m]


def test_repeat_index_is_visible_inside_its_block():
    assert _codes(_markers(
        'exec body C = """{% repeat (i : 4) %}{{i}}{%%}""";')) == []


def test_declared_template_variable_is_visible_to_later_elements():
    assert _codes(_markers(
        'exec body C = """{% int x = 1; %}{{x}}""";')) == []


@pytest.mark.xfail(reason="no declaration-order checking anywhere in the linker "
                          "-- see known-issues P5-X1", strict=True)
def test_declared_variable_is_not_visible_before_its_declaration():
    """§4.7.1.2 says a template variable can be referenced *after* its
    declaration directive.  We resolve it before, too.

    Not a template-specific defect: template locals are registered while the
    AST is built, and resolution runs afterwards over the finished symtab, so
    position within the template is not information the resolver has.  The
    linker order-checks declarations in **no** context today -- §4.7.2
    Example1, a `static const string` whose initializer mustache names a
    constant declared later in the same scope, is the same gap.  Closing it is
    a new linker capability, not a template feature.
    """
    m = _markers('exec body C = """{{x}}{% int x = 1; %}""";')
    assert _codes(m) == ['PSS002']


def test_variable_declared_in_a_block_is_not_visible_after_it():
    m = _markers('exec body C = """{% if (a) %}{% int y = 1; %}{%%}{{y}}""";',
                 'int a;')
    assert _codes(m) == ['PSS002']


def test_foreach_collection_resolves_in_the_outer_scope():
    """The collection must not see the loop variables this block introduces --
    `foreach (e : e)` is not a self-reference, it is an unknown identifier."""
    m = _markers('exec body C = """{% foreach (e : e) %}x{%%}""";')
    assert _codes(m) == ['PSS002']


def test_template_local_shadows_an_enclosing_field():
    """A `{% int a; %}` wins over an action field of the same name inside the
    template -- which is also what makes the PSS112 distinction meaningful."""
    assert _codes(_markers(
        'exec body C = """{% int a = 1; %}{% a = 2; %}""";', 'int a;')) == []


# ===========================================================================
# PSS112 -- the assignment restriction
# ===========================================================================

def test_assignment_to_a_template_local_is_allowed():
    assert _codes(_markers(
        'exec body C = """{% int i = 0; %}{% i = 1; %}""";')) == []


def test_assignment_to_an_action_attribute_is_pss112():
    """§4.7.1.2: `{% x = expr; %}` may only target a variable previously
    declared *within the same triple-quoted string*.

    Nothing in the syntax distinguishes this from a legal template-local
    assignment; the only way to tell is which symtab the name resolved
    through, which is why template locals must be real symbols in a real
    scope rather than a side table.
    """
    m = _markers('exec body C = """{% a = 1; %}""";', 'int a;')
    assert _codes(m) == ['PSS112'], [x['message'] for x in m]
    assert "'a'" in m[0]['message']


def test_assignment_to_an_unknown_name_is_pss002_not_pss112():
    """One root cause, one diagnostic: an undeclared name is an unknown
    identifier, not a misplaced assignment target."""
    m = _markers('exec body C = """{% nope = 1; %}""";')
    assert _codes(m) == ['PSS002'], [x['message'] for x in m]


def test_assignment_to_a_foreach_iterator_is_allowed():
    """The iterator is declared within the template, so it satisfies §4.7.1.2
    even though it was not written with an explicit declaration directive."""
    assert _codes(_markers(
        'exec body C = """{% foreach (e : arr) %}{% e = 1; %}{%%}""";',
        'int arr[4];')) == []


# ===========================================================================
# Diagnostics are reported once
# ===========================================================================

def test_a_bad_reference_in_a_template_is_reported_once():
    """TemplateString and TemplateElem derive from SymbolScope, so the symbol
    tree builder would otherwise hoist them into the enclosing type's scope --
    giving the same expression three parents and reporting every diagnostic
    inside a template three times over."""
    m = _markers('exec body C = """{{nope}}""";')
    assert len(m) == 1, [x['message'] for x in m]


def test_each_bad_reference_is_reported_once():
    m = _markers('exec body C = """{{nope}} {{nope2}}""";')
    assert len(m) == 2, [x['message'] for x in m]


# ===========================================================================
# Specialization -- TaskCopyAst
# ===========================================================================

def test_template_survives_specialization_of_a_parameterized_type():
    """`visitExecTargetTemplateBlock` in TaskCopyAst was an empty stub, so
    specializing a parameterized type dropped the target code entirely.

    That was already a defect before templates existed; it became a worse one
    once the block stopped being a leaf.  A template referencing the type
    parameter is the case that exercises both the block copy and the element
    walk underneath it.
    """
    root, markers = _parse('''
        package p {
            struct S <int W = 8> {
                exec body C = """w={{W}}{% if (W > 4) %}wide{%%}""";
            }
            struct U { S<16> s16; }
        }
    ''')
    assert markers == [], [(m.get('code'), m['message']) for m in markers]

    found = []

    def walk(n, depth=0):
        if depth > 8:
            return
        try:
            n_children = n.numChildren()
        except Exception:
            return
        for i in range(n_children):
            c = n.getChild(i)
            if type(c).__name__ == 'ExecTargetTemplateBlock':
                found.append(c)
            walk(c, depth + 1)

    walk(get_symbol(root, 'p'))
    assert found, 'no exec block reachable'
    for blk in found:
        t = blk.getTemplate()
        assert t is not None, 'specialized copy lost its template'
        assert t.getRaw() == blk.getData()
        kinds = [type(t.getElem(i)).__name__ for i in range(t.numElems())]
        assert kinds == ['TemplateText', 'TemplateExpr', 'TemplateIf']


# ===========================================================================
# Scalar type -- PSS113 (§4.7.1.1)
# ===========================================================================

def test_aggregate_mustache_is_pss113():
    """§4.7.1.1: "The expression type shall be a scalar type."  There is no
    defined text for a list literal."""
    m = _markers('exec body C = """v = {{ {1,2,3} }};""";')
    assert _codes(m) == ['PSS113'], [x['message'] for x in m]


def test_scalar_mustache_is_accepted():
    for decl, expr in [('int a;', 'a'),
                       ('string s;', 's'),
                       ('bool b;', 'b'),
                       ('int a;', 'a + 1')]:
        m = _markers('exec body C = """{{%s}}""";' % expr, decl)
        assert m == [], (decl, expr, [x['message'] for x in m])


def test_unclassifiable_mustache_stays_silent():
    """PSS113 inherits TaskExprTypeCat's gaps (P3-X6c): a member path is not
    classified, and an unknown category is never reported.  Asserting the
    silence pins the posture -- the alternative, guessing, produces false
    errors on perfectly good code."""
    root, markers = _parse('''
        component pss_top {
            struct S { int b; }
            action A {
                rand S s1;
                exec body C = """{{s1.b}}""";
            }
        }
    ''')
    assert markers == [], [(m.get('code'), m['message']) for m in markers]


def test_pss113_is_not_raised_for_a_directive_expression():
    """The scalar rule is §4.7.1.1's, about mustache *substitution*.  A foreach
    directive iterates a collection by definition, so applying the same rule
    there would reject every legal foreach."""
    m = _markers('exec body C = """{% foreach (arr) %}x{%%}""";', 'rand int arr[4];')
    assert _codes(m) == [], [x['message'] for x in m]


# ===========================================================================
# Purity -- PSS114 (§4.7.1.1)
# ===========================================================================

_PURE_PKG = '''
package p {
    function int f(int a);
    pure function int g(int a);
    pure function int h(int a) { return a; }
    %s
}
'''


def _pkg_markers(body):
    _, markers = _parse(_PURE_PKG % body)
    return markers


def test_non_pure_call_in_a_mustache_is_pss114():
    m = _pkg_markers('component c { action A { exec body C = """{{f(1)}}"""; } }')
    assert _codes(m) == ['PSS114'], [x['message'] for x in m]
    assert "'f'" in m[0]['message']


def test_pure_call_in_a_mustache_is_accepted():
    """Both declaration forms carry the qualifier: a bare `pure function`
    prototype and a `pure function` with a body.  `is_pure` was never set from
    either before this check needed it."""
    for call in ['g(1)', 'h(2)']:
        m = _pkg_markers(
            'component c { action A { exec body C = """{{%s}}"""; } }' % call)
        assert m == [], (call, [x['message'] for x in m])


def test_non_pure_call_in_a_directive_is_pss114():
    m = _pkg_markers(
        'component c { action A { exec body C = """{% if (f(1) > 0) %}x{%%}"""; } }')
    assert _codes(m) == ['PSS114'], [x['message'] for x in m]


def test_non_pure_call_outside_a_template_is_not_reported():
    """The rule is about templates.  The same call in an ordinary initializer
    is unremarkable, and a check that fired there would be reporting on most
    of the language."""
    m = _pkg_markers('component c { action A { int x = f(1); } }')
    assert _codes(m) == [], [x['message'] for x in m]


# ===========================================================================
# is_const (§4.7) and PSS115
# ===========================================================================

def _is_const(pss, path=('p', 'c', 'A')):
    root, markers = _parse(pss)
    assert markers == [], [(m.get('code'), m['message']) for m in markers]
    n = root
    for seg in path:
        n = get_symbol(n, seg)
        assert n is not None, seg
    for i in range(n.numChildren()):
        c = n.getChild(i)
        if type(c).__name__ == 'ExecTargetTemplateBlock':
            return c.getTemplate().getIs_const()
    raise AssertionError('no ExecTargetTemplateBlock built')


_CONST_PKG = '''
package p {
    static const int K = 4;
    enum e_t { E_A, E_B }
    component c {
        int sz;
        action A { exec body C = """%s"""; }
    }
}
'''


def test_template_over_constants_is_constant():
    assert _is_const(_CONST_PKG % '{{K}} {{E_A}}') is True


def test_template_with_no_specials_at_all_is_constant():
    """Vacuously: there is nothing non-constant in it.  The value matters
    because `is_const` is what PSS115 consults, and a plain-text template used
    as a `const` initializer must not be rejected."""
    assert _is_const(_CONST_PKG % 'plain {# comment #} text') is True


def test_template_referencing_a_field_is_not_constant():
    assert _is_const(_CONST_PKG % '{{sz}}') is False


def test_template_local_initialized_from_a_constant_is_constant():
    assert _is_const(_CONST_PKG % '{% int x = K; %}{{x}}') is True


def test_template_local_assigned_from_a_field_is_not_constant():
    """The local itself carries the verdict forward: `x` is non-constant from
    the assignment on, so `{{x}}` afterwards is non-constant too."""
    assert _is_const(_CONST_PKG % '{% int x; %}{% x = sz; %}{{x}}') is False


def test_loop_variable_takes_the_collections_constness():
    assert _is_const('''
        package p {
            component c {
                action A {
                    rand int arr[4];
                    exec body C = """{% foreach (a: arr) %}{{a}}{%%}""";
                }
            }
        }
    ''') is False


def test_a_call_is_never_constant():
    """Even a `pure` one.  Purity says the call has no side effects, not that
    this front end can evaluate the body -- and it cannot."""
    assert _is_const('''
        package p {
            pure function int g(int a);
            component c { action A { exec body C = """{{g(1)}}"""; } }
        }
    ''') is False


def test_non_constant_template_in_a_const_field_is_pss115():
    _, m = _parse('''
        package p {
            component c {
                int sz;
                static const string S = """n={{sz}}""";
            }
        }
    ''')
    assert _codes(m) == ['PSS115'], [x['message'] for x in m]


def test_constant_template_in_a_const_field_is_accepted():
    _, m = _parse('''
        package p {
            static const int K = 2;
            component c { static const string S = """n={{K}}"""; }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]


def test_non_constant_template_in_an_annotation_is_pss115():
    """Not PSS102: an annotation initializer holding a template answers the
    constant question through `is_const`, and the generic walker would see the
    references *inside* the mustaches and call a constant template
    non-constant."""
    _, m = _parse('''
        package p {
            annotation desc_s { string text; }
            component c {
                int sz;
                @desc_s {.text = """n={{sz}}"""}
                action A { }
            }
        }
    ''')
    assert _codes(m) == ['PSS115'], [x['message'] for x in m]


def test_constant_template_in_an_annotation_is_accepted():
    _, m = _parse('''
        package p {
            annotation desc_s { string text; }
            static const int K = 1;
            component c {
                @desc_s {.text = """n={{K}}"""}
                action A { }
            }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]


def test_the_same_template_is_legal_in_an_exec_body():
    """PSS115 is raised at the point of *use*.  The template text rejected as a
    `const` initializer above is unremarkable here, which is why the check
    cannot live on the template."""
    _, m = _parse('''
        package p {
            component c {
                int sz;
                action A { exec body C = """n={{sz}}"""; }
            }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]


def test_const_field_declaration_records_the_const_attribute():
    """`visitConst_field_declaration` cleared `m_fields` *before* stamping the
    attribute, so `const int K = 4;` was recorded with no attributes at all.
    Nothing depended on it until `is_const` did, at which point every constant
    reference looked non-constant.

    Asserted through behaviour rather than through `attr`: it is the verdict
    that matters, and a test on the flag alone would pass with the flag set on
    the wrong field.
    """
    assert _is_const('''
        package p {
            const int K = 4;
            component c { action A { exec body C = """{{K}}"""; } }
        }
    ''') is True


# ===========================================================================
# Regression -- the LRM examples (§4.7.2, §20.5.3, §20.6.2)
#
# Transcribed verbatim from PSS 3.1 Draft 22 2026.08.18, wrapped in a package
# or component only where the example fragment needs a home.  A green suite is
# not a conformance oracle, but these are the closest thing this feature gets.
# ===========================================================================

def test_lrm_example1_static_initialization():
    """§4.7.2 Example1.  C3's forward reference to C4 is illegal per the LRM
    and is *not* reported: the linker order-checks constant initializers in no
    context (known issue P5-X1), so only the legal part is asserted here."""
    _, m = _parse('''
        package p {
            static const int C1 = 2;
            static const string C2 = """C1={{C1}}""";
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]


def test_lrm_example2_procedural_context():
    """§4.7.2 Example2 -- a template in a procedural context, over a procedural
    local.  Note the template is *not* constant: `a` is a run-time variable."""
    _, m = _parse('''
        package p {
            function void f1(string val);
            function void f2() {
                int a = 5;
                string v = """{% repeat (a) %}{{a}}{%%}""";
                a = 6;
                f1("""a={{a}}""");
            }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]


def test_lrm_example3_embedded_comments():
    """§4.7.2 Example3.  The mustache inside `{#}` is comment text and must not
    be expanded -- or resolved: `trans_size` appears in both a live mustache
    and a commented one."""
    root, m = _parse('''
        enum op_mode_e {rx,tx,copy}
        component transactor {
            list <op_mode_e> op_mode_l;
            exec init_up {
                op_mode_l = {rx, tx};
            }
            action read_a {
                rand op_mode_e opmode;
                rand int trans_size;
                constraint opmode in comp.op_mode_l;
                exec declaration C = """
//This comment will appear in the target code.
//{{opmode}} - Solved value will appear in the target code.
{#
This comment block will not appear in target code.
static void transactor_init_rx_init();
static void transactor_init_tx_init();
static void transactor_init_copy_init();
#}
static void transactor_init_{{opmode}}_init();
{#} const int trans_size = {{trans_size}};
static int trans_size = {{trans_size}};
""";
            }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]

    act = get_symbol(get_symbol(root, 'transactor'), 'read_a')
    blk = None
    for i in range(act.numChildren()):
        c = act.getChild(i)
        if type(c).__name__ == 'ExecTargetTemplateBlock':
            blk = c
    assert blk is not None
    t = blk.getTemplate()
    kinds = [type(t.getElem(i)).__name__ for i in range(t.numElems())]
    # Three live mustaches: two `{{opmode}}` and the final `{{trans_size}}`.
    # The one inside `{#} ...` is comment text and produces no TemplateExpr.
    assert kinds.count('TemplateExpr') == 3, kinds
    assert kinds.count('TemplateComment') == 2, kinds


def test_lrm_example301_mustache_filename():
    """§20.5.3 Example301 -- special elements in an `exec file` *filename*.
    The filename is deliberately allowed to be non-constant: that is how one
    action type writes to per-traversal files."""
    root, m = _parse('''
        component pss_top {
            action A {
                rand bit[4] fileid;
                rand bit[4] data;
                exec file """datafile_{{fileid}}""" = """data: {{data}}""";
            }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]

    act = get_symbol(get_symbol(root, 'pss_top'), 'A')
    blk = None
    for i in range(act.numChildren()):
        c = act.getChild(i)
        if type(c).__name__ == 'ExecTargetTemplateBlock':
            blk = c
    assert blk is not None
    assert blk.getFilename_template() is not None
    assert blk.getFilename_template().getIs_const() is False


def test_lrm_example302_referencing_pss_variables():
    """§20.5.3 Example302 -- including `{{s1.b}}` and `{{a+s1.b}}`, the member
    paths PSS113 deliberately cannot classify."""
    _, m = _parse('''
        component top {
            struct S {
                rand int b;
            }
            action A {
                rand int a;
                rand S s1;
                exec body C = """
printf("a={{a}} s1.b={{s1.b}} a+b={{a+s1.b}}\\n");
""";
            }
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]


def test_lrm_example309_target_template_function():
    """§20.6.2 Example309 -- mustaches over the *function parameters*, which
    resolve through the prototype's own scope (P5-C2)."""
    root, m = _parse('''
        package thread_ops_asm_pkg {
            target ASM function void do_stw(bit[32] val, bit[32] vaddr) = """
loadi RA {{val}}
store RA {{vaddr}}
""";
        }
    ''')
    assert m == [], [(x.get('code'), x['message']) for x in m]

    # The node lives under the function's own SymbolFunctionScope, not
    # directly under the package.
    fn_scope = get_symbol(get_symbol(root, 'thread_ops_asm_pkg'), 'do_stw')
    assert fn_scope is not None
    fn = None
    for i in range(fn_scope.numChildren()):
        c = fn_scope.getChild(i)
        if type(c).__name__ == 'TargetTemplateFunction':
            fn = c
    assert fn is not None
    t = fn.getTemplate()
    assert t is not None
    kinds = [type(t.getElem(i)).__name__ for i in range(t.numElems())]
    assert kinds.count('TemplateExpr') == 2, kinds
    # A parameter is not a constant, so neither is the template.
    assert t.getIs_const() is False
