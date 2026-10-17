"""
The `foreach` iterator variable takes the collection's element type.

The AST builder creates it untyped -- at parse time the collection is only an
unresolved path -- so member access through the iterator resolved nothing.
Where the loop sat in its enclosing block also decided whether the iterator
resolved at all, because the loop's ref-path index was read from the wrong
field.
"""
from ..test_helpers import assert_parse_ok


def test_iterator_reaches_struct_members():
    root = assert_parse_ok(
        """
        package t {
            struct S { int a; }
            function void f(list<S> l) { foreach (e : l) { e.a = 1; } }
        }
        """
    )
    assert root is not None


def test_iterator_over_a_local_collection():
    root = assert_parse_ok(
        """
        package t {
            struct S { int a; }
            function void f() { list<S> l; foreach (e : l) { e.a = 1; } }
        }
        """
    )
    assert root is not None


def test_iterator_reaches_component_functions_through_a_ref():
    root = assert_parse_ok(
        """
        package t {
            pure component b_c { function void gh(); }
            function void f(list<ref b_c> l) { foreach (e : l) { e.gh(); } }
        }
        """
    )
    assert root is not None


def test_loop_position_in_the_block_does_not_matter():
    root = assert_parse_ok(
        """
        package t {
            struct S { int a; }
            function void first(list<S> l) {
                foreach (e : l) { e.a = 1; }
            }
            function void second(list<S> l) {
                int q;
                foreach (e : l) { e.a = 1; }
            }
            function void third(list<S> l) {
                int q;
                int r;
                foreach (e : l) { e.a = 1; }
            }
        }
        """
    )
    assert root is not None


def test_iterator_over_an_array():
    root = assert_parse_ok(
        """
        package t {
            struct S { int a; }
            function void f(array<S, 4> l) { foreach (e : l) { e.a = 1; } }
        }
        """
    )
    assert root is not None
