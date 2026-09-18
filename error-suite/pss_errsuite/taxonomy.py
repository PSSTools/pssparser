"""The class taxonomy (design §3.3).

A case's `class:` must be one of these, optionally with a further dotted
sub-path (`semantic.type.assign-incompatible`).  Keeping the list closed is
what makes "comprehensive" a checkable claim rather than a feeling: an
unlisted class is either a typo or a deliberate extension of the taxonomy, and
both should be a conscious edit here.
"""
from __future__ import annotations

SYNTAX = (
    "syntax.punct", "syntax.braces", "syntax.names", "syntax.keyword",
    "syntax.scope", "syntax.expr", "syntax.type", "syntax.lex",
    "syntax.stmt", "syntax.reserved", "syntax.recover", "syntax.multifile",
    "syntax.volume", "syntax.template",
)

SEMANTIC = (
    "semantic.resolve", "semantic.duplicate", "semantic.type", "semantic.expr",
    "semantic.constraint", "semantic.decl", "semantic.inherit",
    "semantic.extend", "semantic.template", "semantic.func", "semantic.exec",
    "semantic.activity", "semantic.flow", "semantic.component",
    "semantic.coverage", "semantic.reg", "semantic.addr", "semantic.compile",
    "semantic.pkg", "semantic.31",
)

ACCEPT = (
    "accept.shadowing", "accept.forward-ref", "accept.declarations",
    "accept.extend", "accept.template", "accept.literals", "accept.expr",
    "accept.activity", "accept.misc",
)

#: Harness-test fixtures live outside the real taxonomy on purpose: they are
#: not PSS coverage and must never show up in a coverage rollup.
FIXTURE = ("fixture.harness",)

ALL_CLASSES = SYNTAX + SEMANTIC + ACCEPT + FIXTURE

#: Capabilities a case may legitimately require.  `solver` is deliberately
#: absent: solver-dependent defects are out of scope (design §1), and this list
#: is where that decision is enforced rather than remembered.
CAPABILITIES = ("multifile", "max_errors", "json_output")

#: Language versions the corpus knows about.
PSS_VERSIONS = ("3.0", "3.1")


def is_known_class(cls: str) -> bool:
    return any(cls == c or cls.startswith(c + ".") for c in ALL_CLASSES)


def top_level(cls: str) -> str:
    return cls.split(".", 1)[0]
