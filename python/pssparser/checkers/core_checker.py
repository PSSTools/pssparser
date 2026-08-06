"""Built-in CoreChecker: metadata for parser and linker diagnostics."""
from __future__ import annotations

from .base import CheckerBase
from .markerdef import MarkerDef


class CoreChecker(CheckerBase):
    """Metadata-only checker that documents built-in parse/link markers.

    The actual checking is performed by C++ code; this class exists purely
    to make the built-in marker catalogue discoverable via ``--list-markers``
    and ``--describe``.
    """

    name = "core"
    description = "Built-in parser and linker diagnostics"

    #: Marks this as a built-in checker that cannot be disabled via
    #: ``--no-checker`` and is never passed to the checker invocation loop.
    is_builtin = True

    marker_defs = [
        MarkerDef(
            id="PSS001",
            severity="error",
            summary="Syntax error",
            detail=(
                "The parser encountered a token it did not expect.  "
                "Messages include patterns such as:\n\n"
                "* ``expected ';' before '}'``\n"
                "* ``unexpected end of input; possible missing closing '}'``\n"
                "* ``unexpected '<token>' in this context``\n"
                "* ``expected identifier before '<token>'``\n\n"
                "Check that the surrounding PSS syntax is well-formed."
            ),
        ),
        MarkerDef(
            id="PSS002",
            severity="error",
            summary="Unknown symbol reference",
            detail=(
                "The linker could not resolve a named type, identifier, or "
                "method.  Messages include patterns such as:\n\n"
                "* ``unknown type 'Foo'``\n"
                "* ``unknown identifier 'bar'``\n"
                "* ``unknown method 'baz' on built-in type``\n"
                "* ``'pkg' has no member named 'thing'``\n"
                "* ``Failed to find elem 'thing'``\n\n"
                "The last two are the same diagnosis reached through a "
                "qualified and an unqualified path respectively.\n\n"
                "Ensure the symbol is declared in one of the source files "
                "passed to pssparser, or that the correct package is imported."
                "  When a close match exists, a ``did you mean '...'?`` "
                "suggestion is appended."
            ),
        ),
        MarkerDef(
            id="PSS003",
            severity="error",
            summary="Duplicate symbol declaration",
            detail=(
                "A symbol with this name is already declared in the same "
                "scope.  Messages include patterns such as:\n\n"
                "* ``duplicate declaration of 'Foo'``\n"
                "* ``duplicate variable declaration bar``\n"
                "* ``duplicate parameter name 'p'``\n"
                "* ``duplicate symbol declaration``\n"
                "* ``function 'f' is already defined``\n"
                "* ``function 'f' cannot be both defined and imported``\n"
                "* ``function 'f' is already imported``\n\n"
                "Rename one of the declarations to resolve the conflict."
            ),
        ),
        MarkerDef(
            id="PSS004",
            severity="error",
            summary="Symbol or ref-path resolution failure",
            detail=(
                "A symbol or reference path could not be resolved during "
                "linking.  Messages include patterns such as:\n\n"
                "* ``failed to resolve ref-path <path>``\n"
                "* ``failed to resolve symbol <name>``\n"
                "* ``root ref-path element <x> is not a composite scope``\n\n"
                "Check that all referenced symbols are declared and that "
                "composite-type fields are used correctly."
            ),
        ),
        MarkerDef(
            id="PSS005",
            severity="error",
            summary="Cannot extend unknown type or enum",
            detail=(
                "An ``extend`` declaration targets a type or enum that does "
                "not exist.  Messages include patterns such as:\n\n"
                "* ``cannot extend unknown type 'Foo'``\n"
                "* ``cannot extend unknown enum 'MyEnum'``\n\n"
                "Ensure the base type is declared before or alongside the "
                "extend block."
            ),
        ),
        MarkerDef(
            id="PSS006",
            severity="error",
            summary="Call does not match the callee's parameters",
            detail=(
                "A function call supplies more or fewer arguments than the "
                "callee declares, names something that is not a function, or "
                "the callee's parameter list is itself malformed.  Messages "
                "include patterns such as:\n\n"
                "* ``too few arguments to 'f': expected 2, got 1``\n"
                "* ``too many arguments to 'f': expected 1, got 2``\n"
                "* ``'x' is not a function``\n"
                "* ``parameter 'b' has no default, but follows 'a' which "
                "does``\n"
                "* ``argument 1 of 'f' is a string, but parameter 'a' is "
                "numeric``\n\n"
                "Argument types are compared only by broad category -- "
                "numeric, string, composite.  Widths, signedness and struct "
                "subtyping are deliberately not judged.\n\n"
                "Parameters with a default may be omitted, which is why the "
                "bound is reported as ``at least``/``at most`` when the two "
                "differ.  A ``type... args`` parameter removes the upper "
                "bound entirely."
            ),
        ),
        MarkerDef(
            id="PSS007",
            severity="error",
            summary="Return type used inconsistently",
            detail=(
                "A ``return`` supplies a value from a ``void`` function, "
                "omits one where a return type is declared, or the result of "
                "a ``void`` call is used as a value.  Messages include "
                "patterns such as:\n\n"
                "* ``'f' returns void, so 'return' cannot take a value``\n"
                "* ``'f' has a return type, so 'return' must supply a "
                "value``\n"
                "* ``'f' returns void, so its result cannot be used as a "
                "value``\n\n"
                "The last of these is LRM 20.5: a void function "
                "\"may only be called as a standalone procedural "
                "statement\".  The converse -- calling a non-void function "
                "as a statement and discarding the result -- is explicitly "
                "legal and is not reported.\n\n"
                "Taking a member of a call result counts as using it, so "
                "``f().x`` on a void ``f`` is reported here rather than as a "
                "resolution failure.  A *scalar* return is not: ``f().x`` on "
                "an int-returning ``f`` gets the same PSS004 message a scalar "
                "variable would.\n\n"
                "Whether a non-void function returns on *every* path is not "
                "checked."
            ),
        ),
        MarkerDef(
            id="PSS008",
            severity="error",
            summary="Function qualifier is not allowed here",
            detail=(
                "A ``pure`` or parameter-direction qualifier is used where "
                "the LRM does not allow it.  Messages include patterns such "
                "as:\n\n"
                "* ``parameter 'a' of 'f' is declared output, so 'f' may "
                "only be imported, not defined in PSS``\n"
                "* ``'f' is declared pure, so it cannot return void``\n"
                "* ``'f' is declared pure, so parameter 'a' cannot be "
                "output``\n\n"
                "Direction modifiers (LRM 20.2.2, 20.3.2) mark a function as "
                "importable only; a function carrying one on any of its "
                "declarations may not also have a PSS body.  Functions built "
                "into an implementation, such as the core library, are "
                "exempt.\n\n"
                "``pure`` (LRM 20.2.6) asserts that the result depends only "
                "on the arguments and that evaluation has no side effects, "
                "so a pure function can be neither ``void`` nor take an "
                "``output``/``inout`` parameter.\n\n"
                "The ``const`` parameter qualifier (LRM 20.2.3) is parsed "
                "and discarded rather than checked -- no AST node records "
                "it."
            ),
        ),
        MarkerDef(
            id="PSS009",
            severity="error",
            summary="Declarations of one function disagree",
            detail=(
                "A function may be declared more than once -- a prototype "
                "and a definition, a prototype and an ``import`` -- and LRM "
                "20.2 requires every declaration to give the same signature. "
                " Messages include patterns such as:\n\n"
                "* ``declarations of 'f' disagree about the return type``\n"
                "* ``declarations of 'f' disagree about the return type: one "
                "returns void and the other does not``\n"
                "* ``declarations of 'f' disagree about the number of "
                "parameters (1 and 2)``\n"
                "* ``declarations of 'f' disagree about the type of parameter "
                "1 ('a')``\n"
                "* ``declarations of 'f' disagree about the direction of "
                "parameter 1 ('a')``\n"
                "* ``declarations of 'f' disagree about what kind of "
                "parameter 1 ('a') is``\n"
                "* ``declarations of 'f' disagree about whether parameter 2 "
                "('args') is varargs``\n"
                "* ``parameter 1 ('a') of 'f' is given a default value by "
                "more than one declaration``\n\n"
                "Reported once per function, against the declaration the "
                "rest of the tool treats as authoritative: a definition's "
                "prototype where there is one, otherwise the first.\n\n"
                "The last of these is LRM 20.2.4 c, which forbids "
                "respecifying a default \"even if the value is the same\" -- "
                "so the values are never compared.  A default given by only "
                "one declaration is in effect for all of them.\n\n"
                "Only a *certain* difference is reported.  A ``typedef`` "
                "alias, an integer width that will not fold to a constant, a "
                "default width against a written one, and a type name that "
                "did not resolve are all cases where the two declarations may "
                "well agree, and none of them is reported.\n\n"
                "Three things are deliberately **not** compared. Parameter "
                "*names*, because PSS calls are positional and nothing "
                "requires a redeclaration to reuse them.  A ``pure`` "
                "qualifier, because LRM 20.2.6 b permits omitting it in a "
                "definition whose declaration carries it.  The ``const`` "
                "qualifier, which LRM 20.2.3 c does make part of the "
                "signature -- but it is parsed and discarded, so there is "
                "nothing to compare.\n\n"
                "A *static* function shadowed in a derived component may "
                "differ freely (LRM 20.2) and is not reported.  An "
                "*instance* function shadowed in a derived component must "
                "match, and that is not checked."
            ),
        ),
        MarkerDef(
            id="PSS010",
            severity="error",
            summary="Bad field name in a masked register write",
            detail=(
                "``write_field`` / ``write_fields`` / ``write_masked`` (LRM "
                "21.14.1) name a *declared field* of the register's value "
                "type.  The string spelling is forced by the signature "
                "``write_field(string name, bit[SZ] val)`` and does not make "
                "the name data: 21.14.1 restricts it to a string **literal** "
                "precisely so a tool can resolve it at compile time.  "
                "Messages include patterns such as:\n\n"
                "* ``no field 'chan_en' in register value type 'csr_s'; did "
                "you mean 'ch_en'?``\n"
                "* ``write_field: field 'sub' of 'agg_s' has a composite "
                "type; field-wise register access applies to scalar fields "
                "only``\n"
                "* ``write_field: the field name must be a string literal``\n"
                "* ``write_field: field name 'a.b' must not be a "
                "hierarchical reference``\n"
                "* ``write_fields: duplicate field name 'prio'``\n"
                "* ``write_fields: 2 field name(s) but 1 value(s)``\n"
                "* ``write_masked: no field 'nosuch' in register value type "
                "'csr_s'``\n"
                "* ``write_field: this register's value type is not a "
                "struct, so it has no named fields``\n\n"
                "A duplicate name matters more than it looks: the plural "
                "form writes its fields in a *single* read-modify-write, so "
                "naming one twice does not write it twice -- one of the two "
                "values is simply lost.\n\n"
                "Which **bits** a resolved field occupies is deliberately not "
                "decided here.  ``packed_s<>`` layout is a target "
                "representation -- backends order it oppositely on purpose -- "
                "so the compiler folds the mask.  This checks *which field*; "
                "the compiler answers *which bits*."
            ),
        ),
    ]

    def check(self, context) -> None:  # noqa: D102
        pass  # core checking is performed in C++
