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

    #: Marker IDs are allocated in bands:
    #:
    #:   ``PSS000``             internal error (a defect in pssparser)
    #:   ``PSS001``-``PSS099``  general parse/link diagnostics
    #:   ``PSS100``-``PSS199``  PSS 3.1 language-rule diagnostics
    #:
    #: Core markers originate in C++, which does not carry an ID on the marker
    #: object.  The ID is recovered by matching ``patterns`` against the message
    #: text, so the regexes here and the message strings in ``src/*.cpp`` must
    #: agree.  ``tests/python/test_marker_ids.py`` pins that correspondence.
    marker_defs = [
        MarkerDef(
            id="PSS000",
            severity="error",
            summary="Internal error",
            patterns=(
                r"^internal error\b",
            ),
            detail=(
                "pssparser reached a state it believed could not happen.  "
                "This is a defect in pssparser, not necessarily in the model, "
                "and it should be reported together with the input that "
                "triggers it.  The message names the phase or link pass that "
                "failed:\n\n"
                "* ``internal error in resolving references: ...``\n"
                "* ``internal error while building the AST: ...``\n\n"
                "Results for the rest of the model are incomplete: the pass "
                "that failed stopped, and the passes after it did not run.  "
                "The command-line tool exits with status 3 when an internal "
                "error is reported."
            ),
        ),
        MarkerDef(
            id="PSS001",
            severity="error",
            summary="Syntax error",
            patterns=(
                r"^expected\b",
                r"^unexpected\b",
                r"^unknown exec-block kind\b",
                r"^syntax error at\b",
            ),
            detail=(
                "The parser encountered a token it did not expect.  "
                "Messages include patterns such as:\n\n"
                "* ``expected ';' before '}'``\n"
                "* ``unexpected end of input; possible missing closing '}'``\n"
                "* ``unexpected '<token>' in this context``\n"
                "* ``expected identifier before '<token>'``\n"
                "* ``syntax error at '<token>'``\n\n"
                "Check that the surrounding PSS syntax is well-formed."
            ),
        ),
        MarkerDef(
            id="PSS002",
            severity="error",
            summary="Unknown symbol reference",
            patterns=(
                r"^unknown type\b",
                r"^unknown identifier\b",
                r"^unknown method\b",
                r"^unknown function\b",
                r"\bhas no member named\b",
                # The same failure as the line above, reached through the
                # *unqualified* path. The two spellings are one diagnosis and
                # must carry one code.
                r"^failed to find elem\b",
                # `this` where there is no enclosing type for it to name.
                r"^'this' is only valid inside a type\b",
                # `super.x` with no base type to search, or outside a type;
                # and `super;` with no base activity or exec block to run.
                r"^'super;?' is only valid inside a type\b",
                # A built-in member where the enclosing type has none:
                # `comp` in an abstract action declared in a package, and
                # `prev` reached as a member from outside its state.
                r"^'(comp|prev)' is only valid in\b",
                # A name in an exec, activity or template block used before
                # the block declares it (18.2a/b, 4.7.1.2).
                r"\bis used before its declaration\b",
            ),
            detail=(
                "The linker could not resolve a named type, identifier, or "
                "method.  Messages include patterns such as:\n\n"
                "* ``unknown type 'Foo'``\n"
                "* ``unknown type 'Foo' in 'pkg'`` (the name is not in the "
                "qualifying package or scope)\n"
                "* ``unknown identifier 'bar'``\n"
                "* ``unknown method 'baz' on built-in type``\n"
                "* ``unknown function 'f': an import of this form needs a "
                "separate declaration of the function (20.4.1)``\n"
                "* ``'pkg' has no member named 'thing'``\n"
                "* ``Failed to find elem 'thing'``\n"
                "* ``'this' is only valid inside a type: ...`` (``this`` in "
                "a package-level function)\n"
                "* ``'super' is only valid inside a type that has a base "
                "type, and 'S' has none`` (also ``'super;'``)\n"
                "* ``'comp' is only valid in an action declared in a "
                "component, and 'AB' is declared outside one``\n"
                "* ``'prev' is only valid in a state type or its extension, "
                "and cannot be reached as a member of 'i'``\n"
                "* ``base type 'B' has no member named 'x'`` (``super.x``)\n\n"
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
            patterns=(
                r"^duplicate\b",
                r"^function '.*' is already (defined|imported)\b",
                r"^function '.*' cannot be both defined and imported\b",
            ),
            detail=(
                "A symbol with this name is already declared in the same "
                "scope.  Messages include patterns such as:\n\n"
                "* ``duplicate declaration of 'Foo'``\n"
                "* ``duplicate variable declaration bar``\n"
                "* ``duplicate parameter name 'p'``\n"
                "* ``duplicate symbol declaration``\n"
                "* ``duplicate parameter name 'a'``\n"
                "* ``function 'f' is already defined``\n"
                "* ``function 'f' cannot be both defined and imported``\n"
                "* ``function 'f' is already imported``\n"
                "* ``duplicate declaration of 'a' in an extension of 'S': "
                "its initial definition already declares it (17.2.3)``\n"
                "* ``duplicate declaration of enum item 'B' in 'e': an enum "
                "item must be unique across the enum and all its extensions "
                "(7.5.1)``\n\n"
                "Rename one of the declarations to resolve the conflict.\n\n"
                "Note that ``duplicate declaration of '...'`` is currently "
                "emitted as a *warning* while the others are errors."            ),
        ),
        MarkerDef(
            id="PSS004",
            severity="error",
            summary="Symbol or ref-path resolution failure",
            patterns=(
                r"^failed to resolve\b",
                r"\bref-path element\b",
            ),
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
            patterns=(
                r"^cannot extend unknown\b",
                r"^cannot extend '[^']*'(?: as an enum)?: it is not an\b",
            ),
            detail=(
                "An ``extend`` declaration targets a type or enum that does "
                "not exist, or a name that is not a type of the kind "
                "extended.  Messages include patterns such as:\n\n"
                "* ``cannot extend unknown type 'Foo'``\n"
                "* ``cannot extend unknown enum 'MyEnum'``\n"
                "* ``cannot extend unknown type 'a' in 'C'; an extension "
                "inside a component may extend only a type the component "
                "declares (17.3)``\n"
                "* ``cannot extend 'x': it is not an extendable type``\n"
                "* ``cannot extend 's' as an enum: it is not an enum type``\n\n"
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
                "* ``'size' is a method; call it as 'size()'``\n"
                "* ``'v' is not a symbol; only a symbol can be called in an "
                "activity``\n"
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
            patterns=(
                r"^too few arguments\b",
                r"^too many arguments\b",
                r"^call to '.*' expects\b",
                r"^no overload of '.*' accepts\b",
                r"^'.*' is not a function; it is\b",
                r"^'.*' is not a function",
                r"^'.*' is a method; call it as\b",
                r"^'.*' is not a symbol; only a symbol can be called\b",
                r"\bhas no default, but follows\b",
                r"^argument \d+ of\b",
                r"^argument \d+ to '.*' expects\b",
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
            patterns=(
                r"\breturns void, so 'return'",
                r"\breturns void, so its result\b",
                r"\bhas a return type, so 'return'",
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
            patterns=(
                r"\bmay only be imported, not defined in PSS\b",
                r"\bis declared pure, so\b",
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
                "* ``declarations of 'f' disagree about the default value "
                "of parameter 2 ('y')``\n\n"
                "Reported once per function, against the declaration the "
                "rest of the tool treats as authoritative: a definition's "
                "prototype where there is one, otherwise the first.\n\n"
                "The last of these is LRM 3.1 20.2.4 c: a redeclaration may "
                "repeat a default, \"but this value shall be equal\".  The "
                "values are compared after folding; a default that does not "
                "fold to a constant is not reported.  (PSS 3.0 forbade "
                "repeating a default at all.)  A default given by only one "
                "declaration is in effect for all of them.\n\n"
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
            patterns=(
                r"^declarations of '.*' disagree\b",
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
            patterns=(
                r"\bin register value type\b",
                r"^write_field\b",
                r"^write_fields\b",
                r"^write_masked\b",
            ),
        ),
        MarkerDef(
            id="PSS011",
            severity="error",
            summary="Digit out of range for a based literal's radix",
            detail=(
                "A based literal (LRM B.19, e.g. ``'hFF``, ``8'b1010``) contains "
                "a digit that is not valid for its radix -- for example a "
                "hex literal spelled with a letter past ``f``/``F``. The "
                "lexer accepts any alphanumeric run after the radix "
                "character so a typo still lexes as one literal token "
                "(rather than a lexical error splitting the trailing "
                "characters into an unrelated token); this check then "
                "validates the digits against the radix. Only the first "
                "invalid digit is reported. Message: ``invalid digit '<c>' "
                "in based literal``."
            ),
            patterns=(
                r"^invalid digit\b",
            ),
        ),
        MarkerDef(
            id="PSS012",
            severity="error",
            summary="Packed struct field has a type a packed struct cannot hold",
            detail=(
                "A packed struct -- any struct derived, directly or "
                "indirectly, from ``packed_s`` -- may only have fields of "
                "numeric types, ``bool``, enumerated types that have a base "
                "type, packed struct types, or fixed-size arrays of these "
                "(LRM 21.13.1). Anything else has no defined bit layout. "
                "Messages take the form ``field '<f>' of packed struct '<s>' "
                "is <what>; <how to fix it>``, for example:\n\n"
                "* ``field 'mode' of packed struct 'ctrl_s' is enum 'mode_e', "
                "which has no base type; declare it as 'enum mode_e : "
                "bit[N]'``\n"
                "* ``field 'h' of packed struct 'desc_s' is a chandle; use "
                "sized_addr_handle_s<SZ> for an address``\n"
                "* ``field 'q' of packed struct 's' is struct 'q_s', which is "
                "not packed; derive it from packed_s<>``\n"
                "* ``field 'l' of packed struct 's' is a list; use a "
                "fixed-size array, 'T name[N]'``\n"
                "* ``field 's' of packed struct 'd' is a string, which cannot "
                "be packed``\n\n"
                "A width-less enum is not 32 bits wide in a packed struct: it "
                "is not allowed there at all. A flow or resource object that "
                "inherits from a packed struct is not itself packed (LRM "
                "17.1). ``static const`` members are not part of the layout "
                "and are not checked. A generic packed struct is checked per "
                "specialization."
            ),
            patterns=(
                r"^field '[^']*' of packed struct '[^']*' is ",
            ),
        ),
        MarkerDef(
            id="PSS013",
            severity="error",
            summary="Type extension adds a field to a packed struct",
            detail=(
                "LRM 21.13.1: \"Type extensions of packed structs shall not "
                "add new fields.\" A packed struct's layout is fixed by its "
                "declaration; an ``extend`` elsewhere must not change it. "
                "Constraints, exec blocks and ``static const`` members may "
                "still be added. Message: ``type extension of packed struct "
                "'<s>' adds field '<f>'; an extension of a packed struct may "
                "not add fields``."
            ),
            patterns=(
                r"^type extension of packed struct '[^']*' adds field ",
            ),
        ),
        MarkerDef(
            id="PSS014",
            severity="error",
            summary="Register value type has no size, or is wider than the register",
            detail=(
                "``reg_c<R, ACC, SZ>`` (LRM 21.14.1) lays a value of type "
                "``R`` over a register ``SZ`` bits wide. ``R`` must have a "
                "known packed size -- a packed struct, or another packable "
                "type such as ``bit[N]``, ``int[32]`` or an enum with a base "
                "type -- and ``SZ``, when given, must be at least "
                "``sizeof_s<R>::nbits``. (Omitting ``SZ`` gives "
                "``8*sizeof_s<R>::nbytes``, which always fits.) Messages "
                "include:\n\n"
                "* ``reg_c value type is struct 'cfg_s', which is not packed; "
                "derive it from packed_s<>``\n"
                "* ``reg_c value type is enum 'mode_e', which has no base "
                "type; ...``\n"
                "* ``reg_c width SZ = 32 is smaller than its value type "
                "'desc_s' (40 bits)``\n\n"
                "Reported where the register type is used (``reg_c<...>`` as "
                "a field type or a base type), not in the core library."
            ),
            patterns=(
                r"^reg_c value type is ",
                r"^reg_c width SZ = -?\d+ is smaller than its value type",
            ),
        ),
        MarkerDef(
            id="PSS015",
            severity="error",
            summary="sizeof_s of a type that has no packed size",
            detail=(
                "LRM 21.13.2.1: ``sizeof_s<>`` \"shall not be parameterized "
                "with types other than numeric types, Booleans, enumerated "
                "types that have a base type, packed structs, and arrays "
                "thereof.\" Such a specialization has no ``nbits`` or "
                "``nbytes`` value. Message: ``sizeof_s argument is <what>, which "
                "has no packed size``, or ``sizeof_s argument is <what>; <how "
                "to fix it>``. A packed struct with a bad member is reported "
                "at the member (PSS012), not here."
            ),
            patterns=(
                r"^sizeof_s argument is ",
            ),
        ),
        MarkerDef(
            id="PSS016",
            severity="warning",
            summary="Register width has no primitive access function",
            detail=(
                "LRM 21.14.5a translates register reads and writes into the "
                "primitive ``read8/16/32/64`` and ``write8/16/32/64`` "
                "functions (21.13.9), chosen by the register's size. A "
                "register ``SZ`` bits wide, where ``SZ`` is not 8, 16, 32 or "
                "64, has no such function, so its access cannot be translated "
                "as the spec describes. Not a \"shall\" in the spec, so a "
                "warning. A packed struct of any size is legal on its own -- "
                "a 96-bit DMA descriptor, say; this is only about using one "
                "as a register value type. Message: ``reg_c width SZ = 96 has "
                "no primitive access function; use 8, 16, 32 or 64 bits``. "
                "For a register whose "
                "value type is narrower than a primitive, give ``SZ`` "
                "explicitly (``reg_c<my12_s, READWRITE, 16>``)."
            ),
            patterns=(
                r"^reg_c width SZ = -?\d+ has no primitive access function",
            ),
        ),

        MarkerDef(
            id="PSS017",
            severity="error",
            summary="Ambiguous name: more than one import provides it",
            detail=(
                "LRM 18.1.3: when two imports of the same kind make the same "
                "name visible, and they name different declarations, the name "
                "is not imported at all. An explicit import (``import p::s;``) "
                "takes precedence over a wildcard import (``import p::*;``), "
                "so only imports of the same kind can conflict. Two imports "
                "that reach the same declaration do not conflict.  Message: "
                "``ambiguous reference to 's': more than one wildcard import "
                "provides it, so none does (18.1.3); qualify the name``. "
                "Qualify the name (``lib1::s``) or import it explicitly."
            ),
            patterns=(r"^ambiguous reference to\b",),
        ),
        MarkerDef(
            id="PSS018",
            severity="error",
            summary="Traversal of something that is not an action",
            detail=(
                "An action traversal statement names something that cannot be "
                "traversed.  LRM 11.3.1: the identifier \"names a unique "
                "action handle or variable in the context of the containing "
                "action type or activity scope\"; a variable may be a data "
                "field declared with the ``action`` modifier, which is "
                "randomized with no execution (Example 173).  A generic "
                "constraint (13.4.11), a deprecated ``dynamic`` constraint "
                "(see PSS117) and a symbol may also be traversed.  Messages "
                "include:\n\n"
                "* ``'x' is not an action handle, and cannot be traversed; "
                "only a handle, or a data field declared with the 'action' "
                "modifier, can be``\n"
                "* ``'A' is a type, not an action handle; traverse it by type "
                "with 'do A'``\n"
                "* ``'L1' is an activity label, not an action handle, and "
                "cannot be traversed``\n"
                "* ``'c' is a fixed constraint, which always holds and cannot "
                "be traversed; ...`` -- write it as a generic constraint, "
                "``constraint c() { ... }``\n"
                "* ``'S' is not an action type, and cannot be traversed`` "
                "(``do S`` on a struct or component)\n\n"
                "A name that is not declared at all is PSS002."
            ),
            patterns=(
                r"\bnot an action handle\b",
                r"\bis not an action type, and cannot be traversed\b",
                r"\bis a fixed constraint, which always holds and cannot be traversed\b",
            ),
        ),

        MarkerDef(
            id="PSS019",
            severity="error",
            summary="Function cannot be imported here",
            patterns=(
                r"^cannot import function\b",
            ),
            detail=(
                "An ``import ... function`` names a function that the LRM "
                "does not allow to be imported from where the import is "
                "written.  Messages include patterns such as:\n\n"
                "* ``cannot import function 'f' here: it is declared in "
                "component 'base_c', and may be imported only in that "
                "component type (20.4.1)``\n"
                "* ``cannot import function 'f': it is declared in template "
                "component 't_c' (20.4.1)``\n"
                "* ``cannot import function 'f': it is an instance function "
                "of component 'c', and instance functions cannot be imported "
                "(20.4)``\n"
                "* ``cannot import function 'f': a component function must "
                "be declared 'static' to be imported; instance functions "
                "cannot be imported (20.4)``\n\n"
                "LRM 20.4.1: a static function declared in a component can "
                "be imported only in the scope of that same component type "
                "-- not in a derived component, an unrelated one, or a "
                "package -- and a function declared in a template component "
                "cannot be imported at all.  Declare the function where it "
                "is imported, or move the import next to the declaration.  "
                "A function declared in a package can be imported anywhere "
                "it is visible.\n\n"
                "LRM 20.4: an instance (non-static) function cannot be "
                "imported.  In a component, the prototype form of the import "
                "must say ``static`` (20.4.1.1 b.1), so ``import C function "
                "void f(int a);`` there is reported whether or not ``f`` is "
                "declared ``static`` elsewhere; the name form (``import C "
                "function f;``) is reported when no declaration of ``f`` "
                "says ``static``."
            ),
        ),

        # -- Syntax-error sub-band (PSS020-PSS029) ---------------------------
        #
        # Unlike PSS001-PSS019 above, these markers carry their own `code`
        # from the C++ side (AstBuilderInt::syntaxError / rewriteSyntaxError
        # classifies at the point the message is built), so `patterns` is deliberately left
        # empty -- there is nothing for _assign_core_code to match, and a test
        # in test_marker_ids.py asserts it never fires for one of these IDs.
        # PSS027 is the lexer's ID, and is live as of A6: AstBuilderInt is now
        # the lexer's error listener as well as the parser's, so an
        # unterminated string or block comment is a marker rather than a line
        # on stderr that no consumer -- including the exit status -- ever saw
        # (that was the corpus's U-9, now retired). PSS023 is still reserved,
        # not assigned: see PSS022's detail for why the keyword sub-case it
        # was meant for turned out to be unreachable.

        MarkerDef(
            id="PSS020",
            severity="error",
            summary="Expected specific punctuation before this token",
            detail=(
                "The parser reached a point where only one or two specific "
                "punctuation tokens could legally continue the construct, and "
                "the next token was not one of them. Messages include "
                "patterns such as:\n\n"
                "* ``expected ';' before '<token>'``\n"
                "* ``expected '{' or ':' before '<token>'``\n"
                "* ``expected '{' or ':' before 'extends'; use ':' for "
                "inheritance, not 'extends'``\n\n"
                "Insert the missing punctuation, or (for the last case) "
                "replace ``extends`` with ``:``."
            ),
        ),
        MarkerDef(
            id="PSS021",
            severity="error",
            summary="Unexpected end of input",
            detail=(
                "The file ended while a scope (``{ ... }``) was still open.\n\n"
                "When the still-open scope is a ``component`` or ``struct`` "
                "declared directly (not several rules deeper, e.g. mid "
                "``exec`` body), the marker is reported **at the opening "
                "``{``** of that declaration, named by kind and identifier, "
                "with the end-of-file position attached as a related "
                "location:\n\n"
                "* ``unclosed '{' for component '<name>'``\n"
                "* ``unclosed '{' for struct '<name>'``\n\n"
                "Otherwise -- a deeper truncation, or any other brace-opening "
                "construct (``enum``, ``constraint``, an ``exec`` body, ...) "
                "-- the marker falls back to the generic end-of-file "
                "message, reported at the end of file itself:\n\n"
                "* ``unexpected end of input; missing closing '}'``\n\n"
                "For the fallback case, count braces from the point the "
                "parser last made progress; the true cause is often several "
                "lines above the file's last line, not at it."
            ),
        ),
        MarkerDef(
            id="PSS022",
            severity="error",
            summary="Expected an identifier before this token",
            detail=(
                "The grammar requires an identifier at this position and the "
                "next token is not one. Reached via either of ANTLR's two "
                "recovery strategies for the same situation: single-token-"
                "insertion (offending token already in the follow set, e.g. "
                "``;``, ``{``, ``=``) or a full mismatched-input exception "
                "whose expecting-set is exactly identifier-shaped (``{ID, "
                "ESCAPED_ID}``, optionally with a leading ``'::'``) -- which "
                "is how a real PSS keyword used where an identifier belongs "
                "(``struct``, ``return``, ...) lands here too. There is no "
                "reachable keyword sub-case distinct from this one -- "
                "**PSS023 is reserved, not assigned**.\n\n"
                "Messages:\n\n"
                "* ``expected identifier before '<token>'``\n"
                "* ``'this' is a keyword and cannot be used as a declared "
                "name`` -- the one keyword the lexer returns as an "
                "identifier, so the grammar accepts it and the declaration "
                "is rejected afterwards"
            ),
        ),
        MarkerDef(
            id="PSS024",
            severity="error",
            summary="Unexpected token in this context",
            detail=(
                "A general ``mismatched input`` case that PSS020, PSS021, and "
                "PSS022 do not cover more specifically: the token is not one "
                "of the (possibly several) tokens that could legally appear "
                "here. Messages include patterns such as:\n\n"
                "* ``unexpected '<token>' in this context`` (the expecting "
                "set was too large to usefully quote)\n"
                "* ``unexpected '<token>' expecting {<alternatives>}`` (the "
                "expecting set was small enough to show)"
            ),
        ),
        MarkerDef(
            id="PSS025",
            severity="error",
            summary="Unexpected punctuation in this context",
            detail=(
                "A single punctuation token appears where nothing could "
                "legally follow.\n\n"
                "Message: ``unexpected '<token>' in this context``\n\n"
                "The same wording as PSS024's first pattern; the two differ "
                "only in which ANTLR exception produced them "
                "(``extraneous input`` here, ``mismatched input`` there)."
            ),
        ),
        MarkerDef(
            id="PSS026",
            severity="error",
            summary="Unexpected token in this context (non-punctuation)",
            detail=(
                "As PSS025, but the extraneous token is not a single "
                "punctuation character -- a keyword, a multi-character "
                "operator, or a literal. Only called a \"keyword\" in the "
                "message when it actually looks like one (starts with a "
                "letter or ``_``); anything else, such as a numeric literal, "
                "gets the plain PSS025-style wording while keeping this ID. "
                "Messages include patterns such as:\n\n"
                "* ``unexpected keyword '<token>' in this context``\n"
                "* ``unexpected '<token>' in this context`` (non-keyword-"
                "looking offender, e.g. ``123``)"
            ),
        ),
        MarkerDef(
            id="PSS027",
            severity="error",
            summary="Lexical error: the text could not be made into a token",
            detail=(
                "The lexer, not the parser, could not read this. It is "
                "reported where the unreadable run *starts* -- the opening "
                "quote or ``/*`` -- rather than wherever the parser later "
                "tripped over what was left, which is usually a line or two "
                "further on and about the wrong thing entirely.\n\n"
                "Messages include patterns such as:\n\n"
                "* ``unterminated string literal``\n"
                "* ``unterminated triple-quoted string literal``\n"
                "* ``unterminated block comment``\n"
                "* ``unexpected character '<c>'``\n\n"
                "The parse error that a lexical defect provokes immediately "
                "afterwards is suppressed: an unterminated string swallows "
                "the rest of its line, so what follows not parsing is the "
                "same defect, not a second one."
            ),
        ),
        MarkerDef(
            id="PSS028",
            severity="error",
            summary="Syntax error (unclassified alternative)",
            detail=(
                "ANTLR could not decide among the grammar's alternatives at "
                "this point (a ``no viable alternative`` exception) and no "
                "more specific rewrite applies.\n\n"
                "Message: ``syntax error at '<token>'``\n\n"
                "The message does not say what was expected; work outward "
                "from the enclosing construct to find the mistake."
            ),
        ),
        MarkerDef(
            id="PSS029",
            severity="error",
            summary="Too many errors; stopped reporting further errors",
            detail=(
                "``--max-errors`` (default 20; ``0`` disables the cap) was "
                "reached for this file. Only error-severity markers count "
                "against it -- warnings and hints never trigger it, and a "
                "clean file never sees it. Emitted once, at the location of "
                "the error that pushed the count over the limit; every "
                "further error in that file is dropped, not merely hidden, "
                "so re-running with a higher (or ``0``) ``--max-errors`` is "
                "the only way to see what comes after it.\n\n"
                "Message: ``too many errors (<N>); stopped reporting "
                "further errors for this file``"
            ),
        ),

        # -- Tooling & extension infrastructure (PSS030-PSS039) -------------
        #
        # Unlike every other core marker, these originate in *Python* -- in
        # CheckerManager's discovery pass -- and carry their `code` directly.
        # They must therefore declare **no** `patterns`: the pattern table
        # built by `cli.commands._build_core_patterns` exists to recover an ID
        # for C++ markers that have none, and a pattern here would let one of
        # these IDs be assigned to an unrelated parser message.
        #
        # They also carry no source location; they are reported against the
        # `NO_FILE` pseudo-path and rendered without a file:line:col prefix.

        MarkerDef(
            id="PSS030",
            severity="warning",
            summary="A checker extension could not be loaded",
            detail=(
                "An entry point in the ``pssparser.extensions`` (or legacy "
                "``pssparser.checkers``) group failed to load. The usual "
                "causes are an import error inside the extension, an "
                "exception raised from its ``register()`` function, or a "
                "module that exposes neither ``register()`` nor the "
                "``CHECKERS`` shorthand.\n\n"
                "The run continues: a third-party extension is code you did "
                "not write, and one broken package must not stop the rest of "
                "the registry from loading. The consequence is that the rules "
                "that extension contributes did **not** run, so a clean "
                "result is not evidence of clean source.\n\n"
                "Use ``--list-extensions`` to see what did load, and "
                "``--no-extensions`` (or ``PSSPARSER_NO_EXTENSIONS=1``) to "
                "confirm the behaviour is the extension's and not "
                "pssparser's. In CI, ``-Werror=PSS030`` makes a failed "
                "extension fatal, which is usually what you want."
            ),
        ),

        MarkerDef(
            id="PSS031",
            severity="warning",
            summary="Entry-point key disagrees with the checker's declared name",
            detail=(
                "A legacy ``pssparser.checkers`` entry point is keyed under "
                "one name while the class it names declares another in its "
                "``name`` attribute.\n\n"
                "The class is authoritative -- it is the name the checker "
                "reports itself under and the name ``--checker`` and "
                "``--no-checker`` select -- so the checker is registered "
                "under the declared name and the entry-point key is ignored. "
                "Rename the key to match; while they disagree, a command line "
                "written against the key silently selects nothing."
            ),
        ),

        MarkerDef(
            id="PSS032",
            severity="warning",
            summary="Extension requires a newer checker API than this build provides",
            detail=(
                "The extension declared ``requires_api = N`` (as a module "
                "level ``REQUIRES_API`` or on the registry inside "
                "``register()``) and ``N`` is greater than this build's "
                "``pssparser.checkers.API_VERSION``.\n\n"
                "The extension is not loaded, deliberately: refusing here "
                "produces one clear message, where loading it anyway produces "
                "an ``AttributeError`` from inside a checker halfway through "
                "a run. Upgrade pssparser, or install a build of the "
                "extension made for this API version."
            ),
        ),

        MarkerDef(
            id="PSS033",
            severity="error",
            summary="Two checkers declare the same marker ID",
            detail=(
                "Marker IDs are globally unique across the core and every "
                "installed extension. Two rules wearing one ID make "
                "``--describe``, ``-Werror=ID`` and every per-ID severity "
                "override ambiguous, so the collision is an error rather "
                "than a warning.\n\n"
                "The checker that lost the collision is not registered; "
                "everything else, including the rest of its extension, still "
                "loads. The message names both contributors. The fix belongs "
                "in the extension: pick an unused prefix -- three letters "
                "plus three digits is the convention, and the ``PSS`` prefix "
                "is reserved for the built-in core checker."
            ),
        ),

        # -- General band, continued (PSS040-PSS099) -----------------------
        #
        # PSS001-PSS019 filled up; PSS020-PSS039 are the syntax and tooling
        # sub-bands above. Pattern-matched like PSS001-PSS019.

        MarkerDef(
            id="PSS040",
            severity="error",
            summary="Instance member used without an instance",
            patterns=(
                r"^'.*' is an instance member of\b",
                r"^cannot reference instance member\b",
            ),
            detail=(
                "A reference reaches a field or function that belongs to an "
                "instance of a type from a place that has no instance to "
                "take it from.  Messages include patterns such as:\n\n"
                "* ``'fld' is an instance member of 'sub_c' and cannot be "
                "referenced through the type; only types, static constants, "
                "static functions and enum items can (18.3)``\n"
                "* ``cannot reference instance member 'fld' from static "
                "function 'st_f': a static function has no component "
                "instance (20.2)``\n\n"
                "LRM 18.3: a type's namespace holds types, static "
                "constants, static functions and enum items, so ``T::m`` "
                "cannot name an ordinary field or an instance function; "
                "reach it through an instance with ``.`` instead.  A "
                "reference written inside ``T``, a subtype of ``T`` or an "
                "extension of either is not reported, since a "
                "base-qualified call there has an instance to use.  A "
                "``const`` field is treated as a constant.\n\n"
                "LRM 20.2: a static component function is not associated "
                "with an instance, so its body cannot read the component's "
                "non-static fields or call its instance functions.  Make "
                "the member static, pass the value in as a parameter, or "
                "drop ``static`` from the function."
            ),
        ),

        MarkerDef(
            id="PSS041",
            severity="error",
            summary="Static member used through 'comp'",
            patterns=(
                r"^cannot reach static member '.*' of '.*' through 'comp'",
            ),
            detail=(
                "An action reaches a static function or static constant of "
                "a component through its ``comp`` handle.  Messages include "
                "patterns such as:\n\n"
                "* ``cannot reach static member 'f' of 'my_c' through "
                "'comp'; name it without 'comp.', as 'f' (9.1.4.1 f)``\n"
                "* ``cannot reach static member 'K' of 'sub_c' through "
                "'comp'; name it through the type instead, as 'sub_c::K' "
                "(9.1.4.1 f)``\n\n"
                "LRM 9.1.4.1 f: \"It shall be illegal to access static "
                "component members using the comp handle.\"  ``comp`` is an "
                "instance; a static member belongs to the component type "
                "(20.2.1.1 c).  A member of the action's own component is "
                "found by its plain name, since the action is declared "
                "inside that component or an extension of it; a member of a "
                "sub-component is named through its type, ``sub_c::f``.  "
                "Reported for every path that starts at ``comp``, including "
                "``comp.sub.f()``."
            ),
        ),

        # -- PSS 3.1 language-rule diagnostics (PSS100-PSS199) --------------
        #
        # These IDs are reserved ahead of the C++ code that emits them, so that
        # numbering cannot collide across parallel work on the PSS 3.1 items.
        # The message text quoted in each `detail` is normative: the C++
        # implementation must produce a message matching `patterns`.

        MarkerDef(
            id="PSS100",
            severity="error",
            summary="Annotation is not attached to a model element",
            detail=(
                "An annotation was written at the end of a scope with no "
                "following declaration to attach it to.  PSS 3.1 §7.13: "
                "*it is an error if no subsequent element is present in the "
                "scope*.\n\n"
                "Message: ``annotation is not attached to a model element``\n\n"
                "Either follow the annotation with the element it describes, or "
                "make it a standalone annotation by terminating it with ``;``, "
                "which attaches it to the enclosing scope."
            ),
            patterns=(
                r"^annotation is not attached\b",
                r"^annotation '.*' has no subsequent element\b",
            ),
        ),
        MarkerDef(
            id="PSS101",
            severity="warning",
            summary="Unknown annotation type (annotation disregarded)",
            detail=(
                "An annotation names a type that is not declared.  This is a "
                "warning rather than an error: PSS 3.1 §7.13 requires that "
                "*PSS processing tools shall disregard unrecognized "
                "annotations*, so the surrounding source still compiles.\n\n"
                "Message: ``unknown annotation type '<T>'; annotation "
                "disregarded``\n\n"
                "If the annotation was meant to be recognized, check that its "
                "``annotation`` declaration is visible -- annotation types must "
                "be declared at package scope."
            ),
            patterns=(r"^unknown annotation type\b",),
        ),
        MarkerDef(
            id="PSS102",
            severity="error",
            summary="Annotation initializer is not a constant expression",
            detail=(
                "An annotation parameter was given a value that cannot be "
                "evaluated at elaboration time.  PSS 3.1 §7.13 requires "
                "annotation attribute initializers to be constant "
                "expressions.\n\n"
                "Message: ``annotation initializer for '<field>' is not a "
                "constant expression``\n\n"
                "This check applies only to recognized annotation types; the "
                "contents of an unknown annotation are disregarded (PSS101)."
            ),
            patterns=(r"^annotation initializer\b",),
        ),
        # PSS103 is retired, and must not be reused.
        #
        # It was allocated for "annotation type declared outside package scope"
        # (§7.13b), but `annotation_declaration` is reachable only from
        # `package_body_item`, so the grammar rejects the construct before any
        # linker check could run. A catalogue entry that can never be emitted
        # would advertise a diagnostic that does not exist.

        MarkerDef(
            id="PSS104",
            severity="warning",
            summary="Deprecated brace-less 'compile if' branch",
            detail=(
                "A ``compile if`` branch consists of a single item that is not "
                "surrounded by braces.  This form remains supported, but is "
                "deprecated: prefer the braced form, which is unambiguous when "
                "the branch later grows to more than one item.\n\n"
                "Message: ``'compile if' branch without enclosing braces is "
                "deprecated``\n\n"
                "Before::\n\n"
                "    compile if (X) component C { }\n\n"
                "After::\n\n"
                "    compile if (X) { component C { } }\n\n"
                "The diagnostic underlines the whole unbraced branch and "
                "carries a related location pointing at the ``compile if`` "
                "keyword that owns it, which disambiguates the two warnings "
                "raised for an ``if``/``else`` pair.  Both branches are "
                "reported regardless of which one the condition selects: the "
                "spelling is deprecated either way, and warning only on the "
                "taken branch would make the diagnostic appear and disappear "
                "as unrelated configuration changed."
            ),
            patterns=(r"\bwithout enclosing braces is deprecated\b",),
        ),
        MarkerDef(
            id="PSS105",
            severity="error",
            summary="Illegal 'mutable' qualifier",
            detail=(
                "The ``mutable`` qualifier (PSS 3.1 §9.1.6) was applied where "
                "it is not permitted.  ``mutable`` may qualify component data "
                "declarations only, and is incompatible with the qualifiers "
                "listed in §9.1.6 a-c.\n\n"
                "Message: ``illegal 'mutable' qualifier: <reason>``"
            ),
            patterns=(r"^illegal 'mutable' qualifier\b",),
        ),
        MarkerDef(
            id="PSS106",
            severity="error",
            summary="Exec block tag not permitted on this exec kind",
            detail=(
                "An exec block tag (PSS 3.1 §5.1) was written on an exec kind "
                "that does not accept one.  Tags are permitted only on "
                "``header``, ``declaration``, ``run_start``, ``run_end``, and "
                "``exec file`` blocks -- not on native exec blocks, not on "
                "``body``, and not on the solve execs (``init_down``, "
                "``init_up``, ``pre_solve``, ``post_solve``, ``pre_body``).\n\n"
                "Message: ``exec block tag is not permitted on '<kind>' exec "
                "blocks``"
            ),
            patterns=(r"^exec block tag is not permitted\b",),
        ),
        MarkerDef(
            id="PSS107",
            severity="error",
            summary="Member selection on a slice",
            detail=(
                "A member was selected from a slice of a collection.  A slice "
                "(``[a..b]``, ``[a..]``, ``[..b]``) denotes a sub-collection, "
                "not a single element, so it has no members of its own -- "
                "``arr[1].f`` names a field of one element, while "
                "``arr[1..3].f`` names a field of a list.\n\n"
                "Message: ``member selection is not permitted on a slice of "
                "'<name>'``\n\n"
                "Slices and plain indexes reach the resolver through the same "
                "subscript list, so before PSS 3.1 support a slice was "
                "silently resolved as though it were an index."
            ),
            patterns=(r"^member selection is not permitted on a slice\b",),
        ),
        MarkerDef(
            id="PSS108",
            severity="error",
            summary="Unterminated mustache expression",
            detail=(
                "A ``{{`` inside a triple-quoted string was never closed by a "
                "matching ``}}`` (PSS 3.1 §4.7.1.1).\n\n"
                "Message: ``unterminated mustache expression; if '{{' was "
                "intended as literal text, separate the braces ('{ {') -- "
                "triple-quoted strings have no escape mechanism``\n\n"
                "The hint is not decoration.  PSS 3.1 makes ``{{`` open a "
                "mustache inside ``\"\"\"...\"\"\"`` and provides **no** escape "
                "mechanism, so target code that legitimately contains two "
                "adjacent open braces -- ``int m[2][2] = {{1,2},{3,4}};`` -- "
                "now fails here.  The conformant spelling is ``{ {``: a lone "
                "``{`` is ordinary text, so separating the braces needs no "
                "escape and is read identically by every other PSS tool.\n\n"
                "Note only the *opening* delimiter is special.  A stray ``}}`` "
                "in text is literal and is never reported, which is why C and "
                "C++ closing braces are unaffected."
            ),
            patterns=(r"^unterminated mustache expression\b",),
        ),
        MarkerDef(
            id="PSS109",
            severity="error",
            summary="Malformed mustache expression",
            detail=(
                "The content of a ``{{ ... }}`` did not parse as a PSS "
                "expression (PSS 3.1 §4.7.1.1).\n\n"
                "Message: ``malformed mustache expression: <detail>; if '{{' "
                "was intended as literal text, separate the braces ('{ {')``\n\n"
                "Syntax errors from the sub-parse are wrapped in this "
                "diagnostic rather than forwarded verbatim: a raw "
                "``mismatched input '}' expecting ...`` rebased out of a "
                "fragment tells the user nothing about the real cause, which "
                "is most often the ``{{`` collision described under PSS108.\n\n"
                "An unparseable mustache is deliberately an **error** and "
                "never silently-literal text.  Treating it as text would let a "
                "genuinely malformed ``{{ x + }}`` through unnoticed."
            ),
            patterns=(r"^malformed mustache expression\b",),
        ),
        MarkerDef(
            id="PSS110",
            severity="error",
            summary="Malformed or unterminated template directive or comment",
            detail=(
                "A ``{% ... %}`` directive or ``{# ... #}`` comment inside a "
                "triple-quoted string is unterminated, does not parse, or "
                "opened a block that was never closed (PSS 3.1 §4.7.1.2, "
                "§4.7.1.3).\n\n"
                "Messages:\n\n"
                "* ``unterminated template directive``\n"
                "* ``unterminated template comment``\n"
                "* ``unclosed template block at end of string``\n"
                "* ``malformed template directive: <detail>``\n\n"
                "These carry no ``{ {`` hint, unlike PSS108/PSS109.  A "
                "malformed ``{%`` or ``{#`` cannot be produced by ordinary "
                "target code the way ``{{`` can, so the hint would be noise."
            ),
            patterns=(
                r"^unterminated template (directive|comment)\b",
                r"^unclosed template block\b",
                r"^malformed template directive\b",
            ),
        ),
        MarkerDef(
            id="PSS111",
            severity="error",
            summary="Template block directive out of place",
            detail=(
                "A block-closing or ``else`` directive appeared where no block "
                "was open (PSS 3.1 §4.7.1.2, Table 5).\n\n"
                "Messages:\n\n"
                "* ``template block close with no open block`` -- a ``{%%}`` "
                "too many\n"
                "* ``'else' with no preceding 'if'``\n\n"
                "Note a *duplicate* template-local declaration is reported as "
                "``PSS003`` rather than here: it is the same defect as any "
                "other duplicate declaration and shares that message shape."
            ),
            patterns=(
                r"^template block close with no open block\b",
                r"^'else' with no preceding 'if'",
            ),
        ),
        MarkerDef(
            id="PSS112",
            severity="error",
            summary="Template assignment target is not a template local",
            detail=(
                "A ``{% x = expr; %}`` directive assigned to something other "
                "than a variable declared earlier in the *same* triple-quoted "
                "string (PSS 3.1 §4.7.1.2).  Assigning to an action attribute "
                "is illegal.\n\n"
                "Message: ``template assignment target '<name>' is not "
                "declared within this template string``\n\n"
                "Nothing about the syntax distinguishes a legal template-local "
                "assignment from an illegal attribute assignment -- the only "
                "way to tell them apart is which symbol table the name "
                "resolved through.  Declare the variable with ``{% int x; %}`` "
                "inside the template, or drop the assignment."
            ),
            patterns=(r"^template assignment target\b",),
        ),
        MarkerDef(
            id="PSS113",
            severity="error",
            summary="Template expression is not of scalar type",
            detail=(
                "A ``{{ ... }}`` mustache expression is of aggregate type.  PSS "
                "3.1 §4.7.1.1 requires the substituted expression to be of "
                "scalar type -- there is no defined text for a struct, a list "
                "or a map.\n\n"
                "Message: ``template expression is not of scalar type``\n\n"
                "Classification is the same coarse categoriser the argument "
                "checks use (PSS007), and it inherits that pass's known gaps "
                "(see ``known-issues.md`` P3-X6c): member paths, subscripts, "
                "nested calls and user-defined types are classified as "
                "*unknown*, and nothing is reported for an unknown category.  "
                "So this fires on a literal aggregate and on a field whose "
                "declared type is plainly aggregate, and stays silent "
                "elsewhere rather than guessing."
            ),
            patterns=(r"^template expression is not of scalar type\b",),
        ),
        MarkerDef(
            id="PSS114",
            severity="error",
            summary="Non-pure function called from a template string",
            detail=(
                "A mustache expression or control-flow directive called a "
                "function that is not declared ``pure``.  PSS 3.1 §4.7.1.1: "
                "any function called from a template shall be pure, since "
                "expansion happens during elaboration and must not have side "
                "effects.\n\n"
                "Message: ``call to non-pure function '<name>' in a template "
                "string``\n\n"
                "Declare the function ``pure function ...`` if it is free of "
                "side effects, or compute the value outside the template and "
                "reference the result.\n\n"
                "A function declared in a ``pure component`` is pure without "
                "carrying the qualifier itself, and is not reported.  Purity "
                "follows the type a function is *declared* in, so deriving "
                "from a pure component does not make the derived component's "
                "own functions pure."
            ),
            patterns=(r"^call to non-pure function\b",),
        ),
        MarkerDef(
            id="PSS115",
            severity="error",
            summary="Non-constant template string where a constant is required",
            detail=(
                "A triple-quoted string whose special elements reference "
                "something other than constants was used where a constant "
                "expression is required -- a ``const`` field initializer, or "
                "an annotation initializer (§4.7, §7.13a).\n\n"
                "Message: ``template string with non-constant elements is not "
                "a constant expression``\n\n"
                "Reported at the point of *use*, not at the template: the same "
                "template text is perfectly legal in an exec body.  A template "
                "is constant when every expression under every special element "
                "references only constants -- ``const`` fields, enum items, "
                "type template value parameters, and template locals derived "
                "from those.  A call is never constant, even to a ``pure`` "
                "function: this front end does not evaluate function bodies."
            ),
            patterns=(
                r"^template string with non-constant elements is not a "
                r"constant expression",
            ),
        ),
        MarkerDef(
            id="PSS116",
            severity="warning",
            summary="Construct is accepted but not represented in the AST",
            detail=(
                "The grammar accepts this construct and the parse is sound, "
                "but the AST builder does not build a node for it -- or "
                "builds one that omits part of what was written.  A consumer "
                "walking the AST will not see the construct at all, or will "
                "see it without the detail named in the message.\n\n"
                "Messages take one of two forms, where *construct* is the "
                "construct name in backticks:\n\n"
                "* *construct* ``is accepted but not represented in the AST`` "
                "-- nothing is built for the construct.\n"
                "* *construct* ``is accepted but not represented in the AST:`` "
                "*detail* -- a node is built, and *detail* names the part that "
                "is dropped.\n\n"
                "This is a gap in the front end, not a problem with the "
                "source: the code is legal PSS.  There is nothing to fix in "
                "the input.  Suppress the marker if the construct is not "
                "material to how the AST is consumed; otherwise treat any "
                "analysis that depends on the named construct as unreliable.\n\n"
                "The catalogue of affected constructs, and the plan for "
                "closing them, are in ``docs/ast-coverage-gaps.md`` and "
                "``docs/ast-coverage-plan.md``.  As each construct is "
                "implemented its PSS116 disappears."
            ),
            patterns=(r"^`[^`]+` is accepted but not represented in the AST",),
        ),
        MarkerDef(
            id="PSS117",
            severity="warning",
            summary="Traversal of a deprecated dynamic constraint",
            detail=(
                "An activity traverses a ``dynamic`` constraint.  This still "
                "works, but LRM 13.1.1 deprecates dynamic constraints: \"their "
                "functionality is replaced by a generic constraint with no "
                "parameters\".\n\n"
                "Message: ``traversal of dynamic constraint 'dc' is deprecated "
                "(13.1.1); declare it as a generic constraint, "
                "'constraint dc() { ... }'``\n\n"
                "Before::\n\n"
                "    dynamic constraint dc { x > 0; }\n\n"
                "After::\n\n"
                "    constraint dc() { x > 0; }\n\n"
                "Reported where the constraint is traversed.  Traversing a "
                "*fixed* named constraint is an error (PSS018)."
            ),
            patterns=(r"^traversal of dynamic constraint '[^']*' is deprecated\b",),
        ),
        MarkerDef(
            id="PSS118",
            severity="error",
            summary="Constant initializer references a later or type-level constant",
            detail=(
                "LRM 18.2c: a constant or enum item may be referenced in the "
                "initializer of another constant only after its declaration. "
                "LRM 18.2d: a package-level constant may reference only other "
                "package-level constants.  Messages:\n\n"
                "* ``constant 'C' is used in the initializer of 'A' before its "
                "declaration on line 4; declare it first (18.2)`` (or ``enum "
                "item 'E_X' ...``, or ``... in a file given later``)\n"
                "* ``constant 'A' is used in the initializer of 'A', which is "
                "itself (18.2)``\n"
                "* ``package-level constant 'A' may reference only "
                "package-level constants; 'K' is declared in type 'C' "
                "(18.2)``\n\n"
                "Before::\n\n"
                "    package my {\n"
                "      const int A = C;\n"
                "      const int C = 3;\n"
                "    }\n\n"
                "After::\n\n"
                "    package my {\n"
                "      const int C = 3;\n"
                "      const int A = C;\n"
                "    }\n\n"
                "Across files, the order the files are given in applies, as it "
                "does for ``compile if``.  Elsewhere in a type or package, "
                "declaration order does not matter (Example 262).  A name used "
                "before its declaration in an exec or activity block is "
                "PSS002; in a type width, PSS119."
            ),
            patterns=(
                r"^(constant|enum item) '[^']*' is used in the initializer of\b",
                r"^package-level constant '[^']*' may reference only "
                r"package-level constants\b",
            ),
        ),
        MarkerDef(
            id="PSS119",
            severity="warning",
            summary="Type width references a constant declared later",
            detail=(
                "The prose under LRM Example 264 extends 18.2c to type-width "
                "expressions: a constant used in ``bit[W]`` must be declared "
                "before it.  Message: ``constant 'W' is used in a type width "
                "before its declaration on line 5; declare it first (18.2)``."
                "\n\nA warning rather than an error, because the rule is "
                "stated only in prose and existing models write it.  Move the "
                "constant's declaration above its first use."
            ),
            patterns=(r"^(constant|enum item) '[^']*' is used in a type width "
                      r"before its declaration\b",),
        ),
    ]

    def check(self, context) -> None:  # noqa: D102
        pass  # core checking is performed in C++
