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
    #:   ``PSS001``-``PSS099``  general parse/link diagnostics
    #:   ``PSS100``-``PSS199``  PSS 3.1 language-rule diagnostics
    #:
    #: Core markers originate in C++, which does not carry an ID on the marker
    #: object.  The ID is recovered by matching ``patterns`` against the message
    #: text, so the regexes here and the message strings in ``src/*.cpp`` must
    #: agree.  ``tests/python/test_marker_ids.py`` pins that correspondence.
    marker_defs = [
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
                r"\bhas no member named\b",
                # The same failure as the line above, reached through the
                # *unqualified* path. The two spellings are one diagnosis and
                # must carry one code.
                r"^failed to find elem\b",
            ),
            detail=(
                "The linker could not resolve a named type, identifier, or "
                "method.  Messages include patterns such as:\n\n"
                "* ``unknown type 'Foo'``\n"
                "* ``unknown type 'Foo' in 'pkg'`` (the name is not in the "
                "qualifying package or scope)\n"
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
                "* ``function 'f' is already imported``\n\n"
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
            patterns=(r"^cannot extend unknown\b",),
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
            patterns=(
                r"^too few arguments\b",
                r"^too many arguments\b",
                r"^call to '.*' expects\b",
                r"^no overload of '.*' accepts\b",
                r"^'.*' is not a function; it is\b",
                r"^'.*' is not a function",
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
            patterns=(
                r"^declarations of '.*' disagree\b",
                r"\bis given a default value by more than one declaration\b",
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

        # -- Syntax-error sub-band (PSS020-PSS029) ---------------------------
        #
        # PSS011-PSS019 are held as general-band headroom. Unlike PSS001-PSS010
        # above, these markers carry their own `code` from the C++ side
        # (AstBuilderInt::syntaxError / rewriteSyntaxError classifies at the
        # point the message is built), so `patterns` is deliberately left
        # empty -- there is nothing for _assign_core_code to match, and a test
        # in test_marker_ids.py asserts it never fires for one of these IDs.
        # PSS027 is reserved for lexer-originated errors and is not emitted
        # yet: the lexer does not install AstBuilderInt as its error listener
        # (only the parser does), so a lexical error currently goes to
        # stderr via ANTLR's default listener and never reaches a marker at
        # all -- see the corpus's `KNOWN_ACCEPTED["pathological/lone_backslash.pss"]`
        # (defect U-9). PSS027 stays reserved until that listener wiring (and
        # the exit-status gap it is tangled up with) is fixed. PSS023 is also
        # reserved, not assigned: see PSS022's detail for why the keyword
        # sub-case it was meant for turned out to be unreachable.

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
                "Message: ``expected identifier before '<token>'``"
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
                "    compile if (X) { component C { } }"
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
    ]

    def check(self, context) -> None:  # noqa: D102
        pass  # core checking is performed in C++
