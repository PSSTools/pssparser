"""Walk every activity statement, including those held behind a body accessor.

A walk over `getChildren()` alone misses every body that a statement holds
through an accessor rather than as a child: `atomic`'s body, both branches of
an `if`, the body of `repeat`, `foreach` and `replicate`, and the body of each
`select` branch and `match` choice. sphinx-pss R1 (an `atomic` body with no
location) went unnoticed for exactly that reason, so the location and comment
tests sweep with this instead.
"""


def _tname(node):
    return type(node).__name__ if node is not None else None


def _children(node):
    if not hasattr(node, "getChildren"):
        return []
    return [node.getChild(i) for i in range(len(node.getChildren()))]


def _bodies(node):
    """The statements `node` holds through accessors rather than children."""
    out = []
    for acc in ("getBody", "getTrue_s", "getFalse_s"):
        if hasattr(node, acc):
            b = getattr(node, acc)()
            if b is not None:
                out.append(b)
    if hasattr(node, "numBranches"):
        for i in range(node.numBranches()):
            b = node.getBranche(i).getBody()
            if b is not None:
                out.append(b)
    if hasattr(node, "numChoices"):
        for i in range(node.numChoices()):
            b = node.getChoice(i).getBody()
            if b is not None:
                out.append(b)
    return out


def activity_nodes(node):
    """Every `Activity*` node below `node`, depth-first in source order.

    A labeled top-level statement is also an entry in its action's scope
    (LRM 11.8), but `node` is the ActivityDecl, whose children are each
    statement once, so nothing is reported twice.
    """
    out = []
    for c in _children(node) + _bodies(node):
        if _tname(c).startswith("Activity"):
            out.append(c)
            out.extend(activity_nodes(c))
    return out
