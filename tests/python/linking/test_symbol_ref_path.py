"""``SymbolRefPath.path`` -- the resolved target of a type reference.

The path is a ``list<SymbolRefPathElem>``, and ``SymbolRefPathElem`` is a
by-value struct.  That combination is the only one of its kind in the schema,
and the code generator had no case for it: it emitted the ``path`` property
unconditionally and then dispatched on the element type, so the property
existed and every helper it calls (``numPath``, ``getPath``) did not.

The failure was an ``AttributeError`` at the moment of first use and invisible
until then -- the attribute is there right up until you call it -- which is
why this is asserted rather than left to a consumer to discover.
"""

import pytest

from pssparser import Parser
from pssparser.utils import SymbolScopeUtil


@pytest.fixture
def linked():
    """A linked model, kept alive for the duration of a test.

    The Parser and the root it returns own everything reachable from them, so
    a fixture that returned only the inner node would let them be collected
    and hand the test a dangling pointer -- a segfault, not an exception.
    """
    p = Parser()
    p.parses([("t.pss", """package p {
    struct s_t { int a; }
    component C {
        s_t f;
    }
}
""")])
    root = p.link()
    return p, root


@pytest.fixture
def resolved_target(linked):
    """The SymbolRefPath a field's type reference resolves to."""
    _, root = linked
    comp = SymbolScopeUtil(root).getQname("p::C")

    for child in comp.getChildren():
        if type(child).__name__ == "Field":
            target = child.getType().getType_id().getTarget()
            assert target is not None, "the reference should be resolved"
            return target

    pytest.fail("no field found on p::C")


def test_the_path_reports_its_length(resolved_target):
    assert resolved_target.numPath() == 2


def test_the_path_iterates(resolved_target):
    elems = list(resolved_target.path())
    assert len(elems) == 2
    for elem in elems:
        # Reaching kind and idx is the point: it proves the element arrived as
        # a wrapped struct rather than as an opaque handle.
        assert elem.idx >= 0
        assert int(elem.kind) >= 0


def test_the_path_is_indexable(resolved_target):
    """`path()` is a ListUtil iterator, not a sequence, so the per-element
    accessor is the way to reach one element -- and it must agree."""
    first = resolved_target.getPath(0)
    from_iter = list(resolved_target.path())[0]
    assert (int(first.kind), first.idx) == (int(from_iter.kind), from_iter.idx)


def test_the_list_accessor_agrees_with_the_iterator(resolved_target):
    as_list = [(int(e.kind), e.idx) for e in resolved_target.getPathList()]
    as_iter = [(int(e.kind), e.idx) for e in resolved_target.path()]
    assert as_list == as_iter


def test_elements_are_copies(resolved_target):
    """By value, so a returned element does not alias the vector.

    It stays valid if the vector reallocates -- which is what makes the
    no-ObjFactory shortcut in the generator correct rather than merely
    shorter.
    """
    first = resolved_target.getPath(0)
    again = resolved_target.getPath(0)
    assert first is not again
    assert (int(first.kind), first.idx) == (int(again.kind), again.idx)
