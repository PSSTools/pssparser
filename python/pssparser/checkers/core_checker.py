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
            ),
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
            patterns=(
                r"^unknown type\b",
                r"^unknown identifier\b",
                r"^unknown method\b",
            ),
            detail=(
                "The linker could not resolve a named type, identifier, or "
                "method.  Messages include patterns such as:\n\n"
                "* ``unknown type 'Foo'``\n"
                "* ``unknown type 'Foo' in 'pkg'`` (the name is not in the "
                "qualifying package or scope)\n"
                "* ``unknown identifier 'bar'``\n"
                "* ``unknown method 'baz' on built-in type``\n\n"
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
            patterns=(r"^duplicate\b",),
            detail=(
                "A symbol with this name is already declared in the same "
                "scope.  Messages include patterns such as:\n\n"
                "* ``duplicate declaration of 'Foo'``\n"
                "* ``duplicate variable declaration bar``\n"
                "* ``duplicate parameter name 'p'``\n"
                "* ``duplicate symbol declaration``\n\n"
                "Rename one of the declarations to resolve the conflict.\n\n"
                "Note that ``duplicate declaration of '...'`` is currently "
                "emitted as a *warning* while the other three are errors."
            ),
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
            summary="Wrong number of arguments in a call",
            patterns=(
                r"^call to '.*' expects\b",
                r"^no overload of '.*' accepts\b",
            ),
            detail=(
                "A call supplies a number of arguments the function does not "
                "accept.  Messages include patterns such as:\n\n"
                "* ``call to 'g' expects 1 argument, got 3``\n"
                "* ``call to 'g' expects 1 to 2 arguments, got 0`` "
                "(trailing parameters have defaults)\n"
                "* ``call to 'g' expects at least 1 argument, got 0`` "
                "(the function is variadic)\n"
                "* ``no overload of 'g' accepts 3 arguments``\n\n"
                "This covers the argument *count* only.  A mismatched "
                "argument type is reported separately, as ``PSS007``.\n\n"
                "Built-in ``string`` methods are checked here too -- they "
                "carry real signatures.  Collection methods other than "
                "``push_back`` are not yet: they still resolve by name, so "
                "their argument count is unchecked."
            ),
        ),

        MarkerDef(
            id="PSS007",
            severity="error",
            summary="Argument type mismatch in a call",
            patterns=(
                r"^argument \d+ to '.*' expects\b",
            ),
            detail=(
                "An argument belongs to a different broad type category than "
                "the parameter it is passed to::\n\n"
                "    argument 1 to 'g' expects int, got string\n"
                "    argument 2 to 'g' expects string, got an aggregate literal\n\n"
                "The comparison is by *category* -- numeric, string, "
                "``chandle``, aggregate, ``null`` -- not by exact type.  The "
                "numeric family (``int``, ``bit``, ``bool``, ``float``, enums) "
                "converts freely, so nothing is reported for width, "
                "signedness, or enum-vs-int differences.  Anything the linker "
                "cannot classify -- a user-defined type, a member path such as "
                "``a.b``, a subscript, or a call used as an argument -- is "
                "left alone rather than guessed at, so this check reports no "
                "false positives but is far from exhaustive.\n\n"
                "The count is checked separately, as ``PSS006``; an argument "
                "with the wrong count is never also reported here."
            ),
        ),

        MarkerDef(
            id="PSS008",
            severity="error",
            summary="Call to something that is not a function",
            patterns=(
                r"^'.*' is not a function; it is\b",
            ),
            detail=(
                "A path element carries an argument list, but the declaration "
                "it resolves to is a value rather than a function::\n\n"
                "    'f' is not a function; it is a field\n"
                "    'v' is not a function; it is a variable\n"
                "    'x' is not a function; it is a parameter\n\n"
                "Only declarations that are unambiguously values are reported "
                "-- fields, procedural variables, and function parameters.  A "
                "call whose target the linker models loosely is left alone "
                "rather than guessed at.  Built-in ``string`` and collection "
                "methods are unaffected: they resolve through a separate path "
                "and never reach this check."
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
            patterns=(r"^annotation is not attached\b",),
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
