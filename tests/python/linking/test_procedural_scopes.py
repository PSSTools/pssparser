"""
Procedural compound statements (symbol-resolution plan 4.1b).

A local declared in the body of a procedural `if`/`else`, `match`, `while`
or `repeat`...`while` was found, but recorded against a path that led
nowhere -- bound on paper, dead to every consumer. The statement itself was
missing from the path: it is not a symbol scope (it declares nothing), so it
was never pushed. `while` only looked right when the loop was the first
statement in its block.

Each statement is now a path step: its index in the enclosing scope, then
body `k` at index `k`. As in test_activity_scopes.py, the tests check that
every recorded path resolves, not just that the model links.
"""
import pytest

import pssparser
from pssparser import refs
from pssparser.refs import Resolution

from .test_activity_scopes import assert_links_and_binds, error_messages


def fn(body, fields="int l[2];"):
    return """
component pss_top {
    %s
    function void f(int c) {
        int q;
        %s
    }
}
""" % (fields, body)


@pytest.mark.parametrize("body", [
    "if (c > 0) { int x; x = q; }",
    "if (c > 0) q = 1; else { int x; x = q; }",
    "if (c == 1) q = 1; else if (c == 2) { int y; y = q; } else { int z; z = q; }",
    "match (c) { [1]: q = c; [2]: { int x; x = q; } default: { int y; y = q; } }",
    "while (c > 0) { int x; x = q; }",
    "repeat { int x; x = q; } while (c > 0);",
    "while (c > 0) { if (c > 1) { int x; { int y; y = x + q; } } }",
    "if (c > 0) while (c > 1) { int x; x = q; } else q = 1;",
    "if (c > 0) foreach (e : l) { int x; x = e + q; }",
    "if (c > 0) repeat (i : 2) { int x; x = i + q; }",
    "if (c > 0) if (c > 1) { int x; x = q; }",
    "match (c) { [1]: while (c > 0) { int x; x = q; } }",
    "repeat (2) { if (c > 0) { int x; x = q; } }",
    "foreach (e : l) { match (e) { [1]: { int x; x = e; } } }",
])
def test_locals_in_compound_bodies_resolve(tmp_path, body):
    assert_links_and_binds(tmp_path, fn(body))


def test_exec_block(tmp_path):
    assert_links_and_binds(tmp_path, """
component pss_top {
    int n;
    exec init_down {
        if (n > 0) { int x; x = n; } else { int y; y = n; }
    }
}
""")


def test_binds_to_the_declaration_in_its_own_branch():
    p = pssparser.Parser()
    p.parses([("t.pss", """\
component pss_top {
  function void f(int c) {
    if (c > 0) { int x; x = 1; }
    else       { int x; x = 2; }
  }
}
""")])
    p.link()
    uses = [o for o in refs.occurrences(p)
            if o.text == "x" and not o.is_declaration]
    assert [(o.line, o.resolution) for o in uses] == \
        [(3, Resolution.USER), (4, Resolution.USER)]
    assert [o.decl_location[:3] for o in uses] == [(1, 3, 22), (1, 4, 22)]


@pytest.mark.parametrize("body", [
    "if (c > 0) { int x; } else { x = 1; }",
    "if (c > 0) { int x; } q = x;",
    "match (c) { [1]: { int x; } default: { x = 1; } }",
    "while (c > 0) { int x; } q = x;",
    "repeat { int x; } while (x > 0);",
])
def test_a_body_local_is_not_visible_outside_it(body):
    assert error_messages(fn(body))
