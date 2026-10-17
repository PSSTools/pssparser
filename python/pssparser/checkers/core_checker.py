"""Built-in CoreChecker: metadata for parser and linker diagnostics."""
from __future__ import annotations

from pssparser.lint.catalog import CORE_EMITTED as _CORE_EMITTED_LINT

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
    #:   ``PSS001``-``PSS099``  general parse/link diagnostics
    #:   ``PSS100``-``PSS199``  PSS 3.1 language-rule diagnostics
    #:   ``PSSP...``            the tool's own diagnostics (end of the list)
    #:   ``LINT...``            core-emitted lint, defined in
    #:                          ``pssparser.lint.catalog`` and appended last
    #:
    #: ``PSS`` means an LRM violation.  The warnings and tool errors that used
    #: to share it moved out (lint-framework D-1, D-6); their ``PSS`` rows
    #: stay, ``retired``, with ``replaced_by`` naming the new code.  The
    #: internal error, once ``PSS000``, is ``PSSP000``.
    #:
    #: Core markers originate in C++, which does not carry an ID on the marker
    #: object.  The ID is recovered by matching ``patterns`` against the message
    #: text, so the regexes here and the message strings in ``src/*.cpp`` must
    #: agree.  ``tests/python/test_marker_ids.py`` pins that correspondence.
    marker_defs = [
        MarkerDef(
            id="PSS000",
            severity="error",
            summary="Internal error (moved to PSSP000)",
            status="retired",
            replaced_by=("PSSP000",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP000`` (``internal-error``). ``PSS000`` is still accepted "
                "wherever an ID is typed, and is never reused."
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
                # A named port map entry for a port the covergroup type does
                # not declare (15.2).
                r"^covergroup '[^']*' has no port named\b",
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
                # A name after one whose type did not resolve: `x.y` where
                # x's type is unknown, so y has no scope to be looked up in.
                r"^cannot resolve '.*': the enclosing scope is unknown\b",
                # A qualifier that is not a namespace (18.3): `tx::send_a`
                # for a component instance `tx` (pssc P1).
                r"^'[^']*' is an? [a-z ]+, not a type or package\b",
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
                "* ``'pkg' has no member named 'thing'``, or ``'f()' has no "
                "member named 'thing'`` for a member of a call's result; with "
                "``; did you mean 'thang'?`` when a member is spelled close "
                "to it\n"
                "* ``'this' is only valid inside a type: ...`` (``this`` in "
                "a package-level function)\n"
                "* ``'super' is only valid inside a type that has a base "
                "type, and 'S' has none`` (also ``'super;'``)\n"
                "* ``'comp' is only valid in an action declared in a "
                "component, and 'AB' is declared outside one``\n"
                "* ``'prev' is only valid in a state type or its extension, "
                "and cannot be reached as a member of 'i'``\n"
                "* ``base type 'B' has no member named 'x'`` (``super.x``)\n"
                "* ``cannot resolve 'y': the enclosing scope is unknown`` "
                "(``x[0].y`` where x's element type did not resolve)\n"
                "* ``'tx' is a component instance, not a type or package; did "
                "you mean 'tx_c'?`` -- 18.3: only a package or a type "
                "qualifies a name, so an instance, field, variable, function "
                "or symbol cannot, even where its type declares the name "
                "(9.1.3, Example 47).  The suggestion is the qualifier's "
                "declared type, offered only when it declares the name\n\n"
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
                "numeric``\n"
                "* ``argument 1 of 'g' is an aggregate literal, so parameter "
                "'s' must be declared const (LRM 20.2.3)``, and ``argument 2 "
                "of 'g' is constant 'C', so parameter 'd' must be declared "
                "const (LRM 20.2.3)`` -- a constant of aggregate type passes "
                "only to a const parameter of a PSS function (Example 291)\n"
                "* ``argument 1 of 'sum' is an array of 3 elements, but "
                "parameter 'v' is an array of 2 (LRM 8.3)``\n"
                "* ``argument 1 of 's' is a value, but parameter 'h' is a "
                "handle of action 'A'`` -- a symbol's action-handle parameter "
                "takes a handle of that action type or a subtype, or an "
                "element of an array of them (11.7)\n\n"
                "Argument types are compared only by broad category -- "
                "numeric, string, composite.  Widths, signedness and struct "
                "subtyping are deliberately not judged, except that a "
                "symbol's handle argument must be of the parameter's action "
                "type or a subtype.\n\n"
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
                "value``\n"
                "* ``an exec block returns void, so 'return' cannot take a "
                "value (LRM 20.7.5, ruling R21)`` -- 20.7.5 permits only the "
                "bare ``return;`` in an exec\n\n"
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
                "Two things are deliberately **not** compared. Parameter "
                "*names*, because PSS calls are positional and nothing "
                "requires a redeclaration to reuse them.  A ``pure`` "
                "qualifier, because LRM 20.2.6 b permits omitting it in a "
                "definition whose declaration carries it.  The ``const`` "
                "qualifier is compared: LRM 20.2.3 c makes it \"an essential "
                "part of the function signature\".  So is the platform "
                "qualifier: ``target`` on one declaration and ``solve`` on "
                "another (20.3.1, 20.4.1 b; an unqualified one may meet "
                "either).\n\n"
                "Overrides (LRM 20.2): a *static* function shadowed in a "
                "derived component may differ freely and is not reported.  An "
                "*instance* function shadowed in a derived component shall "
                "have \"the same return type and arguments\" -- const and "
                "defaults included (20.2.3 c, 20.2.4 c) -- shall not be "
                "shadowed by a static function, and a non-pure one shall not "
                "be declared pure (20.2.6):\n\n"
                "* ``'der_c::f' and the 'base_c::f' it overrides disagree "
                "about the number of parameters (1 and 3)``\n"
                "* ``static function 'der_c::f' cannot shadow the instance "
                "function 'base_c::f' (LRM 20.2)``\n"
                "* ``'der_c::f' is pure but overrides the non-pure "
                "'base_c::f' (LRM 20.2.6)``"
            ),
            patterns=(
                r"^declarations of '.*' disagree\b",
                r"^'[^']*' and the '[^']*' it overrides disagree\b",
                r"^static function '[^']*' cannot shadow the instance function\b",
                r"^'[^']*' is pure but overrides the non-pure\b",
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
            summary="Register width has no primitive access function (moved to LINT501)",
            status="retired",
            replaced_by=("LINT501",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT501`` (``reg-width-no-access-function``). "
                "``PSS016`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
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
                "Qualify the name (``lib1::s``) or import it explicitly.  "
                "The same holds for a field or type that extensions in "
                "two packages add to one type, where both packages are "
                "wildcard-imported (17.2.3): ``ambiguous reference to 'b': "
                "extensions of 'S' in package 'p' and package 'q' each "
                "declare it, and each package is imported here (17.2.3); "
                "import only one``."
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
                "(see LINT602) and a symbol may also be traversed.  Messages "
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
                "(``do S`` on a struct or component)\n"
                "* ``'s' is a symbol, not an action handle; a symbol takes no "
                "'with' constraints (11.7)`` (also ``no initializer list``): "
                "``s;`` activates a symbol, but it has no fields to constrain "
                "or set\n\n"
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
                "replace ``extends`` with ``:``.\n\n"
                "``expected ';' before '<token>'`` is also reported when a "
                "statement that could have ended with ``;`` is followed, on "
                "the next line, by a token that starts another statement: "
                "``int a = 1, b = 2`` or ``f(1)`` with no ``;`` before the "
                "next line.  The marker is on the next line's first token, "
                "since that is where the parser noticed.  When the line ends "
                "in a name, the marker moves to the end of that line instead "
                "(``expected ';' after '<name>'``)."
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
            id="PSS023",
            severity="error",
            summary="Reserved: keyword used where an identifier is expected",
            status="reserved",
            detail=(
                "Allocated for a keyword-used-as-identifier sub-case of the "
                "syntax band, which turned out to be unreachable: the case "
                "is reported as PSS022.  Reserved, not assigned."
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
            summary="Too many errors; stopped reporting further errors (moved to PSSP007)",
            status="retired",
            replaced_by=("PSSP007",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP007`` (``too-many-errors``). ``PSS029`` is still accepted "
                "wherever an ID is typed, and is never reused."
            ),
        ),

        # -- Tooling band (PSS030-PSS039), mostly retired -------------------
        #
        # The tool's own diagnostics moved to the PSSP namespace (lint-
        # framework D-6); see the PSSP section at the end of this list.  The
        # retired rows stay so that --describe explains the move and the IDs
        # are never reused.

        MarkerDef(
            id="PSS030",
            severity="warning",
            summary="A checker extension could not be loaded (moved to PSSP001)",
            status="retired",
            replaced_by=("PSSP001",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP001`` (``extension-load-failed``). ``PSS030`` is still accepted "
                "wherever an ID is typed, and is never reused."
            ),
        ),

        MarkerDef(
            id="PSS031",
            severity="warning",
            summary="Entry-point key disagrees with the checker's declared name (moved to PSSP002)",
            status="retired",
            replaced_by=("PSSP002",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP002`` (``entry-point-name-mismatch``). ``PSS031`` is still accepted "
                "wherever an ID is typed, and is never reused."
            ),
        ),

        MarkerDef(
            id="PSS032",
            severity="warning",
            summary="Extension requires a newer checker API than this build provides (moved to PSSP003)",
            status="retired",
            replaced_by=("PSSP003",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP003`` (``extension-api-too-new``). ``PSS032`` is still accepted "
                "wherever an ID is typed, and is never reused."
            ),
        ),

        MarkerDef(
            id="PSS033",
            severity="error",
            summary="Two checkers declare the same marker ID (moved to PSSP008)",
            status="retired",
            replaced_by=("PSSP008",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP008`` (``duplicate-marker-id``). ``PSS033`` is still accepted "
                "wherever an ID is typed, and is never reused."
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
        MarkerDef(
            id="PSS042",
            severity="error",
            summary="Reference left unbound (pssparser defect)",
            patterns=(
                r"\bwas left unbound by pssparser\b",
            ),
            detail=(
                "The linker finished without binding a name, although the "
                "model declares something of that name, and without saying "
                "why.  This is a defect in pssparser, not necessarily in the "
                "model: please report it together with the input.  Message:"
                "\n\n"
                "* ``'x' was left unbound by pssparser, although the model "
                "declares it: a pssparser defect, please report it``\n\n"
                "Reported by the completeness check that runs after linking "
                "(symbol-resolution plan 3.5), so that a consumer is never "
                "handed a reference with no target in silence.  It is "
                "reported only on a model with no other error; with one, an "
                "unbound name is far more likely a consequence of that error.  "
                "A name that nothing in the model declares is PSS002 instead.  "
                "Some constructs are not checked yet: covergroup bodies and "
                "port maps, instance overrides, the member names of a struct "
                "literal whose type is not known from where it is written, "
                "and a bind target past a component whose type is unknown "
                "or generic."
            ),
        ),

        MarkerDef(
            id="PSS043",
            severity="error",
            summary="Illegal package alias declaration",
            patterns=(
                r"^package alias '[^']*' is already declared in this scope\b",
                r"^package alias '[^']*' has the same name as a package\b",
            ),
            detail=(
                "LRM 18.1.4 restricts the name of a package alias "
                "(``import pkg1::a::b as p1;``).  Messages:\n\n"
                "* ``package alias 'X' is already declared in this scope; two "
                "aliases in one scope shall not share a name (18.1.4)``\n"
                "* ``package alias 'foo' has the same name as a package "
                "declared in package 'P'; rename the alias (18.1.4)``\n\n"
                "Two aliases in one lexical scope -- one ``package`` "
                "statement, component declaration or extension, or one "
                "file's global scope -- shall not have the same name; the "
                "same name in two statements of one package is legal.  An "
                "alias shall not take the name of a package declared in the "
                "same namespace in this source unit or an earlier one (Example "
                "260).  A package of that name added in a later source unit "
                "is legal, and from then on a reference finds the package "
                "rather than the alias (18.3 c.1 before c.2.i)."
            ),
        ),

        MarkerDef(
            id="PSS044",
            severity="warning",
            summary="Enum item hides a declaration of the same name (moved to LINT401)",
            status="retired",
            replaced_by=("LINT401",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT401`` (``enum-item-hides-declaration``). "
                "``PSS044`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
        ),
        MarkerDef(
            id="PSS045",
            severity="error",
            summary="Ambiguous enum item in a comparison (withdrawn; see PSS130)",
            status="retired",
            detail=(
                "Read ``a == b`` both ways, each side's type being the other "
                "side's expected type, and reported a comparison of two bare "
                "names either of which could be an item of the other's enum.  "
                "Ruling R22 gives the left side no expected type (8.4.3), so "
                "the ambiguity cannot arise: an unqualified item on the left "
                "is PSS130.  ``PSS045`` is never reused."
            ),
        ),
        MarkerDef(
            id="PSS046",
            severity="warning",
            summary="Enum item used where its enumeration type is not expected (moved to LINT101)",
            status="retired",
            replaced_by=("LINT101",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT101`` (``enum-item-type-mismatch``). "
                "``PSS046`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
        ),
        MarkerDef(
            id="PSS047",
            severity="error",
            summary="Template argument of the wrong kind",
            patterns=(
                r"^template parameter '[^']*' expects a (value|type)\b",
            ),
            detail=(
                "A template parameter is either a value parameter or a type "
                "parameter (10.3), and its argument has to be of the same "
                "kind.  A name spells a type and a constant alike, so "
                "``S<X>`` is decided by what ``X`` names: for a value "
                "parameter, ``X`` is looked up as a value -- an enum item of "
                "the parameter's enumeration type first (18.3 a), then the "
                "usual scopes -- and a type found there is reported.  "
                "Messages:\n\n"
                "* ``template parameter 'N' expects a value, but 'my_s' is a "
                "type``\n"
                "* ``template parameter 'N' expects a value, but the argument "
                "supplied is a type`` (a built-in type, ``S<int>``)\n"
                "* ``template parameter 'T' expects a type, but the argument "
                "supplied is a value`` (``S<4>`` for ``S<type T>``)\n\n"
                "A name that is not declared at all is PSS002 (``unknown "
                "identifier``)."
            ),
        ),

        MarkerDef(
            id="PSS048",
            severity="error",
            summary="Invalid struct literal member",
            patterns=(
                r"^struct literal names '[^']*'",
            ),
            detail=(
                "A struct literal names the data attributes of its context "
                "type (4.8.4): the type of the field or variable it "
                "initializes, the left-hand side of the assignment, the "
                "parameter it is passed for, the function's return type, an "
                "exec block's tag type, or the enclosing literal's member "
                "(4.8.5).  Each attribute may be named once.  Messages:\n\n"
                "* ``struct literal names 'a' more than once (4.8.4)``\n"
                "* ``struct literal names 'c1', which is not a data "
                "attribute of 'S1' (4.8.4)`` (a constraint, say)\n\n"
                "A name the context type does not declare at all is PSS002 "
                "(``'S1' has no member named 'x'``)."
            ),
        ),

        MarkerDef(
            id="PSS049",
            severity="error",
            summary="Invalid bind operand",
            patterns=(
                r"^bind names '[^']*', which is not\b",
            ),
            detail=(
                "A pool bind (12.3) names a pool, then for each target a "
                "path of component instances from the binding component, an "
                "action type of the last component reached, and an input, "
                "output or resource-claim field of that action type.  "
                "Messages:\n\n"
                "* ``bind names 'x', which is not a pool (12.3)``\n"
                "* ``bind names 'x', which is not a component instance of "
                "'C' (12.3)``\n"
                "* ``bind names 'x', which is not an action type of 'C' "
                "(12.3)``\n"
                "* ``bind names 'x', which is not an input, output or "
                "resource-claim field of 'A' (12.3)``\n\n"
                "A name that is not declared where it is looked up is PSS002 "
                "(``'C' has no member named 'x'``)."
            ),
        ),

        MarkerDef(
            id="PSS050",
            severity="error",
            summary="Invalid coverage reference",
            patterns=(
                r"^cross '[^']*' names '[^']*', which is not\b",
                r"^bins '[^']*' names '[^']*', which is not its own\b",
            ),
            detail=(
                "A cross crosses coverpoints of its covergroup, or variables, "
                "each of which is an implicit coverpoint (15.1 d, 15.4).  A "
                "bin written ``bins b = cp with (...)`` names its own "
                "coverpoint (15.3.3.3), and a cross bin its own cross "
                "(15.4.3).  Messages:\n\n"
                "* ``cross 'X' names 'f', which is not a coverpoint or a data "
                "field (15.4)``\n"
                "* ``bins 'b' names 'a', which is not its own coverpoint 'c' "
                "(15.3.3.3)``\n"
                "* ``bins 'b' names 'Y', which is not its own cross 'X' "
                "(15.4.3)``\n\n"
                "A name that is not declared at all is PSS002."
            ),
        ),

        MarkerDef(
            id="PSS051",
            severity="error",
            summary="Extension member not visible here",
            patterns=(
                r"^'[^']*' is declared by an extension of '[^']*' in .*, "
                r"(which is not|none of which is) visible here\b",
                r"^'[^']*' is an item an extension of '[^']*' in .* adds, "
                r"which is not visible here\b",
            ),
            detail=(
                "A member an extension adds to a type is accessible in the "
                "package the extension is written in, and elsewhere only "
                "where that package is wildcard-imported (17.2.3, 18.1.3).  "
                "An extension in the global scope, or in the package that "
                "declares the type, is visible wherever the type is.  "
                "Messages:\n\n"
                "* ``'b' is declared by an extension of 'S' in package 'p', "
                "which is not visible here (17.2.3); add 'import p::*;'``\n"
                "* ``'B' is an item an extension of 'E' in package 'p' adds, "
                "which is not visible here (17.2.3); add 'import p::*;'``\n\n"
                "The use still binds to the member, so later diagnostics "
                "are measured against it.  A warning in pssparser 3.1.7; an error "
                "since (symbol-resolution plan §8).  Where two imported "
                "packages each add the name, the use is ambiguous: PSS017."
            ),
        ),

        MarkerDef(
            id="PSS052",
            severity="error",
            summary="Explicit import conflicts with a declaration or import",
            patterns=(
                r"^'import [^']*;' names '[^']*', which .* already declares\b",
                r"^'[^']*' is already imported explicitly in this scope\b",
            ),
            detail=(
                "18.1.3: it shall be illegal to explicitly import an "
                "identifier the importing namespace already declares, or to "
                "explicitly import the same identifier from two different "
                "packages.  Messages:\n\n"
                "* ``'import lib::s;' names 's', which package 'p' already "
                "declares; an explicit import shall not name a declaration "
                "of the importing namespace (18.1.3)``\n"
                "* ``'s' is already imported explicitly in this scope, by "
                "'import lib1::s;'; the same name shall not be imported "
                "explicitly from two packages (18.1.3)``\n\n"
                "The namespace is every statement of a package, or a "
                "component and its extensions; two imports conflict only "
                "within one statement.  A warning in pssparser 3.1.7; an error since "
                "(plan §8).  A use of a name two explicit imports provide is "
                "PSS017."
            ),
        ),

        MarkerDef(
            id="PSS053",
            severity="warning",
            summary="Import after a declaration (moved to LINT402)",
            status="retired",
            replaced_by=("LINT402",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT402`` (``import-after-declaration``). "
                "``PSS053`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
        ),
        MarkerDef(
            id="PSS054",
            severity="error",
            summary="compile assert failed",
            patterns=(
                r"^compile assert failed\b",
            ),
            detail=(
                "19.4: a ``compile assert`` whose condition is false.  "
                "Messages:\n\n"
                "* ``compile assert failed: too wide`` -- the condition "
                "folded when the file was read; the string is the "
                "assertion's own message, when it has one\n"
                "* ``compile assert failed for 'S<64>': too wide`` -- an "
                "assertion in a generic type's body that names a template "
                "parameter (Ex. 71-73).  It has a value only in a "
                "specialization, so each specialization is checked once "
                "linked, and reported at the first use that creates it, with "
                "a related location at the assertion.  The generic itself is "
                "never checked."
            ),
        ),
        MarkerDef(
            id="PSS055",
            severity="error",
            summary="Compile-time condition cannot be evaluated",
            patterns=(
                r"^compile (if|assert) condition cannot be evaluated\b",
            ),
            detail=(
                "19.1.3, 19.4: the condition of a ``compile if`` or "
                "``compile assert`` must be determinable at compile time.  "
                "Messages:\n\n"
                "* ``compile if condition cannot be evaluated at compile "
                "time: 'X > 1'. ...`` -- it names something that is not a "
                "constant, or one declared in a later file (19.1.2)\n"
                "* ``compile assert condition cannot be evaluated for "
                "'S<4>': ...`` -- an assertion on a template parameter "
                "that does not fold in that specialization"
            ),
        ),
        MarkerDef(
            id="PSS056",
            severity="error",
            summary="Template arguments given to a type that is not generic",
            patterns=(
                r"^'.*' is not a generic type\b",
            ),
            detail=(
                "A type that declares no template parameters was written "
                "with an argument list, in a use (``t<1> f;``) or in an "
                "instance extension (``extend struct t<1>``, 17.2.6b).  "
                "Message: ``'t' is not a generic type, so it takes no "
                "template arguments``.  Remove the argument list."
            ),
        ),
        MarkerDef(
            id="PSS057",
            severity="error",
            summary="Extension of a type inside a template instance",
            patterns=(
                r"^cannot extend a type declared inside a template instance\b",
            ),
            detail=(
                "``extend struct C<2>::s``, or an ``extend struct s`` "
                "written inside ``extend component C<2>``, extends a type "
                "declared in one instance of a generic component.  pssparser "
                "does not support this.  An extension of the instance's own "
                "members (``extend component C<2> { int x; }``) is supported "
                "(17.2.6b)."
            ),
        ),
        MarkerDef(
            id="PSS058",
            severity="error",
            summary="Extension kind does not match the type",
            patterns=(
                r"^'extend \w+' names '.*', which is an? \w+\b",
            ),
            detail=(
                "An ``extend`` statement names the kind of type it extends, "
                "and LRM 17.2 requires it to agree with the type: "
                "``extend action M`` where ``M`` is a monitor, or "
                "``extend struct b`` where ``b`` is a buffer, or "
                "``extend struct e`` where ``e`` is an enum.  The message "
                "gives the kind to write.  ``extend enum s`` where ``s`` is "
                "not an enum is PSS005.  The extension's members are not "
                "added to the type."
            ),
        ),
        MarkerDef(
            id="PSS059",
            severity="error",
            summary="Cyclic inheritance",
            patterns=(
                r"^cyclic inheritance\b",
            ),
            detail=(
                "A type inherits, directly or through its base types, from "
                "itself: ``struct S : S``, or ``A : B`` and ``B : A``.  "
                "Message: ``cyclic inheritance: 'A' -> 'B' -> 'A'``, which "
                "names every type on the ring, in inheritance order.  It is "
                "reported once per ring.  Names looked up through the "
                "inheritance chain of a type on the ring are not searched past "
                "it."
            ),
        ),
        MarkerDef(
            id="PSS060",
            severity="error",
            summary="Template argument list does not match the parameters",
            patterns=(
                r"^'.*' takes \d+ template arguments?, but \d+ are given\b",
                r"^no (value|type) supplied for template parameter\b",
                r"^template type '.*' requires a template argument list\b",
            ),
            detail=(
                "A use of a generic type supplies the wrong number of template "
                "arguments (LRM 10).  Messages:\n\n"
                "* ``'array' takes 2 template arguments, but 3 are given`` -- "
                "too many\n"
                "* ``no value supplied for template parameter 'N', and it has "
                "no default`` -- too few, for a value parameter\n"
                "* ``no type supplied for template parameter 'T', and it has "
                "no default`` -- too few, for a type parameter "
                "(``list<> x;``)\n"
                "* ``template type 'P' requires a template argument list`` "
                "-- a generic named with no list at all, as the qualifier of "
                "``P::nbytes``\n\n"
                "Supply an argument for each parameter that has no default."
            ),
        ),
        MarkerDef(
            id="PSS061",
            severity="error",
            summary="Template argument does not satisfy its parameter",
            patterns=(
                r"^template parameter '.*' requires an argument of type category\b",
                r"^template parameter '.*' is restricted to '.*' and its subtypes\b",
            ),
            detail=(
                "A type argument is of the wrong kind for its parameter "
                "(LRM 10.3.2).  Messages:\n\n"
                "* ``template parameter 'T' requires an argument of type "
                "category 'struct', but the argument 'c' is of category "
                "'component'`` -- the parameter was declared ``struct T``\n"
                "* ``template parameter 'T' is restricted to 'base_s' and its "
                "subtypes, but the argument 'x_s' does not derive from "
                "'base_s'`` -- the parameter was declared ``struct T : "
                "base_s``"
            ),
        ),
        MarkerDef(
            id="PSS062",
            severity="error",
            summary="Recursive template specialization does not terminate",
            patterns=(
                r"^recursive specialization of '.*' exceeded the maximum depth\b",
            ),
            detail=(
                "Specializing a generic type specializes it again with a "
                "strictly larger argument, so the chain never reaches a "
                "specialization that already exists: ``struct S<type T> { "
                "S<S<T>> next; }``.  pssparser stops at a fixed depth and "
                "reports it at the generic's declaration.  Message: "
                "``recursive specialization of 'S' exceeded the maximum depth "
                "of N: ...``"
            ),
        ),
        MarkerDef(
            id="PSS063",
            severity="error",
            summary="Invalid override action",
            patterns=(
                r"^cannot override action '.*': no action of that name\b",
                r"^cannot override template action\b",
                r"^action '.*' must be declared 'override'",
            ),
            detail=(
                "An action declared ``override`` in a component replaces the "
                "action of that name in a base component (LRM 9.2.2).  "
                "Messages:\n\n"
                "* ``cannot override action 'A': no action of that name is "
                "declared in a base component of 'C'``\n"
                "* ``cannot override template action 'A'`` -- a generic "
                "action cannot be overridden\n"
                "* ``action 'A' must be declared 'override': 'C' declares it "
                "as an override action`` -- an action that redeclares an "
                "override action's name needs the keyword too"
            ),
        ),
        MarkerDef(
            id="PSS064",
            severity="error",
            summary="A symbol activates itself",
            patterns=(
                r"^symbol '.*' activates itself\b",
            ),
            detail=(
                "LRM 11.7: \"A symbol may activate another symbol, but symbols "
                "are not recursive and may not activate themselves.\"  The "
                "activations are the calls ``s(...)`` and the ``s;`` form of "
                "Example 120 in a symbol's body.  A cycle is reported once, at "
                "the activation that closes it, naming the chain:\n\n"
                "* ``symbol 's1' activates itself: s1 -> s2 -> s1 (11.7)``\n"
                "* ``symbol 's' activates itself: s -> s (11.7)``"
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
            summary="Unknown annotation type (annotation disregarded) (moved to LINT403)",
            status="retired",
            replaced_by=("LINT403",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT403`` (``unknown-annotation``). "
                "``PSS101`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
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
                "contents of an unknown annotation are disregarded (LINT403)."
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
            id="PSS103",
            severity="error",
            summary="Retired: annotation type declared outside package scope",
            status="retired",
            detail=(
                "Allocated for an annotation type declared outside package "
                "scope (7.13b), but the grammar reaches "
                "``annotation_declaration`` only from ``package_body_item``, "
                "so the construct is a syntax error before any linker check "
                "could run.  Never emitted, and never reused."
            ),
        ),

        MarkerDef(
            id="PSS104",
            severity="warning",
            summary="Deprecated brace-less 'compile if' branch (moved to LINT601)",
            status="retired",
            replaced_by=("LINT601",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT601`` (``deprecated-braceless-compile-if``). "
                "``PSS104`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
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
            summary="Construct is accepted but not represented in the AST (moved to PSSP101)",
            status="retired",
            replaced_by=("PSSP101",),
            detail=(
                "A diagnostic about pssparser itself, not about the "
                "model, so it moved to the ``PSSP`` namespace as "
                "``PSSP101`` (``construct-not-represented``). ``PSS116`` is still accepted "
                "wherever an ID is typed, and is never reused."
            ),
        ),
        MarkerDef(
            id="PSS117",
            severity="warning",
            summary="Traversal of a deprecated dynamic constraint (moved to LINT602)",
            status="retired",
            replaced_by=("LINT602",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT602`` (``deprecated-dynamic-constraint-traversal``). "
                "``PSS117`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
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
                "PSS002; in a type width, LINT404."
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
            summary="Type width references a constant declared later (moved to LINT404)",
            status="retired",
            replaced_by=("LINT404",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT404`` (``width-references-later-constant``). "
                "``PSS119`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
        ),
        MarkerDef(
            id="PSS120",
            severity="warning",
            summary="Exported function is a component instance function (moved to LINT301)",
            status="retired",
            replaced_by=("LINT301",),
            detail=(
                "A lint rule, not an LRM violation, so it moved to the "
                "``LINT`` namespace as ``LINT301`` (``exported-instance-function``). "
                "``PSS120`` is still accepted wherever an ID is typed -- "
                "configuration, ``-W``, ``--describe`` -- and is never "
                "reused."
            ),
        ),
        MarkerDef(
            id="PSS121",
            severity="error",
            summary="A constant or a const parameter is assigned",
            detail=(
                "LRM 7.1: \"The value of constant fields can be read but not "
                "modified. A constant cannot appear on the left-hand side of "
                "the assignment operator\", and \"If the constant is of "
                "aggregate type, its elements are constants too.\"  LRM "
                "20.2.3: a const parameter \"cannot be changed in the "
                "function body\".  Messages:\n\n"
                "* ``constant 'C' cannot be assigned: a constant cannot appear "
                "on the left of an assignment (LRM 7.1)``\n"
                "* ``an element or member of constant 'TBL' cannot be "
                "assigned: a constant's elements are constants too (LRM "
                "7.1)``\n"
                "* ``parameter 'x' is const, so its value cannot be changed in "
                "the function body (LRM 20.2.3)``\n"
                "* ``an element or member of const parameter 's' cannot be "
                "changed in the function body (LRM 20.2.3)``\n\n"
                "A compound assignment (``C += 1``) is an assignment.  Passing "
                "a constant of aggregate type to a non-const parameter is "
                "PSS006."
            ),
            patterns=(
                r"^constant '[^']*' cannot be assigned\b",
                r"^an element or member of constant '[^']*' cannot be assigned\b",
                r"^parameter '[^']*' is const, so its value cannot be changed\b",
                r"^an element or member of const parameter '[^']*' cannot be "
                r"changed\b",
            ),
        ),
        MarkerDef(
            id="PSS122",
            severity="error",
            summary="Sub-string on the left of an assignment",
            detail=(
                "LRM 7.6.2: \"The sub-string operator shall not be used on the "
                "left-hand side of an assignment operator.\"  An index or a "
                "slice of a string is a sub-string (8.6.3), so ``s[0] = "
                "\"x\"`` is an error; assign the whole string instead.  An "
                "element of an array of strings is not a sub-string: "
                "``ss[1] = \"x\"`` is legal."
            ),
            patterns=(
                r"^a sub-string of '[^']*' on the left of an assignment\b",
            ),
        ),
        MarkerDef(
            id="PSS123",
            severity="error",
            summary="A foreach changes its index, iterator or collection",
            detail=(
                "LRM 20.7.8 g: \"The index and iterator variables are "
                "read-only. Their values shall not be changed within the "
                "foreach body. It shall be an error to change the contents of "
                "the iterated collection variable with[in] the foreach body.\" "
                " An assignment to the collection or to what holds it, and a "
                "call of a method that changes it (``push_back``, ``insert``, "
                "``delete``, ``clear``, ...), are reported.  An assignment to "
                "an element is not: the LRM's own Example 291 assigns "
                "``dst[i]`` in ``foreach (dst[i])``; nor is a member of the "
                "iterator, which aliases the element (20.7.8 c), only the "
                "iterator written whole.  Messages:\n\n"
                "* ``foreach index variable 'i' is read-only and cannot be "
                "changed in the foreach body (LRM 20.7.8 g)``\n"
                "* ``foreach iterator variable 'e' is read-only ...``\n"
                "* ``'w' is the collection this foreach iterates, so it cannot "
                "be changed in the foreach body (LRM 20.7.8 g)``"
            ),
            patterns=(
                r"^foreach (index|iterator) variable '[^']*' is read-only\b",
                r"^'[^']*' is the collection this foreach iterates\b",
            ),
        ),
        MarkerDef(
            id="PSS124",
            severity="error",
            summary="break or continue outside a loop",
            detail=(
                "LRM 20.7.11 b: \"break and continue may only appear within "
                "loop statements (repeat-count, repeat-while or foreach). "
                "Within a loop, break and continue may be nested in "
                "conditional branch or match statements.\""
            ),
            patterns=(
                r"^'(break|continue)' may only appear within a loop statement\b",
            ),
        ),
        MarkerDef(
            id="PSS125",
            severity="error",
            summary="A match statement has more than one default branch",
            detail=(
                "LRM 20.7.10 f (procedural) and 11.4.6 f (activity): \"The "
                "default branch is optional. There may be at most one default "
                "branch in the match statement.\"  The second and any later "
                "``default`` is reported."
            ),
            patterns=(
                r"^a match statement may have at most one default branch\b",
            ),
        ),
        MarkerDef(
            id="PSS126",
            severity="error",
            summary="A cast from or to a type that cannot be cast",
            detail=(
                "LRM 7.12: \"Expressions of types int, bit, bool, enum, or "
                "floating-point type can be changed to another type in this "
                "list by using a cast operator. In addition, an expression of "
                "a reference type can be changed to a compatible reference "
                "type.\"  7.12.1: \"A type_identifier specified as a "
                "casting_type shall refer to a numeric, Boolean, enumeration, "
                "or reference type\", and a) \"A numeric, Boolean, or "
                "enumeration value can only be cast to another numeric, "
                "Boolean or enumeration type.\"  Messages:\n\n"
                "* ``a cast to struct p_s: a casting type shall be a numeric, "
                "Boolean, enumeration or reference type (LRM 7.12.1)``\n"
                "* ``a cast from chandle: only a numeric, Boolean or "
                "enumeration value, or a reference, can be cast (LRM "
                "7.12)``\n\n"
                "A cast from a chandle, a string, a struct or a collection is "
                "illegal only because 7.12 does not list it."
            ),
            patterns=(
                r"^a cast to .*: a casting type shall be\b",
                r"^a cast from .*: only a numeric, Boolean or enumeration value\b",
            ),
        ),
        MarkerDef(
            id="PSS127",
            severity="error",
            summary="'in' with a range list and a non-scalar left side",
            detail=(
                "LRM 8.5.9.1: \"The left-hand side shall not be an "
                "unqualified enum_item (see 7.5) or an aggregate literal\", "
                "and \"If the expression on the left-hand side is of a scalar "
                "type, the right-hand side may be an open_range_list or a "
                "collection_expression. Otherwise, the right-hand side shall "
                "be a collection_expression.\"  ``p in [1]`` with ``p`` a "
                "struct is an error; ``p in list_of_p`` is legal."
            ),
            patterns=(
                r"^the left side of 'in' shall not be an aggregate literal\b",
                r"^the left side of 'in' is .*, not a scalar\b",
            ),
        ),
        MarkerDef(
            id="PSS128",
            severity="error",
            summary="An operator applied to an array of components or actions",
            detail=(
                "LRM 7.9.2: arrays of modeling elements may be indexed with "
                "``[]``, \"However, other operators and methods do not apply "
                "to these arrays, unless otherwise specified\" -- ``size()``, "
                "``foreach`` and ``in`` are.  ``s == t`` and ``s = t`` on "
                "arrays of components are reported."
            ),
            patterns=(
                r"^'[!=]=' does not apply to an array of components or actions\b",
                r"^an array of components or actions cannot be assigned\b",
            ),
        ),
        MarkerDef(
            id="PSS129",
            severity="error",
            summary="A function signature uses a component, action or object type without ref",
            detail=(
                "LRM 20.2.2: \"Functions shall not return action types, "
                "component types, or flow/resource object types without the "
                "ref modifier\", and \"Functions shall not have parameters "
                "of action types, component types, or flow/resource object "
                "types without the ref modifier.\"  Messages:\n\n"
                "* ``function 'g' returns component type 'sub_c' without "
                "'ref': a function shall not (LRM 20.2.2)``\n"
                "* ``parameter 'b' of 'f' has flow object type 'b_s' without "
                "'ref': a function shall not (LRM 20.2.2)``"
            ),
            patterns=(
                r"^function '[^']*' returns .* type '[^']*' without 'ref'",
                r"^parameter '[^']*' of '[^']*' has .* type '[^']*' without 'ref'",
            ),
        ),
        MarkerDef(
            id="PSS130",
            severity="error",
            summary="Unqualified enum item where its enumeration type is not expected",
            detail=(
                "An enum item belongs to its enumeration type's scope, not to "
                "the scope that declares the enum (7.5.1 g).  Unqualified, it "
                "is found only where the expression's expected type is that "
                "enumeration type (7.5.1 i, 8.4.3, 18.3 a): an assignment or "
                "initializer, a call argument, a ``return``, the RIGHT side "
                "of ``==``/``!=``, the values of ``in``, a cast to the enum, "
                "and the arms of ``?:``.  The left side of ``==`` has no "
                "expected type, and 8.5.9.1: \"The left-hand side [of in] "
                "shall not be an unqualified enum_item\".  pssparser finds "
                "an item of an enclosing scope's enum anyway, when the name "
                "means nothing else, and reports it: an error by ruling R22 "
                "(it was the warning LINT101).  Messages:\n\n"
                "* ``enum item 'ORANGE' is used where no enumeration type is "
                "expected (7.5.1 i, 8.4.3; ruling R22); qualify it as "
                "'color_e::ORANGE'``\n"
                "* ``enum item 'RED' is used where 'mode_e' is expected, but "
                "it is an item of 'color_e' (7.5.1 i, 8.4.3; ruling R22); "
                "qualify it as 'color_e::RED'``\n\n"
                "Qualify the item.  LRM Example 37: ``print_num((int)ORANGE)`` "
                "is an error, because the cast's type is ``int``."
            ),
            patterns=(
                r"^enum item '[^']*' is used where (no enumeration type is expected|"
                r"'[^']*' is expected, but it is an item of)\b",
            ),
        ),
        MarkerDef(
            id="PSS131",
            severity="error",
            summary="An operand of a type its operator does not take",
            detail=(
                "LRM 8.4 Table 10 says which operand types each operator takes "
                "(Table 9 for the compound assignments): ``-``, ``+``, ``*``, "
                "``/``, ``**`` and the relational operators take numeric "
                "operands (8.5.1, 8.5.2: \"may be applied only to numeric "
                "operands\"); ``%``, ``~``, the bitwise, reduction and shift "
                "operators, ``&=``, ``|=``, ``<<=`` and ``>>=`` take integer "
                "ones; ``!``, ``&&`` and ``||`` Boolean ones.  So a "
                "relational operator on bool or string, the chained ``a < b < "
                "c``, a bitwise operator on bool, ``%`` on a float and ``+`` "
                "on strings are errors.  7.7: a chandle is compared only with "
                "a chandle, and \"the only literal value with which it may be "
                "compared is 0\".  An enum operand is not judged here (7.5.1 "
                "permits it in assignment and equality).  Messages:\n\n"
                "* ``operator '<' takes numeric operands, not bool (LRM 8.4 "
                "Table 10, 8.5.2)``\n"
                "* ``a chandle can be compared only with a chandle or the "
                "literal 0, not int (LRM 7.7)``"
            ),
            patterns=(
                r"^operator '[^']*' takes (numeric|integer|Boolean) operands, not\b",
                r"^a chandle can be compared only with a chandle or the literal 0\b",
            ),
        ),
        MarkerDef(
            id="PSS132",
            severity="error",
            summary="A condition that is not Boolean",
            detail=(
                "The condition of ``if`` (20.7.9), ``while`` and ``repeat ... "
                "while`` (20.7.7 a: \"expression shall be of type bool\") and "
                "of ``?:`` (8.5.8: \"cond_predicate shall be of Boolean "
                "type\") is a Boolean.  ``if (x)`` with an integer ``x`` is "
                "an error; write ``if (x != 0)``."
            ),
            patterns=(
                r"^the condition of .* shall be of Boolean type, not\b",
            ),
        ),
        MarkerDef(
            id="PSS133",
            severity="error",
            summary="null assigned to what is not a reference",
            detail=(
                "LRM 8.3: the right side of an assignment shall be "
                "assignment-compatible with the left; ``null`` is the value of "
                "a reference (7.10).  ``int y = null;`` is an error.  A chandle "
                "is not judged."
            ),
            patterns=(
                r"^null cannot be assigned to .*: only a reference takes null\b",
            ),
        ),
        MarkerDef(
            id="PSS134",
            severity="error",
            summary="Enum item values: a duplicate, or outside the base type",
            detail=(
                "LRM 7.5.1 e: \"Each enum_item shall have a distinct integer "
                "value\" -- across the declaration and its extensions.  7.5.1 "
                "c: with a base type, \"It shall be an error to explicitly "
                "assign a value which does not belong to the base type\" (a "
                "negative value with an unsigned base, say), and to give an item "
                "no value when the previous one has the base type's greatest "
                "value.  7.5.1: the base type \"shall not have a value "
                "domain\".  An item whose value does not fold here (one defined "
                "by another item) ends the check for its enum.  Messages:\n\n"
                "* ``enum item 'B' has the value 1, as 'A' does: each enum item "
                "shall have a distinct value (LRM 7.5.1 e)``\n"
                "* ``enum item 'A' has the value -1, which is not a value of the "
                "base type bit[4] (LRM 7.5.1 c)``\n"
                "* ``enum item 'B' has no value of its own, and the item before "
                "it has the greatest value of the base type bit[2] (LRM 7.5.1 "
                "c)``\n"
                "* ``the base type of enum 'h_e' shall not have a value domain "
                "(LRM 7.5.1)``"
            ),
            patterns=(
                r"^enum item '[^']*' has the value -?\d+, as '[^']*' does\b",
                r"^enum item '[^']*' has the value -?\d+, which is not a value of the base type\b",
                r"^enum item '[^']*' has no value of its own, and the item before it\b",
                r"^the base type of enum '[^']*' shall not have a value domain\b",
            ),
        ),
        MarkerDef(
            id="PSS135",
            severity="error",
            summary="A variable of an enum with no items",
            detail=(
                "LRM 7.5.1 j: an enum may be declared with no items and given "
                "them in extensions, but \"It shall be illegal to declare an "
                "enumeration variable whose type contains no enum_items across "
                "its initial definition and extensions.\""
            ),
            patterns=(
                r"^'[^']*' is a variable of enum '[^']*', which has no items\b",
            ),
        ),
        MarkerDef(
            id="PSS136",
            severity="error",
            summary="A generic or varargs parameter of a user-written function",
            detail=(
                "LRM 20.2.5: generic parameters (``type``, or a type category "
                "such as ``struct`` or ``ref action``) and varargs parameters "
                "(``...``) \"are used for the declaration of functions whose "
                "definition is built into implementations\", the core library "
                "among them.  Ruling R23: only a core-library function may "
                "have one -- not a function with a PSS body, not an imported "
                "one, not a bodiless declaration (so Examples 293 and 294, "
                "written in a user model, are errors)."
            ),
            patterns=(
                r"^parameter '[^']*' of '[^']*' is (varargs|generic), which only a "
                r"core-library function may have\b",
            ),
        ),
        MarkerDef(
            id="PSS137",
            severity="error",
            summary="An import or export signature type the foreign mapping does not take",
            detail=(
                "LRM 20.4.1 c restricts an imported function's parameters and "
                "result to bit/int of at most 64 bits, bool, enum, string, "
                "chandle, struct, an array of those (sub-arrays included) and "
                "a list of those but strings and chandles.  20.4.2.1 restricts "
                "an exported function's to bit/int of at most 64 bits, bool, "
                "enum, float32/float64, string, chandle and struct -- and g) a "
                "struct parameter shall be declared ``const``.  An exported "
                "component *instance* function is an extension (LINT301) "
                "that 20.4.2.1 does not govern, and is not judged.  "
                "Messages:\n\n"
                "* ``parameter 'v' of imported function 'put' has type "
                "bit[65], which an import cannot take (LRM 20.4.1 c)``\n"
                "* ``parameter 'p' of exported function 'sf' is a struct, so "
                "it shall be declared const (LRM 20.4.2.1 g)``"
            ),
            patterns=(
                r"^parameter '[^']*' of (imported|exported) function '[^']*' has "
                r"type .*, which an? (import|export) cannot take\b",
                r"^(imported|exported) function '[^']*' returns .*, which an? "
                r"(import|export) cannot\b",
                r"^parameter '[^']*' of exported function '[^']*' is a struct, so "
                r"it shall be declared const\b",
            ),
        ),

        # -- PSSP: the tool's own diagnostics (lint-framework D-6) ----------
        #
        # PSSP000  internal error (a defect in pssparser)
        # PSSP0xx  extensions, configuration, marker IDs and run limits
        # PSSP1xx  parser coverage: constructs accepted but not represented
        # PSSP2xx  lint infrastructure (rule metadata, waivers, baselines)
        #
        # Every PSSP marker has tier "tool": no lint profile selects or hides
        # it, and the ownership filter and baselines never drop it.  Most
        # carry their code directly (set in Python, or by C++ for PSSP000 and
        # PSSP007), so they declare no `patterns`.  PSSP000 and PSSP101 are
        # also pattern-matched, at the position of their retired PSS000 and
        # PSS116 rows, so pattern precedence is unchanged.

        MarkerDef(
            id="PSSP000",
            name="internal-error",
            tier="tool",
            aliases=("PSS000",),
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
            id="PSSP001",
            name="extension-load-failed",
            tier="tool",
            aliases=("PSS030",),
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
                "pssparser's. In CI, ``-Werror=PSSP001`` makes a failed "
                "extension fatal, which is usually what you want."
            ),
        ),

        MarkerDef(
            id="PSSP002",
            name="entry-point-name-mismatch",
            tier="tool",
            aliases=("PSS031",),
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
            id="PSSP003",
            name="extension-api-too-new",
            tier="tool",
            aliases=("PSS032",),
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
            id="PSSP004",
            name="deprecated-alias",
            tier="tool",
            severity="info",
            summary="An old marker ID was used where an ID is accepted",
            detail=(
                "A configuration key, ``-W`` flag or other ID-accepting "
                "input named a code that has moved -- for example "
                "``PSS104``, which is now ``LINT601``.  The old code still "
                "works: it is rewritten to the new one, and this note says "
                "so once per spelling, naming where it was written.  Update "
                "the input to the new ID to silence the note.\n\n"
                "Codes move when their meaning is reclassified: a warning "
                "about legal code is lint (``LINT``), and a diagnostic about "
                "pssparser itself is ``PSSP``; ``PSS`` is kept for LRM "
                "violations."
            ),
        ),

        MarkerDef(
            id="PSSP005",
            name="reserved-namespace",
            tier="tool",
            severity="error",
            summary="A checker declares a marker ID in a reserved namespace",
            detail=(
                "The ``PSS``, ``LINT``, ``PSSP`` and ``PSSX`` namespaces "
                "belong to pssparser, with or without a team qualifier "
                "(``PSS-ACME001`` is refused too).  A checker from an "
                "installed extension that declares an ID in one of them is "
                "not registered; the rest of its extension still loads.  "
                "Choose a namespace of your own -- two to five capital "
                "letters, then three digits (``PRC001``)."
            ),
        ),

        MarkerDef(
            id="PSSP006",
            name="malformed-marker-id",
            tier="tool",
            severity="warning",
            summary="A checker declares a marker ID that does not fit the ID grammar",
            detail=(
                "Marker IDs are a namespace of two to five capital letters, "
                "optionally followed by ``-`` and a team of two to five more, "
                "then three digits (``PRC001``, ``ACME-NET001``).  An ID that "
                "does not fit still loads, for now, but cannot be selected by "
                "namespace or band and will be refused in a later release.  "
                "Rename it."
            ),
        ),

        MarkerDef(
            id="PSSP007",
            name="too-many-errors",
            tier="tool",
            aliases=("PSS029",),
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

        MarkerDef(
            id="PSSP008",
            name="duplicate-marker-id",
            tier="tool",
            aliases=("PSS033",),
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
                "in the extension: pick an unused namespace -- two to five "
                "capital letters, then three digits (``PRC001``).  The "
                "``PSS``, ``LINT``, ``PSSP`` and ``PSSX`` namespaces belong "
                "to pssparser (``PSSP005``)."
            ),
        ),

        MarkerDef(
            id="PSSP101",
            name="construct-not-represented",
            tier="tool",
            aliases=("PSS116",),
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
                "implemented its PSSP101 disappears."
            ),
            patterns=(r"^`[^`]+` is accepted but not represented in the AST",),
        ),

        MarkerDef(
            id="PSSP201",
            name="bad-rule-metadata",
            tier="tool",
            severity="warning",
            summary="A lint rule's metadata is invalid",
            detail=(
                "A ``MarkerDef`` with lint metadata breaks one of the rules "
                "in the plug-in guide's *Rule metadata* section: a name that "
                "is not unique or not kebab-case, a tier, family or level "
                "outside its closed set, a ``LINT`` ID with no tier, a "
                "``nursery`` rule with no ``since``, a fix with no example "
                "showing it, or a severity that differs from the tier's "
                "default without a ``Severity:`` paragraph in ``detail``.  "
                "The message names the field.  The checker is not "
                "registered."
            ),
        ),

        # -- Source waivers (docs/waivers.rst).  A source waiver cannot
        # waive these four: it could otherwise hide the warning that it is
        # itself unused.  [severity] can re-level them.
        MarkerDef(
            id="PSSP202",
            name="unused-waiver",
            tier="tool",
            severity="warning",
            summary="A waiver matched no diagnostic",
            detail=(
                "A ``@lint_pkg::waive`` annotation or ``// pssparser waive`` "
                "comment covered no diagnostic, although a rule it names ran "
                "on this run.  Usually the code it excused has been fixed: "
                "delete the waiver.  A waiver for a rule that did not run -- "
                "turned off, outside the lint profile, or from a checker "
                "that was not loaded -- is not reported, so a waiver does "
                "not flap with the configuration."
            ),
        ),
        MarkerDef(
            id="PSSP203",
            name="unknown-waiver-rule",
            tier="tool",
            severity="warning",
            summary="A waiver names no known rule",
            detail=(
                "The ``id`` of a ``@lint_pkg::waive`` annotation, or an ID in "
                "a ``// pssparser waive`` comment, is not a marker ID, rule "
                "name or selector that any loaded checker declares.  Usually "
                "a typo; the message suggests the nearest match.  A rule from "
                "an extension that is not installed looks the same."
            ),
        ),
        MarkerDef(
            id="PSSP204",
            name="waiver-on-error",
            tier="tool",
            severity="warning",
            summary="A waiver names an error that cannot be waived",
            detail=(
                "An LRM error means the model was not built, so waiving it "
                "would report success for a run that compiled nothing.  The "
                "waiver has no effect.  Fix the error, and delete the "
                "waiver."
            ),
        ),
        MarkerDef(
            id="PSSP205",
            name="waiver-without-reason",
            tier="tool",
            severity="warning",
            summary="A waiver gives no reason",
            detail=(
                "Every waiver says why: ``.reason`` in the annotation, or the "
                "text after ``:`` in the comment.  The waiver still applies; "
                "this asks for the reason."
            ),
        ),

        # -- Baselines (docs/lint.rst, "Adopting lint on an existing
        # model").
        MarkerDef(
            id="PSSP206",
            name="stale-baseline-entry",
            tier="tool",
            severity="info",
            summary="A baseline entry matched fewer findings than it recorded",
            detail=(
                "The baseline records a finding that this run no longer "
                "reports: it was fixed, or the code changed enough to be a "
                "different finding.  The diagnostic points at the entry in "
                "the baseline file.  Rewrite the baseline with "
                "``--write-baseline`` so that the finding cannot come back "
                "unnoticed.  It is reported only for an entry whose file was "
                "checked and whose rule ran, so checking a subset of the "
                "files, or turning a rule off, does not make entries stale."
            ),
        ),

        # -- Rule files (pss-rules-format.md §6.3; lint-core-plan.md §6).
        # Reported by the C++ rule loader, located in the rule file.  A bad
        # rule is left out; the rest of its file loads.
        MarkerDef(
            id="PSSP210",
            name="rule-file-structure",
            tier="tool",
            severity="error",
            summary="A rule file is not a pss-rules file",
            detail=(
                "The file is refused as a whole: it is empty, its top level "
                "is not a mapping with the single key ``pss-rules``, "
                "``pss-rules`` is not a mapping or has no ``rules`` list, or "
                "it declares a ``version`` this pssparser does not read.  A "
                "file of a later version is never partly loaded; the message "
                "names both versions."
            ),
        ),
        MarkerDef(
            id="PSSP211",
            name="rule-unknown-key",
            tier="tool",
            severity="error",
            summary="A rule file has a key the format does not define",
            detail=(
                "Rule files are strict: an unknown key is an error, never "
                "ignored, so a misspelt ``wher:`` cannot leave a rule "
                "firing on every node.  The message suggests the nearest "
                "key.  A key in a rule disables that rule.  Keys starting "
                "with ``x-`` are the author's own and are ignored.  Settings "
                "beside ``pss-rules`` at the top level belong under it."
            ),
        ),
        MarkerDef(
            id="PSSP212",
            name="rule-field-invalid",
            tier="tool",
            severity="error",
            summary="A rule field is missing or has a wrong value",
            detail=(
                "A required field is missing (``id``, ``name``, ``tier``, "
                "``summary``, ``message``, ``match``; ``since`` in the "
                "nursery tier; ``family``, ``doc`` and examples that fire "
                "and do not fire in a built-in rule), or a field has the "
                "wrong type or a value outside its set.  This includes "
                "``options`` specs, ``let`` names, example expectations, a "
                "field under ``defaults`` that cannot be defaulted, and "
                "``fix``, which is reserved.  The rule is not loaded."
            ),
        ),
        MarkerDef(
            id="PSSP213",
            name="rule-unknown-kind",
            tier="tool",
            severity="error",
            summary="A rule's match names an unknown node kind",
            detail=(
                "``match.kind``, ``inside`` and ``not_inside`` name AST "
                "classes from the schema (``ast/*.yaml``), as ``ExprBin`` "
                "or ``Action``.  The message suggests the nearest class.  "
                "The rule is not loaded."
            ),
        ),
        MarkerDef(
            id="PSSP214",
            name="rule-expression-syntax",
            tier="tool",
            severity="error",
            summary="A rule expression is not valid CEL",
            detail=(
                "A ``where``, ``report``, ``let``, ``define`` or message "
                "``${...}`` expression does not parse, or uses a part of "
                "CEL that pss-rules leaves out (see "
                "``docs/lint-functions.rst``).  The position is mapped back "
                "to the line and column in the rule file.  Write CEL in a "
                "block scalar (``>-``) or a quoted string, since ``:``, "
                "``#`` and ``?`` would otherwise trip YAML.  In a message, "
                "``$${`` is a literal ``${``."
            ),
        ),
        MarkerDef(
            id="PSSP215",
            name="rule-expression-type",
            tier="tool",
            severity="error",
            summary="A rule expression does not type-check",
            detail=(
                "Every expression has a static type, checked when the rule "
                "loads: an unknown name, field, function or option, a wrong "
                "argument type, ``where`` that is not a bool, ``report`` that "
                "is not a list of nodes, or a message interpolation that is "
                "not a string, number, bool or node.  The rule is not loaded."
            ),
        ),
        MarkerDef(
            id="PSSP216",
            name="rule-expression-limit",
            tier="tool",
            severity="error",
            summary="A rule expression exceeds a limit",
            detail=(
                "Comprehensions nest more than two deep in one expression "
                "or helper (move the inner part into a ``define:`` helper), "
                "``define:`` helpers call each other in a cycle (the message "
                "gives the path), or a regular expression is outside the "
                "supported RE2 syntax.  These limits keep every rule's run "
                "time bounded.  The rule is not loaded."
            ),
        ),
        MarkerDef(
            id="PSSP217",
            name="rule-id-conflict",
            tier="tool",
            severity="error",
            summary="A rule's ID or name is reserved or already taken",
            detail=(
                "A site rule file may not use the ``PSS``, ``PSSP``, "
                "``PSSX`` or ``LINT`` namespaces, with or without a team "
                "qualifier (``LINT-NET001`` is refused too); a built-in rule "
                "file uses ``LINT`` only.  Across every loaded rule file and "
                "extension, a rule's ID and aliases are unique among IDs and "
                "aliases, and its name among names; the message names the "
                "other rule's file and line.  Team namespaces are separate: "
                "``ACME-NET001`` and ``ACME-DMA001`` do not clash.  The rule "
                "is not loaded."
            ),
        ),
        MarkerDef(
            id="PSSP218",
            name="rule-file-yaml",
            tier="tool",
            severity="error",
            summary="A rule file is not valid YAML for pss-rules",
            detail=(
                "A YAML syntax error, a duplicate key, a tag (``!!str``), or "
                "more than one document in the file.  The file is refused as "
                "a whole.  Rule files use YAML 1.2 core-schema scalars: "
                "``yes``, ``no``, ``on`` and ``off`` are strings."
            ),
        ),
        MarkerDef(
            id="PSSP219",
            name="rule-helper-shadowed",
            tier="tool",
            severity="info",
            summary="A rule's helper shadows the file's helper of the same name",
            detail=(
                "A ``define:`` helper of a rule has the name of a file-level "
                "helper, so within that rule it replaces the file's.  That "
                "may be intended; rename one of them if it is not."
            ),
        ),

        # -- Rule runs (lint-core-plan.md C5.3; lint-rule-expressions.md §5).
        # Reported by the C++ lint runner, located in the model.
        MarkerDef(
            id="PSSP220",
            name="rule-evaluation-error",
            tier="tool",
            severity="warning",
            summary="A lint rule failed while evaluating",
            detail=(
                "A rule's ``where``, ``report`` or message expression "
                "evaluated to an error on a node: most often a field read "
                "through an unset one (``node.super_t.elems`` on a type "
                "with no base), which a rule guards with ``has()`` or "
                "``.?``.  The message names the rule, the expression and "
                "the node.  The rule is skipped for the rest of that file, "
                "once; the other rules still run.  A finding whose message "
                "failed is kept, with ``?`` in place of the failed part.  "
                "The model is not at fault: fix the rule, or turn it off."
            ),
        ),
        MarkerDef(
            id="PSSP221",
            name="rule-budget-exceeded",
            tier="tool",
            severity="warning",
            summary="A lint rule used up its evaluation budget for a file",
            detail=(
                "Each rule may spend a fixed number of evaluation steps on "
                "each file, counted across every node it matches, so a "
                "costly rule cannot stall the editor.  A rule that runs out "
                "is skipped for the rest of that file; the findings it "
                "already made stand, and the other rules still run.  The "
                "message names the rule and the node it was evaluating.  "
                "Make the rule cheaper: a narrower ``match``, or a "
                "``where`` that rejects early."
            ),
        ),
        MarkerDef(
            id="PSSP222",
            name="rule-example-failed",
            tier="tool",
            severity="error",
            summary="A lint rule's example does not give the findings it expects",
            detail=(
                "``pssparser --check-rules`` runs each rule's ``examples:``: "
                "every example is parsed and linked on its own, and only its "
                "rule runs.  The rule must report exactly where the "
                "example's ``// expect:`` comments say, and nowhere else; an "
                "example with no ``expect`` must report nothing.  An example "
                "that does not parse or link, or on which the rule fails, "
                "fails too.  The marker is at the example in the rule file, "
                "and its message gives the position in the example's text.  "
                "Fix the rule or the example: an example is the rule's "
                "documentation, so the two must agree."
            ),
        ),
        MarkerDef(
            id="PSSP223",
            name="rule-unknown-type",
            tier="tool",
            severity="info",
            summary="A lint rule names a type the model does not have",
            detail=(
                "A rule's ``type_named`` or ``derives_from`` names a PSS type "
                "(``acme::claim_s``) that is not in the model being checked: "
                "a typo, or a package that was not compiled in.  The rule "
                "still runs, with ``type_named`` giving ``optional.none()`` "
                "and ``derives_from`` false for that name, so it may report "
                "nothing.  The note is given once per rule and name, at the "
                "node the rule was evaluating when it first asked.  Fix the "
                "name, or add the package's files to the run."
            ),
        ),
        MarkerDef(
            id="PSSP230",
            name="lint-skipped",
            tier="tool",
            severity="info",
            summary="Lint did not run because the model has errors",
            detail=(
                "Lint rules run only on a model that parsed, linked and "
                "passed the semantic checks without an error, since a rule "
                "on a broken model would report noise.  The message gives "
                "the number of errors.  Fix them, and lint runs."
            ),
        ),
        MarkerDef(
            id="LINT101",
            name="enum-item-type-mismatch",
            tier="suspicious",
            family="constraint",
            since="2026.1",
            aliases=("PSS046",),
            severity="warning",
            status="retired",
            summary="Enum item used where its enumeration type is not expected (now PSS130)",
            detail=(
                "Retired: ruling R22 made this warning an error, reported as "
                "``PSS130`` (it had moved here from ``PSS046``).  ``LINT101`` "
                "is still accepted wherever an ID is typed -- configuration, "
                "``-W``, ``--describe`` -- and is never reused."
            ),
        ),
    ] + list(_CORE_EMITTED_LINT)

    def check(self, context) -> None:  # noqa: D102
        pass  # core checking is performed in C++
